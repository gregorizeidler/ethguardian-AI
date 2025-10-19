"""
Advanced Pattern Detection Module
Detects suspicious patterns in blockchain transactions including:
- Layering (multiple transfers to obfuscate origin)
- Mixing/Tumbling detection
- Peel chains (gradual value separation)
- Round amount transactions
- Time-based suspicious patterns
- Dust attacks
- Wash trading
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import statistics


class PatternDetector:
    """Advanced pattern detection for AML analysis"""
    
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
    
    def detect_layering(self, address: str, depth: int = 5, time_window_hours: int = 24) -> Dict[str, Any]:
        """
        Detect layering patterns - multiple rapid transfers to obfuscate origin
        Layering is a key money laundering technique
        """
        query = """
        MATCH path = (start:Address {address: $address})-[:TRANSACTION*1..5]->(end:Address)
        WHERE start <> end
        WITH path, length(path) as depth, 
             [rel in relationships(path) | rel.timestamp] as timestamps,
             [rel in relationships(path) | rel.value_eth] as values
        WHERE depth >= 3
        AND (timestamps[-1] - timestamps[0]) < $time_window
        RETURN 
            depth,
            [n in nodes(path) | n.address] as chain,
            timestamps,
            values,
            reduce(total = 0.0, val in values | total + val) as total_value
        ORDER BY depth DESC
        LIMIT 50
        """
        
        with self.driver.session() as session:
            result = session.run(
                query, 
                address=address, 
                time_window=time_window_hours * 3600
            )
            
            chains = []
            for record in result:
                chains.append({
                    "depth": record["depth"],
                    "chain": record["chain"],
                    "timestamps": record["timestamps"],
                    "values": record["values"],
                    "total_value": record["total_value"],
                    "time_span_hours": (record["timestamps"][-1] - record["timestamps"][0]) / 3600
                })
            
            # Calculate layering score
            score = 0
            if chains:
                # More chains = higher score
                score += min(len(chains) * 10, 40)
                # Deeper chains = higher score
                avg_depth = statistics.mean([c["depth"] for c in chains])
                score += min(avg_depth * 5, 30)
                # Faster chains = higher score
                if chains:
                    avg_time = statistics.mean([c["time_span_hours"] for c in chains])
                    if avg_time < 1:
                        score += 30
                    elif avg_time < 6:
                        score += 20
                    elif avg_time < 24:
                        score += 10
            
            return {
                "pattern": "layering",
                "detected": len(chains) > 0,
                "risk_score": min(score, 100),
                "chains_found": len(chains),
                "details": chains[:10]  # Return top 10
            }
    
    def detect_peel_chains(self, address: str, min_outputs: int = 5) -> Dict[str, Any]:
        """
        Detect peel chains - pattern where value is gradually "peeled off"
        Common in tumbling operations
        """
        query = """
        MATCH (a:Address {address: $address})-[t:TRANSACTION]->(next:Address)
        WITH a, collect({to: next.address, value: t.value_eth, timestamp: t.timestamp}) as txs
        WHERE size(txs) >= $min_outputs
        RETURN 
            txs,
            reduce(total = 0.0, tx in txs | total + tx.value) as total_value,
            size(txs) as tx_count
        """
        
        with self.driver.session() as session:
            result = session.run(query, address=address, min_outputs=min_outputs)
            
            peel_chains = []
            for record in result:
                txs = sorted(record["txs"], key=lambda x: x["timestamp"])
                
                # Check if values are decreasing (peel pattern)
                values = [tx["value"] for tx in txs]
                is_peeling = all(values[i] > values[i+1] for i in range(len(values)-1))
                
                if is_peeling:
                    peel_chains.append({
                        "transactions": txs,
                        "total_value": record["total_value"],
                        "tx_count": record["tx_count"],
                        "value_decrease_pattern": values
                    })
            
            score = min(len(peel_chains) * 25, 100) if peel_chains else 0
            
            return {
                "pattern": "peel_chain",
                "detected": len(peel_chains) > 0,
                "risk_score": score,
                "peel_chains_found": len(peel_chains),
                "details": peel_chains[:5]
            }
    
    def detect_round_amounts(self, address: str, threshold: float = 0.9) -> Dict[str, Any]:
        """
        Detect suspicious round amount transactions
        Money launderers often use round numbers
        """
        query = """
        MATCH (a:Address {address: $address})-[t:TRANSACTION]->()
        WHERE t.value_eth IS NOT NULL
        WITH a, collect(t.value_eth) as values
        RETURN values
        """
        
        with self.driver.session() as session:
            result = session.run(query, address=address)
            record = result.single()
            
            if not record:
                return {
                    "pattern": "round_amounts",
                    "detected": False,
                    "risk_score": 0,
                    "round_count": 0
                }
            
            values = record["values"]
            if not values:
                return {
                    "pattern": "round_amounts",
                    "detected": False,
                    "risk_score": 0,
                    "round_count": 0
                }
            
            # Check for round numbers (1.0, 5.0, 10.0, 100.0, etc.)
            round_numbers = [1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 500.0, 1000.0]
            round_count = sum(1 for v in values if any(abs(v - r) < 0.01 for r in round_numbers))
            
            round_percentage = round_count / len(values) if values else 0
            
            score = 0
            if round_percentage > threshold:
                score = min(round_percentage * 100, 100)
            
            return {
                "pattern": "round_amounts",
                "detected": round_percentage > threshold,
                "risk_score": score,
                "round_count": round_count,
                "total_transactions": len(values),
                "round_percentage": round_percentage * 100
            }
    
    def detect_time_patterns(self, address: str) -> Dict[str, Any]:
        """
        Detect suspicious time patterns (e.g., activity at unusual hours)
        Most legitimate activity happens during business hours
        """
        query = """
        MATCH (a:Address {address: $address})-[t:TRANSACTION]->()
        WHERE t.timestamp IS NOT NULL
        RETURN collect(t.timestamp) as timestamps
        """
        
        with self.driver.session() as session:
            result = session.run(query, address=address)
            record = result.single()
            
            if not record or not record["timestamps"]:
                return {
                    "pattern": "time_anomaly",
                    "detected": False,
                    "risk_score": 0
                }
            
            timestamps = record["timestamps"]
            
            # Convert to hours (0-23)
            hours = [datetime.fromtimestamp(ts).hour for ts in timestamps]
            
            # Count transactions in suspicious hours (2am - 6am)
            suspicious_hours = sum(1 for h in hours if 2 <= h <= 6)
            suspicious_percentage = suspicious_hours / len(hours) if hours else 0
            
            # Count weekend activity
            weekdays = [datetime.fromtimestamp(ts).weekday() for ts in timestamps]
            weekend_count = sum(1 for d in weekdays if d >= 5)
            weekend_percentage = weekend_count / len(weekdays) if weekdays else 0
            
            score = 0
            if suspicious_percentage > 0.3:  # More than 30% at night
                score += 50
            if weekend_percentage > 0.5:  # More than 50% on weekends
                score += 30
            
            return {
                "pattern": "time_anomaly",
                "detected": score > 0,
                "risk_score": min(score, 100),
                "suspicious_hours_percentage": suspicious_percentage * 100,
                "weekend_percentage": weekend_percentage * 100,
                "most_active_hours": statistics.mode(hours) if hours else None
            }
    
    def detect_dust_attacks(self, address: str, dust_threshold: float = 0.0001) -> Dict[str, Any]:
        """
        Detect dust attacks - tiny amounts sent to track wallet
        """
        query = """
        MATCH (a:Address {address: $address})<-[t:TRANSACTION]-(sender:Address)
        WHERE t.value_eth < $dust_threshold AND t.value_eth > 0
        RETURN 
            count(t) as dust_tx_count,
            collect(DISTINCT sender.address) as dust_senders,
            collect(t.value_eth) as dust_amounts
        """
        
        with self.driver.session() as session:
            result = session.run(query, address=address, dust_threshold=dust_threshold)
            record = result.single()
            
            if not record:
                return {
                    "pattern": "dust_attack",
                    "detected": False,
                    "risk_score": 0
                }
            
            dust_count = record["dust_tx_count"]
            unique_senders = len(record["dust_senders"])
            
            score = 0
            if dust_count > 10:
                score = min(dust_count * 5, 80)
            if unique_senders > 5:
                score += 20
            
            return {
                "pattern": "dust_attack",
                "detected": dust_count > 5,
                "risk_score": min(score, 100),
                "dust_transactions": dust_count,
                "unique_dust_senders": unique_senders,
                "dust_amounts": record["dust_amounts"][:20]
            }
    
    def detect_wash_trading(self, address: str) -> Dict[str, Any]:
        """
        Detect wash trading - transactions between same entities
        """
        query = """
        MATCH (a:Address {address: $address})-[t1:TRANSACTION]->(b:Address)
        MATCH (b)-[t2:TRANSACTION]->(a)
        WHERE t1.timestamp < t2.timestamp
        AND abs(t1.value_eth - t2.value_eth) < 0.01
        RETURN 
            count(*) as wash_count,
            collect({
                counterparty: b.address,
                value: t1.value_eth,
                time_diff: t2.timestamp - t1.timestamp
            }) as wash_trades
        """
        
        with self.driver.session() as session:
            result = session.run(query, address=address)
            record = result.single()
            
            if not record:
                return {
                    "pattern": "wash_trading",
                    "detected": False,
                    "risk_score": 0
                }
            
            wash_count = record["wash_count"]
            score = min(wash_count * 15, 100) if wash_count > 0 else 0
            
            return {
                "pattern": "wash_trading",
                "detected": wash_count > 0,
                "risk_score": score,
                "wash_trades_count": wash_count,
                "details": record["wash_trades"][:10]
            }
    
    def detect_all_patterns(self, address: str) -> Dict[str, Any]:
        """
        Run all pattern detection algorithms
        """
        results = {
            "address": address,
            "timestamp": datetime.now().isoformat(),
            "patterns": {}
        }
        
        # Run all detections
        results["patterns"]["layering"] = self.detect_layering(address)
        results["patterns"]["peel_chains"] = self.detect_peel_chains(address)
        results["patterns"]["round_amounts"] = self.detect_round_amounts(address)
        results["patterns"]["time_anomaly"] = self.detect_time_patterns(address)
        results["patterns"]["dust_attack"] = self.detect_dust_attacks(address)
        results["patterns"]["wash_trading"] = self.detect_wash_trading(address)
        
        # Calculate overall suspicious pattern score
        pattern_scores = [p["risk_score"] for p in results["patterns"].values()]
        results["overall_pattern_score"] = statistics.mean(pattern_scores) if pattern_scores else 0
        results["patterns_detected"] = sum(1 for p in results["patterns"].values() if p["detected"])
        
        return results

