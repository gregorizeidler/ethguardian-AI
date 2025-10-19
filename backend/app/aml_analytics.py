import time
from typing import Dict, List, Optional, Tuple

from neo4j import Driver

# Heurísticas AML (consultas Cypher) + criação de Alert nodes


def _create_alert(tx, address: str, alert_type: str, score: float, details: Dict) -> None:
    now = int(time.time() * 1000)
    alert_id = f"{alert_type}:{address}:{now}"
    cypher = """
    MERGE (a:Address {address: $address})
    MERGE (al:Alert {id: $id})
      ON CREATE SET al.created_at = $now
      SET al.type = $type, al.score = $score, al.details = $details
    MERGE (al)-[:FOR]->(a)
    WITH a, al
    SET a.last_alert_ts = $now, a.has_alert = true
    """
    tx.run(
        cypher,
        address=address,
        id=alert_id,
        now=now,
        type=alert_type,
        score=float(score),
        details=details,
    )


def detect_structuring(tx, address: Optional[str] = None) -> List[Tuple[str, float]]:
    """
    Detecta 'structuring': muitos depósitos pequenos num curto período.
    Retorna lista de tuplas (address, score).
    """
    cypher = """
    MATCH (a:Address {address: $address})<-[:RECEIVED_BY]-(t:Transaction)
    WHERE t.value > 0 AND t.value < $max_small
      AND t.time >= $since
    WITH a, count(t) AS cnt, sum(t.value) AS total
    WHERE cnt >= $min_count
    RETURN a.address AS address, (toFloat(cnt) / $min_count) * 20 + (CASE WHEN total > 1.0 THEN 10 ELSE 0 END) AS score
    """
    rows = list(
        tx.run(
            cypher,
            address=address,
            max_small=0.5,  # < 0.5 ETH
            since=int(time.time()) - 3 * 24 * 3600,  # últimos 3 dias
            min_count=5,
        )
    )
    results = []
    for r in rows:
        score = float(r["score"])
        results.append((r["address"], score))
        _create_alert(tx, r["address"], "STRUCTURING", score, {"window_days": 3})
    return results


def detect_peel_chains(tx, address: Optional[str] = None) -> List[Tuple[str, float]]:
    """
    Peel chain: caminhos dirigidos com redução de valor por hop.
    """
    cypher = """
    MATCH (a0:Address {address: $address})-[r1:TRANSFER]->(a1:Address)-[r2:TRANSFER]->(a2:Address)
    WHERE r2.value_sum <= r1.value_sum * $ratio
    WITH a0, a1, a2, r1, r2
    OPTIONAL MATCH (a2)-[r3:TRANSFER]->(a3:Address)
    WHERE r3.value_sum <= r2.value_sum * $ratio
    WITH a0, count(*) AS depth
    RETURN a0.address AS address, CASE WHEN depth >= 1 THEN 40 ELSE 0 END + depth * 10 AS score
    """
    rows = list(tx.run(cypher, address=address, ratio=0.7))
    results = []
    for r in rows:
        score = float(r["score"])
        results.append((r["address"], score))
        _create_alert(tx, r["address"], "PEEL_CHAIN", score, {"ratio": 0.7})
    return results


def find_mixer_activity(tx, address: Optional[str] = None) -> List[Tuple[str, float]]:
    """
    Fan-in/out acentuado pode indicar mixers/serviços.
    """
    cypher = """
    MATCH (a:Address {address: $address})
    OPTIONAL MATCH (src:Address)-[rin:TRANSFER]->(a)
    WITH a, count(DISTINCT src) AS fanin
    OPTIONAL MATCH (a)-[rout:TRANSFER]->(dst:Address)
    WITH a, fanin, count(DISTINCT dst) AS fanout
    RETURN a.address AS address,
           CASE WHEN fanin >= 20 OR fanout >= 20 THEN 60
                WHEN fanin >= 10 OR fanout >= 10 THEN 40
                ELSE 0 END AS score,
           fanin, fanout
    """
    rows = list(tx.run(cypher, address=address))
    results = []
    for r in rows:
        score = float(r["score"])
        if score > 0:
            results.append((r["address"], score))
            _create_alert(
                tx,
                r["address"],
                "MIXER_PATTERN",
                score,
                {"fanin": int(r["fanin"]), "fanout": int(r["fanout"])},
            )
    return results


