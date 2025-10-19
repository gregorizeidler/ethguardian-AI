"""
Fraud Detection Module
Detects specific types of crypto fraud including:
- Rug pulls (DeFi scams)
- Ponzi schemes
- Phishing attacks
- MEV bot attacks
- Flash loan exploits
- Token scams
"""

from typing import Dict, Any, List
from datetime import datetime
import statistics


class FraudDetector:
    """Detect specific fraud patterns in blockchain activity"""
    
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
    
    def detect_rug_pull_pattern(self, address: str) -> Dict[str, Any]:
        """
        Detect rug pull pattern:
        - Large initial inflows (liquidity deposits)
        - Sudden massive outflow
        - Little to no subsequent activity
        """
        query = """
        MATCH (a:Address {address: $address})
        OPTIONAL MATCH (a)<-[t_in:TRANSACTION]-(sender)
        OPTIONAL MATCH (a)-[t_out:TRANSACTION]->(receiver)
        WITH a,
             collect(DISTINCT {value: t_in.value_eth, timestamp: t_in.timestamp}) as inflows,
             collect(DISTINCT {value: t_out.value_eth, timestamp: t_out.timestamp}) as outflows
        RETURN 
            inflows,
            outflows,
            reduce(total = 0.0, tx in inflows | total + coalesce(tx.value, 0)) as total_in,
            reduce(total = 0.0, tx in outflows | total + coalesce(tx.value, 0)) as total_out
        """
        
        with self.driver.session() as session:
            result = session.run(query, address=address)
            record = result.single()
            
            if not record:
                return {
                    "fraud_type": "rug_pull",
                    "detected": False,
                    "risk_score": 0
                }
            
            inflows = [tx for tx in record["inflows"] if tx.get("value")]
            outflows = [tx for tx in record["outflows"] if tx.get("value")]
            total_in = record["total_in"] or 0
            total_out = record["total_out"] or 0
            
            score = 0
            indicators = []
            
            # Check for massive outflow relative to inflow
            if total_in > 0 and total_out > total_in * 0.8:
                score += 40
                indicators.append("Large outflow relative to inflow")
            
            # Check for sudden drain
            if outflows:
                outflow_values = [tx["value"] for tx in outflows if tx.get("value")]
                if outflow_values:
                    max_outflow = max(outflow_values)
                    if max_outflow > total_out * 0.7:
                        score += 40
                        indicators.append("Single large withdrawal")
            
            # Check for activity cessation
            if outflows:
                last_outflow = max(tx["timestamp"] for tx in outflows if tx.get("timestamp"))
                time_since = datetime.now().timestamp() - last_outflow
                if time_since > 7 * 24 * 3600:  # 7 days
                    score += 20
                    indicators.append("No activity after withdrawal")
            
            return {
                "fraud_type": "rug_pull",
                "detected": score >= 60,
                "risk_score": min(score, 100),
                "indicators": indicators,
                "total_in": total_in,
                "total_out": total_out,
                "withdrawal_percentage": (total_out / total_in * 100) if total_in > 0 else 0
            }
    
    def detect_ponzi_scheme(self, address: str) -> Dict[str, Any]:
        """
        Detect Ponzi scheme pattern:
        - Many small inflows (investors)
        - Outflows to early investors
        - Pyramid structure
        """
        query = """
        MATCH (a:Address {address: $address})
        OPTIONAL MATCH (a)<-[t_in:TRANSACTION]-(sender)
        OPTIONAL MATCH (a)-[t_out:TRANSACTION]->(receiver)
        WITH a,
             count(DISTINCT sender) as unique_senders,
             count(DISTINCT receiver) as unique_receivers,
             collect(DISTINCT t_in.value_eth) as inflow_amounts,
             collect(DISTINCT t_out.value_eth) as outflow_amounts,
             count(t_in) as total_in_tx,
             count(t_out) as total_out_tx
        RETURN 
            unique_senders,
            unique_receivers,
            inflow_amounts,
            outflow_amounts,
            total_in_tx,
            total_out_tx
        """
        
        with self.driver.session() as session:
            result = session.run(query, address=address)
            record = result.single()
            
            if not record:
                return {
                    "fraud_type": "ponzi_scheme",
                    "detected": False,
                    "risk_score": 0
                }
            
            unique_senders = record["unique_senders"]
            unique_receivers = record["unique_receivers"]
            inflow_amounts = [a for a in record["inflow_amounts"] if a]
            outflow_amounts = [a for a in record["outflow_amounts"] if a]
            
            score = 0
            indicators = []
            
            # Many depositors
            if unique_senders > 50:
                score += 30
                indicators.append(f"Many depositors ({unique_senders})")
            
            # Fewer receivers than senders (pyramid)
            if unique_senders > 0 and unique_receivers > 0:
                ratio = unique_receivers / unique_senders
                if ratio < 0.3:
                    score += 30
                    indicators.append("Pyramid structure detected")
            
            # Consistent small deposits
            if inflow_amounts and len(inflow_amounts) > 10:
                avg_inflow = statistics.mean(inflow_amounts)
                stdev_inflow = statistics.stdev(inflow_amounts) if len(inflow_amounts) > 1 else 0
                if stdev_inflow < avg_inflow * 0.5:  # Low variance
                    score += 20
                    indicators.append("Consistent deposit amounts")
            
            # Higher outflows to early participants
            if outflow_amounts and inflow_amounts:
                avg_outflow = statistics.mean(outflow_amounts)
                avg_inflow = statistics.mean(inflow_amounts)
                if avg_outflow > avg_inflow * 1.2:
                    score += 20
                    indicators.append("Returns exceed deposits")
            
            return {
                "fraud_type": "ponzi_scheme",
                "detected": score >= 60,
                "risk_score": min(score, 100),
                "indicators": indicators,
                "unique_depositors": unique_senders,
                "unique_receivers": unique_receivers,
                "pyramid_ratio": unique_receivers / unique_senders if unique_senders > 0 else 0
            }
    
    def detect_phishing(self, address: str) -> Dict[str, Any]:
        """
        Detect phishing pattern:
        - Many small inflows from different addresses
        - Rapid consolidation and withdrawal
        """
        query = """
        MATCH (a:Address {address: $address})
        OPTIONAL MATCH (a)<-[t_in:TRANSACTION]-(victim)
        WITH a, 
             count(DISTINCT victim) as victim_count,
             collect({
                 from: victim.address,
                 value: t_in.value_eth,
                 timestamp: t_in.timestamp
             }) as victim_txs
        OPTIONAL MATCH (a)-[t_out:TRANSACTION]->(destination)
        WITH a, victim_count, victim_txs,
             count(DISTINCT destination) as destination_count,
             min(t_out.timestamp) as first_withdrawal
        RETURN 
            victim_count,
            victim_txs,
            destination_count,
            first_withdrawal
        """
        
        with self.driver.session() as session:
            result = session.run(query, address=address)
            record = result.single()
            
            if not record:
                return {
                    "fraud_type": "phishing",
                    "detected": False,
                    "risk_score": 0
                }
            
            victim_count = record["victim_count"]
            victim_txs = record["victim_txs"]
            destination_count = record["destination_count"]
            first_withdrawal = record["first_withdrawal"]
            
            score = 0
            indicators = []
            
            # Many different sources (victims)
            if victim_count > 20:
                score += 40
                indicators.append(f"Multiple victims ({victim_count})")
            
            # Small amounts from each
            if victim_txs:
                amounts = [tx["value"] for tx in victim_txs if tx.get("value")]
                if amounts:
                    avg_amount = statistics.mean(amounts)
                    if avg_amount < 0.5:  # Small amounts
                        score += 20
                        indicators.append("Small amounts from each victim")
            
            # Quick consolidation
            if victim_txs and first_withdrawal:
                timestamps = [tx["timestamp"] for tx in victim_txs if tx.get("timestamp")]
                if timestamps:
                    last_deposit = max(timestamps)
                    time_to_withdraw = first_withdrawal - last_deposit
                    if time_to_withdraw < 3600:  # Less than 1 hour
                        score += 30
                        indicators.append("Rapid withdrawal after deposits")
            
            # Few destinations (consolidation)
            if destination_count > 0 and destination_count < 5:
                score += 10
                indicators.append("Funds consolidated to few addresses")
            
            return {
                "fraud_type": "phishing",
                "detected": score >= 60,
                "risk_score": min(score, 100),
                "indicators": indicators,
                "potential_victims": victim_count,
                "consolidation_addresses": destination_count
            }
    
    def detect_mev_bot(self, address: str) -> Dict[str, Any]:
        """
        Detect MEV bot activity (front-running, sandwich attacks)
        - Very high transaction frequency
        - Transactions clustered in same blocks
        - Profitable patterns
        """
        query = """
        MATCH (a:Address {address: $address})-[t:TRANSACTION]->()
        WITH a, 
             count(t) as tx_count,
             collect(t.block_number) as blocks,
             collect(t.timestamp) as timestamps
        RETURN 
            tx_count,
            blocks,
            timestamps,
            size([b in blocks WHERE size([x in blocks WHERE x = b]) > 1]) as multi_tx_blocks
        """
        
        with self.driver.session() as session:
            result = session.run(query, address=address)
            record = result.single()
            
            if not record:
                return {
                    "fraud_type": "mev_bot",
                    "detected": False,
                    "risk_score": 0
                }
            
            tx_count = record["tx_count"]
            blocks = record["blocks"]
            timestamps = record["timestamps"]
            multi_tx_blocks = record["multi_tx_blocks"]
            
            score = 0
            indicators = []
            
            # Very high transaction frequency
            if tx_count > 1000:
                score += 40
                indicators.append(f"Very high tx frequency ({tx_count})")
            
            # Multiple transactions in same blocks
            if blocks and multi_tx_blocks > 0:
                ratio = multi_tx_blocks / len(blocks)
                if ratio > 0.3:
                    score += 40
                    indicators.append("Multiple tx in same blocks")
            
            # Check transaction timing patterns
            if timestamps and len(timestamps) > 10:
                time_diffs = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
                avg_diff = statistics.mean(time_diffs)
                if avg_diff < 60:  # Less than 1 minute between tx
                    score += 20
                    indicators.append("Very rapid transaction pattern")
            
            return {
                "fraud_type": "mev_bot",
                "detected": score >= 70,
                "risk_score": min(score, 100),
                "indicators": indicators,
                "total_transactions": tx_count,
                "multi_tx_blocks": multi_tx_blocks
            }
    
    def detect_flash_loan_exploit(self, address: str) -> Dict[str, Any]:
        """
        Detect flash loan exploit pattern:
        - Large borrowing and repayment in same block
        - Interaction with DeFi protocols
        - Profit extraction
        """
        query = """
        MATCH (a:Address {address: $address})-[t:TRANSACTION]->()
        WITH a, t.block_number as block, 
             collect(t.value_eth) as values,
             count(t) as tx_in_block
        WHERE tx_in_block > 5
        RETURN 
            block,
            values,
            tx_in_block,
            reduce(s = 0.0, v in values | s + v) as block_volume
        ORDER BY block_volume DESC
        LIMIT 10
        """
        
        with self.driver.session() as session:
            result = session.run(query, address=address)
            
            suspicious_blocks = []
            for record in result:
                if record["block_volume"] > 100:  # Large volume
                    suspicious_blocks.append({
                        "block": record["block"],
                        "transactions": record["tx_in_block"],
                        "volume": record["block_volume"]
                    })
            
            score = 0
            if suspicious_blocks:
                score = min(len(suspicious_blocks) * 30, 100)
            
            return {
                "fraud_type": "flash_loan_exploit",
                "detected": len(suspicious_blocks) > 0,
                "risk_score": score,
                "suspicious_blocks": len(suspicious_blocks),
                "details": suspicious_blocks[:5]
            }
    
    def detect_all_fraud_types(self, address: str) -> Dict[str, Any]:
        """
        Run all fraud detection algorithms
        """
        results = {
            "address": address,
            "timestamp": datetime.now().isoformat(),
            "fraud_checks": {}
        }
        
        # Run all fraud detections
        results["fraud_checks"]["rug_pull"] = self.detect_rug_pull_pattern(address)
        results["fraud_checks"]["ponzi_scheme"] = self.detect_ponzi_scheme(address)
        results["fraud_checks"]["phishing"] = self.detect_phishing(address)
        results["fraud_checks"]["mev_bot"] = self.detect_mev_bot(address)
        results["fraud_checks"]["flash_loan_exploit"] = self.detect_flash_loan_exploit(address)
        
        # Calculate overall fraud score
        fraud_scores = [f["risk_score"] for f in results["fraud_checks"].values()]
        results["overall_fraud_score"] = max(fraud_scores) if fraud_scores else 0
        results["fraud_types_detected"] = sum(1 for f in results["fraud_checks"].values() if f["detected"])
        
        # Flag high risk
        results["high_risk"] = results["overall_fraud_score"] > 70
        
        return results

