"""
Enhanced Analytics Module
Advanced temporal and behavioral analysis including:
- Transaction velocity analysis
- Dormancy patterns
- Burst activity detection
- Balance history tracking
- Risk progression over time
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import statistics


class EnhancedAnalytics:
    """Advanced analytics for behavioral and temporal patterns"""
    
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
    
    def analyze_velocity(self, address: str, time_window_hours: int = 24) -> Dict[str, Any]:
        """
        Analyze transaction velocity - how fast funds move through an address
        High velocity often indicates tumbling or layering
        """
        query = """
        MATCH (a:Address {address: $address})
        OPTIONAL MATCH (a)<-[t_in:TRANSACTION]-(sender)
        WHERE t_in.timestamp > timestamp() - ($time_window * 3600)
        WITH a, collect({value: t_in.value_eth, timestamp: t_in.timestamp}) as recent_inflows
        
        OPTIONAL MATCH (a)-[t_out:TRANSACTION]->(receiver)
        WHERE t_out.timestamp > timestamp() - ($time_window * 3600)
        WITH a, recent_inflows, 
             collect({value: t_out.value_eth, timestamp: t_out.timestamp}) as recent_outflows
        
        RETURN 
            recent_inflows,
            recent_outflows,
            reduce(total = 0.0, tx in recent_inflows | total + coalesce(tx.value, 0)) as total_in,
            reduce(total = 0.0, tx in recent_outflows | total + coalesce(tx.value, 0)) as total_out
        """
        
        with self.driver.session() as session:
            result = session.run(query, address=address, time_window=time_window_hours)
            record = result.single()
            
            if not record:
                return {
                    "metric": "velocity",
                    "time_window_hours": time_window_hours,
                    "risk_score": 0,
                    "velocity_ratio": 0
                }
            
            inflows = [tx for tx in record["recent_inflows"] if tx.get("value")]
            outflows = [tx for tx in record["recent_outflows"] if tx.get("value")]
            total_in = record["total_in"] or 0
            total_out = record["total_out"] or 0
            
            # Calculate velocity metrics
            inflow_count = len(inflows)
            outflow_count = len(outflows)
            
            # Velocity ratio: how quickly funds leave after arriving
            velocity_ratio = 0
            if total_in > 0:
                velocity_ratio = total_out / total_in
            
            # Calculate average time funds stay in address
            avg_residence_time = 0
            if inflows and outflows:
                residence_times = []
                for inflow in inflows:
                    for outflow in outflows:
                        if outflow["timestamp"] > inflow["timestamp"]:
                            residence_times.append(
                                (outflow["timestamp"] - inflow["timestamp"]) / 3600
                            )
                if residence_times:
                    avg_residence_time = statistics.mean(residence_times)
            
            # Calculate risk score
            score = 0
            indicators = []
            
            # High velocity (funds leave quickly)
            if velocity_ratio > 0.8:
                score += 30
                indicators.append("High velocity - funds leave quickly")
            
            # Very short residence time
            if avg_residence_time > 0 and avg_residence_time < 1:
                score += 40
                indicators.append(f"Very short residence time ({avg_residence_time:.2f}h)")
            
            # High transaction frequency
            total_tx = inflow_count + outflow_count
            if total_tx > 50:
                score += 30
                indicators.append(f"High transaction frequency ({total_tx})")
            
            return {
                "metric": "velocity",
                "time_window_hours": time_window_hours,
                "risk_score": min(score, 100),
                "velocity_ratio": velocity_ratio,
                "avg_residence_time_hours": avg_residence_time,
                "inflow_count": inflow_count,
                "outflow_count": outflow_count,
                "total_volume_in": total_in,
                "total_volume_out": total_out,
                "indicators": indicators
            }
    
    def analyze_dormancy(self, address: str) -> Dict[str, Any]:
        """
        Analyze dormancy patterns - addresses that were inactive and suddenly activate
        Often indicates compromised wallets or awakening of old criminal wallets
        """
        query = """
        MATCH (a:Address {address: $address})
        OPTIONAL MATCH (a)-[t:TRANSACTION]->()
        WITH a, collect(t.timestamp) as timestamps
        WHERE size(timestamps) > 0
        WITH a, timestamps,
             timestamps[0] as first_tx,
             timestamps[-1] as last_tx
        RETURN 
            first_tx,
            last_tx,
            timestamps,
            size(timestamps) as total_tx,
            (last_tx - first_tx) as lifespan_seconds
        """
        
        with self.driver.session() as session:
            result = session.run(query, address=address)
            record = result.single()
            
            if not record or not record["timestamps"]:
                return {
                    "metric": "dormancy",
                    "risk_score": 0,
                    "status": "no_activity"
                }
            
            timestamps = sorted(record["timestamps"])
            first_tx = record["first_tx"]
            last_tx = record["last_tx"]
            total_tx = record["total_tx"]
            lifespan = record["lifespan_seconds"]
            
            # Calculate dormancy periods (gaps > 30 days)
            dormancy_periods = []
            dormancy_threshold = 30 * 24 * 3600  # 30 days
            
            for i in range(len(timestamps) - 1):
                gap = timestamps[i + 1] - timestamps[i]
                if gap > dormancy_threshold:
                    dormancy_periods.append({
                        "start": timestamps[i],
                        "end": timestamps[i + 1],
                        "duration_days": gap / (24 * 3600)
                    })
            
            # Check if currently dormant
            time_since_last = datetime.now().timestamp() - last_tx
            currently_dormant = time_since_last > dormancy_threshold
            
            # Check for sudden awakening
            recent_activity = [ts for ts in timestamps if datetime.now().timestamp() - ts < 7 * 24 * 3600]
            sudden_awakening = len(dormancy_periods) > 0 and len(recent_activity) > 5
            
            # Calculate risk score
            score = 0
            indicators = []
            
            # Long dormancy followed by sudden activity
            if sudden_awakening:
                score += 50
                indicators.append("Sudden awakening after dormancy")
            
            # Very old wallet suddenly active
            wallet_age_days = lifespan / (24 * 3600)
            if wallet_age_days > 365 and len(recent_activity) > 0:
                score += 30
                indicators.append(f"Old wallet reactivated ({wallet_age_days:.0f} days old)")
            
            # Multiple dormancy periods
            if len(dormancy_periods) > 2:
                score += 20
                indicators.append(f"Multiple dormancy periods ({len(dormancy_periods)})")
            
            return {
                "metric": "dormancy",
                "risk_score": min(score, 100),
                "status": "dormant" if currently_dormant else "active",
                "dormancy_periods": len(dormancy_periods),
                "longest_dormancy_days": max([p["duration_days"] for p in dormancy_periods]) if dormancy_periods else 0,
                "days_since_last_activity": time_since_last / (24 * 3600),
                "sudden_awakening": sudden_awakening,
                "wallet_age_days": wallet_age_days,
                "indicators": indicators,
                "details": dormancy_periods[:5]
            }
    
    def detect_burst_activity(self, address: str, burst_threshold: int = 10, time_window_minutes: int = 60) -> Dict[str, Any]:
        """
        Detect burst activity - sudden spikes in transaction frequency
        Often indicates automated activity or panic selling/money laundering
        """
        query = """
        MATCH (a:Address {address: $address})-[t:TRANSACTION]->()
        WITH a, t.timestamp as ts
        ORDER BY ts
        WITH a, collect(ts) as timestamps
        RETURN timestamps
        """
        
        with self.driver.session() as session:
            result = session.run(query, address=address)
            record = result.single()
            
            if not record or not record["timestamps"]:
                return {
                    "metric": "burst_activity",
                    "risk_score": 0,
                    "bursts_detected": 0
                }
            
            timestamps = sorted(record["timestamps"])
            
            # Find bursts - periods with many transactions in short time
            bursts = []
            window_seconds = time_window_minutes * 60
            
            i = 0
            while i < len(timestamps):
                window_start = timestamps[i]
                window_end = window_start + window_seconds
                
                # Count transactions in this window
                tx_in_window = sum(1 for ts in timestamps[i:] if ts < window_end)
                
                if tx_in_window >= burst_threshold:
                    bursts.append({
                        "start_time": window_start,
                        "transactions": tx_in_window,
                        "duration_minutes": time_window_minutes
                    })
                    i += tx_in_window  # Skip past this burst
                else:
                    i += 1
            
            # Calculate risk score
            score = 0
            indicators = []
            
            if bursts:
                score += min(len(bursts) * 20, 60)
                indicators.append(f"{len(bursts)} burst(s) detected")
                
                # Very intense bursts
                max_burst = max(b["transactions"] for b in bursts)
                if max_burst > 50:
                    score += 40
                    indicators.append(f"Very intense burst ({max_burst} tx)")
            
            return {
                "metric": "burst_activity",
                "risk_score": min(score, 100),
                "bursts_detected": len(bursts),
                "max_burst_size": max(b["transactions"] for b in bursts) if bursts else 0,
                "indicators": indicators,
                "burst_details": bursts[:10]
            }
    
    def analyze_balance_history(self, address: str) -> Dict[str, Any]:
        """
        Analyze balance progression over time
        Detect unusual patterns like sudden large increases/decreases
        """
        query = """
        MATCH (a:Address {address: $address})
        OPTIONAL MATCH (a)<-[t_in:TRANSACTION]-()
        WITH a, collect({value: t_in.value_eth, timestamp: t_in.timestamp, type: 'in'}) as inflows
        
        OPTIONAL MATCH (a)-[t_out:TRANSACTION]->()
        WITH a, inflows + collect({value: t_out.value_eth, timestamp: t_out.timestamp, type: 'out'}) as all_txs
        
        UNWIND all_txs as tx
        WITH tx
        ORDER BY tx.timestamp
        RETURN collect(tx) as transactions
        """
        
        with self.driver.session() as session:
            result = session.run(query, address=address)
            record = result.single()
            
            if not record or not record["transactions"]:
                return {
                    "metric": "balance_history",
                    "risk_score": 0,
                    "balance_changes": []
                }
            
            transactions = record["transactions"]
            
            # Calculate balance at each point
            balance_history = []
            current_balance = 0
            
            for tx in transactions:
                if tx.get("value"):
                    if tx["type"] == "in":
                        current_balance += tx["value"]
                    else:
                        current_balance -= tx["value"]
                    
                    balance_history.append({
                        "timestamp": tx["timestamp"],
                        "balance": current_balance,
                        "change": tx["value"] if tx["type"] == "in" else -tx["value"]
                    })
            
            if not balance_history:
                return {
                    "metric": "balance_history",
                    "risk_score": 0,
                    "balance_changes": []
                }
            
            # Analyze patterns
            balances = [b["balance"] for b in balance_history]
            changes = [b["change"] for b in balance_history]
            
            max_balance = max(balances)
            current_balance = balances[-1] if balances else 0
            
            # Find sudden large changes
            large_changes = [c for c in changes if abs(c) > max_balance * 0.5]
            
            # Calculate risk score
            score = 0
            indicators = []
            
            # Sudden large increase then decrease (potential laundering)
            if large_changes and len(large_changes) > 2:
                score += 40
                indicators.append("Multiple large balance changes")
            
            # Currently near zero after having large balance
            if max_balance > 10 and current_balance < max_balance * 0.1:
                score += 30
                indicators.append("Drained after holding large balance")
            
            return {
                "metric": "balance_history",
                "risk_score": min(score, 100),
                "max_balance": max_balance,
                "current_balance": current_balance,
                "large_changes": len(large_changes),
                "balance_volatility": statistics.stdev(balances) if len(balances) > 1 else 0,
                "indicators": indicators
            }
    
    def analyze_risk_progression(self, address: str) -> Dict[str, Any]:
        """
        Analyze how risk has changed over time
        Early low risk → later high risk often indicates account compromise
        """
        query = """
        MATCH (a:Address {address: $address})-[t:TRANSACTION]->()
        WITH a, t
        ORDER BY t.timestamp
        WITH a, collect({
            timestamp: t.timestamp,
            value: t.value_eth,
            block: t.block_number
        }) as txs
        RETURN txs
        """
        
        with self.driver.session() as session:
            result = session.run(query, address=address)
            record = result.single()
            
            if not record or not record["txs"]:
                return {
                    "metric": "risk_progression",
                    "risk_score": 0,
                    "trend": "stable"
                }
            
            txs = record["txs"]
            
            # Divide history into periods and analyze each
            if len(txs) < 10:
                return {
                    "metric": "risk_progression",
                    "risk_score": 0,
                    "trend": "insufficient_data"
                }
            
            # Early period (first 25% of transactions)
            early_count = len(txs) // 4
            early_txs = txs[:early_count]
            late_txs = txs[-early_count:]
            
            # Simple heuristic: compare transaction patterns
            early_avg_value = statistics.mean([tx["value"] for tx in early_txs if tx.get("value")])
            late_avg_value = statistics.mean([tx["value"] for tx in late_txs if tx.get("value")])
            
            # Check for escalation
            value_increase = late_avg_value / early_avg_value if early_avg_value > 0 else 0
            
            score = 0
            trend = "stable"
            indicators = []
            
            if value_increase > 5:
                score = 60
                trend = "escalating"
                indicators.append("Transaction values increased significantly")
            elif value_increase > 2:
                score = 30
                trend = "increasing"
                indicators.append("Transaction values moderately increased")
            
            return {
                "metric": "risk_progression",
                "risk_score": min(score, 100),
                "trend": trend,
                "early_avg_value": early_avg_value,
                "late_avg_value": late_avg_value,
                "value_increase_ratio": value_increase,
                "indicators": indicators
            }
    
    def analyze_all_metrics(self, address: str) -> Dict[str, Any]:
        """
        Run all enhanced analytics
        """
        results = {
            "address": address,
            "timestamp": datetime.now().isoformat(),
            "analytics": {}
        }
        
        # Run all analytics
        results["analytics"]["velocity"] = self.analyze_velocity(address)
        results["analytics"]["dormancy"] = self.analyze_dormancy(address)
        results["analytics"]["burst_activity"] = self.detect_burst_activity(address)
        results["analytics"]["balance_history"] = self.analyze_balance_history(address)
        results["analytics"]["risk_progression"] = self.analyze_risk_progression(address)
        
        # Calculate overall enhanced analytics score
        scores = [a["risk_score"] for a in results["analytics"].values()]
        results["overall_analytics_score"] = statistics.mean(scores) if scores else 0
        results["high_risk_metrics"] = sum(1 for s in scores if s > 70)
        
        return results