def run_taint_analysis(tx, address: str) -> List[Tuple[str, float]]:
    """
    'Taint' por proximidade a endereços com alertas pesados.
    """
    cypher = """
    MATCH (bad:Address)<-[:FOR]-(al:Alert)
    WHERE al.type IN ['SANCTION', 'MIXER_PATTERN', 'PEEL_CHAIN'] AND al.score >= 50
    WITH collect(DISTINCT bad) AS bads
    MATCH (a:Address {address: $address})
    OPTIONAL MATCH p = shortestPath((a)-[:TRANSFER*..3]-(b))
    WHERE b IN bads
    WITH a, p
    RETURN a.address AS address,
           CASE WHEN p IS NULL THEN 0 ELSE 50 - 10 * (length(p)-1) END AS score
    """
    rows = list(tx.run(cypher, address=address))
    results = []
    for r in rows:
        score = max(0.0, float(r["score"]))
        if score > 0:
            results.append((r["address"], score))
            _create_alert(tx, r["address"], "TAINT", score, {"max_hops": 3})
    return results


def find_circular_txns(tx, address: Optional[str] = None) -> List[Tuple[str, float]]:
    """
    Ciclos onde fundos retornam ao endereço.
    """
    cypher = """
    MATCH (a:Address {address: $address})
    MATCH p = (a)-[:TRANSFER*2..4]->(a)
    WITH a, count(p) AS cycles
    RETURN a.address AS address,
           CASE WHEN cycles >= 3 THEN 50 WHEN cycles = 2 THEN 35 WHEN cycles = 1 THEN 20 ELSE 0 END AS score,
           cycles
    """
    rows = list(tx.run(cypher, address=address))
    results = []
    for r in rows:
        score = float(r["score"])
        if score > 0:
            results.append((r["address"], score))
            _create_alert(tx, r["address"], "CIRCULARITY", score, {"cycles": int(r["cycles"])})
    return results


def detect_velocity_alert(tx, address: Optional[str] = None) -> List[Tuple[str, float]]:
    """
    Detects high-frequency transaction bursts (velocity alert).
    Many transactions in short time period suggests bot or coordinated activity.
    """
    cypher = """
    MATCH (a:Address {address: $address})-[:EMITTED]->(t:Transaction)
    WHERE t.time >= $since
    WITH a, count(t) AS tx_count, 
         max(t.time) - min(t.time) AS time_span_seconds
    WHERE tx_count >= $min_count
    WITH a, tx_count, time_span_seconds,
         CASE 
            WHEN time_span_seconds > 0 
            THEN toFloat(tx_count) / (toFloat(time_span_seconds) / 3600.0)
            ELSE toFloat(tx_count)
         END AS txs_per_hour
    WHERE txs_per_hour >= 10
    RETURN a.address AS address,
           CASE 
              WHEN txs_per_hour >= 50 THEN 70.0
              WHEN txs_per_hour >= 30 THEN 55.0
              WHEN txs_per_hour >= 10 THEN 40.0
              ELSE 30.0
           END AS score,
           tx_count, txs_per_hour
    """
    rows = list(
        tx.run(
            cypher,
            address=address,
            since=int(time.time()) - 24 * 3600,  # Last 24 hours
            min_count=10
        )
    )
    results = []
    for r in rows:
        score = float(r["score"])
        results.append((r["address"], score))
        _create_alert(
            tx, 
            r["address"], 
            "VELOCITY_ALERT", 
            score, 
            {
                "tx_count": int(r["tx_count"]),
                "txs_per_hour": float(r["txs_per_hour"]),
                "window_hours": 24
            }
        )
    return results


