"""
Real-time Blockchain Monitor - Large Transaction Detection
Monitors recent blockchain activity for high-value transactions and auto-analyzes them.
"""
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from .core import EtherscanClient, driver, ingest_address
from .aml_analytics import run_all_analytics
from .ml_models import get_address_risk_score, run_gds_feature_engineering

logger = logging.getLogger("aml.monitor")


class BlockchainMonitor:
    """
    Real-time monitor for large transactions on Ethereum blockchain.
    """
    
    def __init__(
        self,
        min_value_usd: float = 100000.0,
        eth_price_usd: float = 2000.0,  # Approximate, should fetch from API
        check_interval_seconds: int = 3600,
        auto_analyze: bool = True,
        max_transactions_per_check: int = 100
    ):
        self.min_value_usd = min_value_usd
        self.eth_price_usd = eth_price_usd
        self.min_value_eth = min_value_usd / eth_price_usd
        self.check_interval_seconds = check_interval_seconds
        self.auto_analyze = auto_analyze
        self.max_transactions_per_check = max_transactions_per_check
        
        # Import chain_id from core
        from .core import ETHERSCAN_CHAIN_ID
        self.client = EtherscanClient(chain_id=ETHERSCAN_CHAIN_ID)
        self.last_check_block = None
        self.monitored_addresses: set = set()
        self.stats = {
            "checks_completed": 0,
            "large_transactions_found": 0,
            "addresses_analyzed": 0,
            "alerts_generated": 0,
            "start_time": None
        }
    
    def start_monitoring(self, duration_hours: Optional[int] = None):
        """
        Start continuous monitoring.
        
        Args:
            duration_hours: How long to monitor (None = indefinite)
        """
        logger.info(f"Starting blockchain monitor (min value: ${self.min_value_usd})")
        self.stats["start_time"] = datetime.utcnow().isoformat()
        
        end_time = None
        if duration_hours:
            end_time = datetime.utcnow() + timedelta(hours=duration_hours)
        
        while True:
            if end_time and datetime.utcnow() >= end_time:
                logger.info("Monitor duration reached. Stopping.")
                break
            
            try:
                self._check_recent_activity()
                self.stats["checks_completed"] += 1
                logger.info(f"Check #{self.stats['checks_completed']} complete. Sleeping {self.check_interval_seconds}s")
                time.sleep(self.check_interval_seconds)
            except KeyboardInterrupt:
                logger.info("Monitor stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait a bit before retrying
        
        return self.get_stats()
    
    def check_once(self) -> Dict:
        """
        Perform a single check of recent activity.
        
        Returns:
            Dict with found large transactions and analysis results
        """
        logger.info("Performing single check of recent blockchain activity")
        self.stats["start_time"] = datetime.utcnow().isoformat()
        
        results = self._check_recent_activity()
        self.stats["checks_completed"] = 1
        
        return {
            "status": "completed",
            "stats": self.stats,
            "results": results
        }
    
    def _check_recent_activity(self) -> List[Dict]:
        """
        Check recent blocks for large transactions.
        
        Returns:
            List of large transaction details
        """
        large_txs = []
        
        # Get recent block number
        current_block = self._get_current_block()
        if not current_block:
            logger.warning("Could not get current block number")
            return large_txs
        
        # Determine block range to check
        if self.last_check_block:
            start_block = self.last_check_block + 1
        else:
            # First check: look back ~24 hours (~6500 blocks)
            start_block = max(0, current_block - 6500)
        
        end_block = current_block
        self.last_check_block = current_block
        
        logger.info(f"Checking blocks {start_block} to {end_block}")
        
        # Scan for large transactions
        large_txs = self._find_large_transactions(start_block, end_block)
        self.stats["large_transactions_found"] += len(large_txs)
        
        # Auto-analyze involved addresses
        if self.auto_analyze and large_txs:
            logger.info(f"Auto-analyzing {len(large_txs)} large transactions")
            for tx in large_txs:
                self._analyze_transaction_addresses(tx)
        
        return large_txs
    
    def _get_current_block(self) -> Optional[int]:
        """Get current block number from blockchain."""
        try:
            # Use a recent transaction to get block number
            # In production, use web3 or dedicated API
            cypher = "MATCH (t:Transaction) RETURN t.block AS block ORDER BY t.block DESC LIMIT 1"
            with driver.session() as session:
                result = session.execute_read(lambda tx: tx.run(cypher).single())
                if result:
                    return int(result["block"])
        except Exception as e:
            logger.warning(f"Could not get current block from DB: {e}")
        
        # Fallback: return a recent block number (approximate)
        return 19000000  # Approximate current block as fallback
    
    def _find_large_transactions(self, start_block: int, end_block: int) -> List[Dict]:
        """
        Find transactions above value threshold in block range.
        
        This is a simplified version. In production, you would:
        1. Stream blocks using web3.py or similar
        2. Parse transaction logs
        3. Filter by value
        
        For now, we'll scan known addresses in our DB.
        """
        # Query existing transactions in DB
        cypher = """
        MATCH (t:Transaction)
        WHERE t.block >= $start_block AND t.block <= $end_block
          AND t.value >= $min_value
        MATCH (from:Address)-[:EMITTED]->(t)-[:RECEIVED_BY]->(to:Address)
        RETURN DISTINCT
          t.hash AS hash,
          from.address AS from_address,
          to.address AS to_address,
          t.value AS value_eth,
          t.time AS timestamp,
          t.block AS block
        ORDER BY t.value DESC
        LIMIT $limit
        """
        
        with driver.session() as session:
            records = session.execute_read(
                lambda tx: list(tx.run(
                    cypher,
                    start_block=start_block,
                    end_block=end_block,
                    min_value=self.min_value_eth,
                    limit=self.max_transactions_per_check
                ))
            )
        
        large_txs = []
        for rec in records:
            large_txs.append({
                "hash": rec["hash"],
                "from": rec["from_address"],
                "to": rec["to_address"],
                "value_eth": float(rec["value_eth"]),
                "value_usd": float(rec["value_eth"]) * self.eth_price_usd,
                "timestamp": rec["timestamp"],
                "block": rec["block"]
            })
        
        logger.info(f"Found {len(large_txs)} large transactions in block range")
        return large_txs
    
    def _analyze_transaction_addresses(self, tx: Dict):
        """Analyze both sender and receiver of a large transaction."""
        for address in [tx["from"], tx["to"]]:
            if address in self.monitored_addresses:
                continue  # Already analyzed
            
            try:
                logger.info(f"Auto-analyzing address {address} (large tx: ${tx['value_usd']:,.0f})")
                
                # Ingest if not already in DB
                ingest_address(address, limit=500)
                
                # Run analytics
                with driver.session() as session:
                    analytics = session.execute_write(lambda tx_db: run_all_analytics(tx_db, address))
                    alert_count = sum(len(v) for v in analytics.values())
                    self.stats["alerts_generated"] += alert_count
                
                # Calculate risk score (quick version)
                risk_score = self._calculate_quick_risk(analytics)
                
                logger.info(f"Address {address}: Risk Score = {risk_score:.1f}, Alerts = {alert_count}")
                
                self.monitored_addresses.add(address)
                self.stats["addresses_analyzed"] += 1
                
            except Exception as e:
                logger.error(f"Failed to analyze {address}: {e}")
    
    def _calculate_quick_risk(self, analytics: Dict) -> float:
        """Quick risk calculation without full GDS."""
        score = 0.0
        for alert_list in analytics.values():
            score += len(alert_list) * 10
        return min(100, score)
    
    def get_stats(self) -> Dict:
        """Get monitoring statistics."""
        return {
            "status": "running" if self.stats["start_time"] else "not_started",
            "stats": self.stats,
            "monitored_addresses_count": len(self.monitored_addresses)
        }


def start_monitor(
    min_value_usd: float = 100000.0,
    check_interval_minutes: int = 60,
    duration_hours: Optional[int] = None
) -> Dict:
    """
    Convenience function to start blockchain monitoring.
    
    Args:
        min_value_usd: Minimum transaction value to flag
        check_interval_minutes: How often to check
        duration_hours: How long to run (None = run once)
    
    Returns:
        Monitoring statistics
    """
    monitor = BlockchainMonitor(
        min_value_usd=min_value_usd,
        check_interval_seconds=check_interval_minutes * 60,
        auto_analyze=True
    )
    
    if duration_hours:
        return monitor.start_monitoring(duration_hours=duration_hours)
    else:
        return monitor.check_once()

