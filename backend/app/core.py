import os
import time
import logging
from typing import Dict, List, Tuple

import requests
from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver

load_dotenv()
logger = logging.getLogger("aml.core")
logging.basicConfig(level=logging.INFO)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")
ETHERSCAN_CHAIN_ID = int(os.getenv("ETHERSCAN_CHAIN_ID", "1"))  # Default: Ethereum Mainnet

driver: Driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def init_constraints() -> None:
    """Cria constraints idempotentes para Address, Transaction e Alert."""
    cyphers = [
        "CREATE CONSTRAINT address_unique IF NOT EXISTS FOR (a:Address) REQUIRE a.address IS UNIQUE",
        "CREATE CONSTRAINT tx_hash_unique IF NOT EXISTS FOR (t:Transaction) REQUIRE t.hash IS UNIQUE",
        "CREATE CONSTRAINT alert_id_unique IF NOT EXISTS FOR (al:Alert) REQUIRE al.id IS UNIQUE",
    ]
    with driver.session() as session:
        for c in cyphers:
            session.execute_write(lambda tx: tx.run(c))
    logger.info("Constraints ok.")


class EtherscanClient:
    BASE = "https://api.etherscan.io/v2/api"  # V2 API endpoint

    def __init__(self, api_key: str | None = None, chain_id: int = 1):
        """
        Initialize Etherscan V2 Client.
        
        Args:
            api_key: Etherscan API key
            chain_id: Chain ID (1=Ethereum Mainnet, 56=BSC, 137=Polygon, etc)
        """
        self.api_key = api_key or ETHERSCAN_API_KEY
        self.chain_id = chain_id
        if not self.api_key:
            logger.warning("ETHERSCAN_API_KEY não definido. Ingestão pode falhar.")

    def get_txlist(
        self,
        address: str,
        startblock: int = 0,
        endblock: int = 99999999,
        sort: str = "asc",
    ) -> List[Dict]:
        """
        Busca lista de transações 'normal' (externally owned accounts).
        Now using Etherscan V2 API with chainid parameter.
        """
        params = {
            "chainid": self.chain_id,  # V2 requires chainid
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": startblock,
            "endblock": endblock,
            "sort": sort,
            "apikey": self.api_key,
        }
        r = requests.get(self.BASE, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        if data.get("status") == "0" and data.get("message") != "No transactions found":
            raise RuntimeError(f"Etherscan V2 error: {data}")
        result = data.get("result", [])
        return result


def _prepare_tx_rows(raw_txs: List[Dict]) -> List[Dict]:
    rows = []
    for t in raw_txs:
        if not t.get("to"):
            # Contrato criado (to vazio) — ignorar por simplicidade
            continue
        try:
            value_eth = int(t["value"]) / 1e18
        except Exception:
            value_eth = 0.0
        rows.append(
            {
                "hash": t["hash"],
                "from": t["from"],
                "to": t["to"],
                "value": float(value_eth),
                "ts": int(t["timeStamp"]),
                "block": int(t["blockNumber"]),
                "nonce": int(t.get("nonce", 0)),
            }
        )
    return rows


def ingest_address(address: str, limit: int | None = None) -> Dict:
    """Ingestão de transações do Etherscan e *MERGE* no Neo4j."""
    client = EtherscanClient(chain_id=ETHERSCAN_CHAIN_ID)
    logger.info("Ingesting from Etherscan V2 (Chain ID: %d) for %s", ETHERSCAN_CHAIN_ID, address)
    raw = client.get_txlist(address)
    if limit:
        raw = raw[:limit]
    rows = _prepare_tx_rows(raw)

    if not rows:
        logger.info("Nenhuma transação para %s", address)
        return {"ingested": 0}

    cypher = """
    UNWIND $txs AS tx
    WITH tx
    WHERE tx.to IS NOT NULL AND tx.to <> ''
    MERGE (a:Address {address: tx.from})
      ON CREATE SET a.first_seen = tx.ts, a.total_in = 0.0, a.total_out = 0.0
      SET a.last_seen = CASE WHEN a.last_seen IS NULL OR a.last_seen < tx.ts THEN tx.ts ELSE a.last_seen END,
          a.total_out = coalesce(a.total_out, 0.0) + tx.value
    MERGE (b:Address {address: tx.to})
      ON CREATE SET b.first_seen = tx.ts, b.total_in = 0.0, b.total_out = 0.0
      SET b.last_seen = CASE WHEN b.last_seen IS NULL OR b.last_seen < tx.ts THEN tx.ts ELSE b.last_seen END,
          b.total_in = coalesce(b.total_in, 0.0) + tx.value
    MERGE (t:Transaction {hash: tx.hash})
      ON CREATE SET t.value = tx.value, t.time = tx.ts, t.block = tx.block, t.nonce = tx.nonce
    MERGE (a)-[:EMITTED]->(t)
    MERGE (t)-[:RECEIVED_BY]->(b)
    MERGE (a)-[r:TRANSFER]->(b)
      ON CREATE SET r.count = 0, r.value_sum = 0.0, r.last_ts = tx.ts
      SET r.count = r.count + 1, r.value_sum = r.value_sum + tx.value, r.last_ts = tx.ts
    """
    with driver.session() as session:
        session.execute_write(lambda tx: tx.run(cypher, txs=rows))
    logger.info("Ingested %d tx rows.", len(rows))
    return {"ingested": len(rows)}


def expand_graph(address: str, hops: int = 2, limit_nodes: int = 400) -> Tuple[List[Dict], List[Dict]]:
    """
    Retorna nós (endereços) e arestas (TRANSFER) até N hops.
    """
    hops = max(1, min(3, int(hops)))  # proteção simples
    node_query = """
    MATCH (seed:Address {address: $address})
    MATCH (seed)-[:TRANSFER*0..$hops]-(n:Address)
    WITH DISTINCT n LIMIT $limit
    RETURN n.address AS id, coalesce(n.risk_score, 0.0) AS risk, coalesce(n.label, '') AS label
    """
    link_query = """
    UNWIND $ids AS ids
    WITH ids
    MATCH (a:Address)-[r:TRANSFER]-(b:Address)
    WHERE a.address IN ids AND b.address IN ids
    RETURN a.address AS source, b.address AS target, r.count AS count, r.value_sum AS value_sum
    """
    with driver.session() as session:
        node_records = session.execute_read(
            lambda tx: list(tx.run(node_query, address=address, hops=hops, limit=limit_nodes))
        )
        node_ids = [rec["id"] for rec in node_records]
        link_records = session.execute_read(
            lambda tx: list(tx.run(link_query, ids=node_ids))
        )

    nodes = [
        {"id": rec["id"], "label": rec["label"] or rec["id"][:10] + "…", "risk_score": rec["risk"]}
        for rec in node_records
    ]
    links = [
        {
            "source": rec["source"],
            "target": rec["target"],
            "label": "TRANSFER",
            "count": rec["count"],
            "value_sum": rec["value_sum"],
        }
        for rec in link_records
    ]
    return nodes, links