def detect_dormant_reactivation(tx, address: Optional[str] = None) -> List[Tuple[str, float]]:
    """
    Detects dormant accounts that suddenly reactivate with large transactions.
    Could indicate hacked account or "sleeper cell" activation.
    """
    cypher = """
    MATCH (a:Address {address: $address})
    WHERE a.first_seen IS NOT NULL AND a.last_seen IS NOT NULL
    WITH a, (a.last_seen - a.first_seen) AS lifetime_seconds
    WHERE lifetime_seconds > $dormant_threshold
    MATCH (a)-[:EMITTED]->(t:Transaction)
    WHERE t.time >= $recent_threshold AND t.value >= $min_value
    WITH a, lifetime_seconds, count(t) AS recent_tx_count, sum(t.value) AS recent_value
    WHERE recent_tx_count >= 1
    RETURN a.address AS address,
           CASE 
              WHEN recent_value >= 10.0 THEN 65.0
              WHEN recent_value >= 5.0 THEN 50.0
              ELSE 35.0
           END AS score,
           lifetime_seconds / 86400 AS dormant_days,
           recent_tx_count,
           recent_value
    """
    rows = list(
        tx.run(
            cypher,
            address=address,
            dormant_threshold=180 * 24 * 3600,  # 6 months
            recent_threshold=int(time.time()) - 30 * 24 * 3600,  # Last 30 days
            min_value=1.0  # >= 1 ETH
        )
    )
    results = []
    for r in rows:
        score = float(r["score"])
        results.append((r["address"], score))
        _create_alert(
            tx,
            r["address"],
            "DORMANT_REACTIVATION",
            score,
            {
                "dormant_days": int(r["dormant_days"]),
                "recent_tx_count": int(r["recent_tx_count"]),
                "recent_value_eth": float(r["recent_value"])
            }
        )
    return results


def detect_round_amounts(tx, address: Optional[str] = None) -> List[Tuple[str, float]]:
    """
    Detects suspiciously round transaction amounts.
    Natural transactions rarely have exact values like 1.0, 5.0, 10.0 ETH.
    """
    cypher = """
    MATCH (a:Address {address: $address})-[:EMITTED]->(t:Transaction)
    WHERE t.value IN [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0]
      AND t.time >= $since
    WITH a, count(t) AS round_tx_count, collect(t.value) AS amounts
    WHERE round_tx_count >= $min_count
    RETURN a.address AS address,
           CASE 
              WHEN round_tx_count >= 20 THEN 50.0
              WHEN round_tx_count >= 10 THEN 35.0
              ELSE 25.0
           END AS score,
           round_tx_count,
           amounts[0..5] AS sample_amounts
    """
    rows = list(
        tx.run(
            cypher,
            address=address,
            since=int(time.time()) - 90 * 24 * 3600,  # Last 90 days
            min_count=5
        )
    )
    results = []
    for r in rows:
        score = float(r["score"])
        results.append((r["address"], score))
        _create_alert(
            tx,
            r["address"],
            "ROUND_AMOUNTS",
            score,
            {
                "round_tx_count": int(r["round_tx_count"]),
                "sample_amounts": r["sample_amounts"]
            }
        )
    return results


def detect_timing_patterns(tx, address: Optional[str] = None) -> List[Tuple[str, float]]:
    """
    Detects transactions that occur at regular time intervals.
    Suggests automated bot behavior or scheduled operations.
    """
    cypher = """
    MATCH (a:Address {address: $address})-[:EMITTED]->(t:Transaction)
    WHERE t.time >= $since
    WITH a, t.time AS timestamp
    ORDER BY timestamp
    WITH a, collect(timestamp) AS timestamps
    WHERE size(timestamps) >= $min_count
    WITH a, timestamps,
         [i IN range(0, size(timestamps)-2) | timestamps[i+1] - timestamps[i]] AS intervals
    WITH a, timestamps, intervals,
         reduce(sum = 0.0, interval IN intervals | sum + interval) / size(intervals) AS avg_interval,
         reduce(sum = 0.0, interval IN intervals | 
            sum + (interval - reduce(s = 0.0, x IN intervals | s + x) / size(intervals))^2
         ) / size(intervals) AS variance
    WHERE variance < $max_variance AND avg_interval < 24 * 3600
    RETURN a.address AS address,
           CASE 
              WHEN avg_interval <= 3600 THEN 55.0
              WHEN avg_interval <= 7200 THEN 45.0
              ELSE 35.0
           END AS score,
           avg_interval / 3600.0 AS avg_hours,
           size(timestamps) AS tx_count
    """
    rows = list(
        tx.run(
            cypher,
            address=address,
            since=int(time.time()) - 30 * 24 * 3600,  # Last 30 days
            min_count=10,
            max_variance=3600 * 3600  # 1 hour variance
        )
    )
    results = []
    for r in rows:
        score = float(r["score"])
        results.append((r["address"], score))
        _create_alert(
            tx,
            r["address"],
            "TIMING_PATTERN",
            score,
            {
                "avg_interval_hours": float(r["avg_hours"]),
                "tx_count": int(r["tx_count"])
            }
        )
    return results


def detect_wash_trading(tx, address: Optional[str] = None) -> List[Tuple[str, float]]:
    """
    Detects wash trading - same addresses trading back and forth.
    Used to inflate volume or manipulate prices.
    """
    cypher = """
    MATCH (a:Address {address: $address})-[r1:TRANSFER]->(b:Address)
    MATCH (b)-[r2:TRANSFER]->(a)
    WHERE r1.last_ts >= $since AND r2.last_ts >= $since
    WITH a, b, r1, r2,
         abs(r1.value_sum - r2.value_sum) AS value_diff
    WHERE r1.count >= 3 AND r2.count >= 3
      AND value_diff < (r1.value_sum * 0.1)
    WITH a, count(DISTINCT b) AS counterparties,
         sum(r1.count + r2.count) AS total_roundtrips
    RETURN a.address AS address,
           CASE 
              WHEN total_roundtrips >= 20 THEN 70.0
              WHEN total_roundtrips >= 10 THEN 55.0
              ELSE 40.0
           END AS score,
           counterparties,
           total_roundtrips
    """
    rows = list(
        tx.run(
            cypher,
            address=address,
            since=int(time.time()) - 90 * 24 * 3600  # Last 90 days
        )
    )
    results = []
    for r in rows:
        score = float(r["score"])
        results.append((r["address"], score))
        _create_alert(
            tx,
            r["address"],
            "WASH_TRADING",
            score,
            {
                "counterparties": int(r["counterparties"]),
                "total_roundtrips": int(r["total_roundtrips"])
            }
        )
    return results


def run_all_analytics(tx, address: str) -> Dict:
    """
    Executa todas as heurísticas e cria Alert nodes.
    """
    out = {}
    # Original alerts
    out["structuring"] = detect_structuring(tx, address)
    out["peel_chains"] = detect_peel_chains(tx, address)
    out["mixer_activity"] = find_mixer_activity(tx, address)
    out["taint"] = run_taint_analysis(tx, address)
    out["circularity"] = find_circular_txns(tx, address)
    
    # New advanced alerts
    out["velocity_alert"] = detect_velocity_alert(tx, address)
    out["dormant_reactivation"] = detect_dormant_reactivation(tx, address)
    out["round_amounts"] = detect_round_amounts(tx, address)
    out["timing_patterns"] = detect_timing_patterns(tx, address)
    out["wash_trading"] = detect_wash_trading(tx, address)
    
    return out
