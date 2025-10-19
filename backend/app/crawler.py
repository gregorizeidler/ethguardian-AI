"""
Blockchain Crawler - Autonomous AML Address Discovery
Crawls the blockchain graph starting from seed addresses to find suspicious activity.
"""
import time
import logging
from typing import List, Dict, Set, Optional
from datetime import datetime
from .core import driver, ingest_address
from .aml_analytics import run_all_analytics
from .ml_models import get_address_risk_score, run_gds_feature_engineering

logger = logging.getLogger("aml.crawler")


class BlockchainCrawler:
    """
    Autonomous crawler that explores blockchain connections to find suspicious addresses.
    """
    
    def __init__(
        self,
        seed_addresses: List[str],
        max_depth: int = 3,
        min_transaction_value_eth: float = 1.0,
        min_risk_score_to_expand: float = 60.0,
        max_addresses: int = 5000,
        transaction_limit_per_address: int = 1000
    ):
        self.seed_addresses = seed_addresses
        self.max_depth = max_depth
        self.min_transaction_value_eth = min_transaction_value_eth
        self.min_risk_score_to_expand = min_risk_score_to_expand
        self.max_addresses = max_addresses
        self.transaction_limit_per_address = transaction_limit_per_address
        
        self.visited: Set[str] = set()
        self.to_analyze: List[tuple] = []  # (address, depth)
        self.suspicious_found: List[Dict] = []
        self.stats = {
            "addresses_analyzed": 0,
            "suspicious_found": 0,
            "total_alerts": 0,
            "start_time": None,
            "end_time": None
        }
    
    def crawl(self) -> Dict:
        """
        Main crawl execution - explores blockchain from seed addresses.
        
        Returns:
            Dict with crawl statistics and found suspicious addresses
        """
        logger.info(f"Starting blockchain crawl with {len(self.seed_addresses)} seeds")
        self.stats["start_time"] = datetime.utcnow().isoformat()
        
        # Initialize queue with seed addresses
        for seed in self.seed_addresses:
            self.to_analyze.append((seed.lower(), 0))
        
        while self.to_analyze and len(self.visited) < self.max_addresses:
            address, depth = self.to_analyze.pop(0)
            
            if address in self.visited or depth > self.max_depth:
                continue
            
            logger.info(f"Analyzing {address} at depth {depth} ({len(self.visited)}/{self.max_addresses})")
            self.visited.add(address)
            
            # Ingest and analyze
            try:
                result = self._analyze_address(address, depth)
                if result:
                    self.suspicious_found.append(result)
                    self.stats["suspicious_found"] += 1
                    
                    # Expand to connected addresses if risky enough
                    if result["risk_score"] >= self.min_risk_score_to_expand and depth < self.max_depth:
                        connected = self._get_connected_addresses(address)
                        for conn in connected:
                            if conn not in self.visited:
                                self.to_analyze.append((conn, depth + 1))
                
                self.stats["addresses_analyzed"] += 1
                time.sleep(0.2)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Error analyzing {address}: {e}")
                continue
        
        self.stats["end_time"] = datetime.utcnow().isoformat()
        logger.info(f"Crawl complete. Found {self.stats['suspicious_found']} suspicious addresses")
        
        return {
            "status": "completed",
            "stats": self.stats,
            "suspicious_addresses": self.suspicious_found
        }
    
    def _analyze_address(self, address: str, depth: int) -> Optional[Dict]:
        """
        Ingest, analyze and score an address.
        
        Returns:
            Dict with analysis results if suspicious, None otherwise
        """
        # Ingest transactions
        try:
            ingest_result = ingest_address(address, limit=self.transaction_limit_per_address)
            if ingest_result.get("ingested", 0) == 0:
                return None
        except Exception as e:
            logger.warning(f"Failed to ingest {address}: {e}")
            return None
        
        # Run AML analytics
        try:
            with driver.session() as session:
                analytics = session.execute_write(lambda tx: run_all_analytics(tx, address))
                self.stats["total_alerts"] += sum(len(v) for v in analytics.values())
        except Exception as e:
            logger.warning(f"Failed to run analytics for {address}: {e}")
            analytics = {}
        
        # Calculate risk score (skip GDS for speed, use heuristics only)
        try:
            # Quick risk score based on alerts only
            risk_score = self._calculate_quick_risk_score(address, analytics)
        except Exception as e:
            logger.warning(f"Failed to score {address}: {e}")
            risk_score = 0
        
        # Only return if suspicious
        if risk_score >= 40:  # Lower threshold for crawler
            return {
                "address": address,
                "depth": depth,
                "risk_score": risk_score,
                "alerts": analytics,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return None
    
    def _calculate_quick_risk_score(self, address: str, analytics: Dict) -> float:
        """Calculate risk score based on alerts without full GDS."""
        score = 0.0
        
        # Count alerts by type
        for alert_type, alerts in analytics.items():
            if not alerts:
                continue
            
            if alert_type == "structuring":
                score += min(30, len(alerts) * 15)
            elif alert_type == "peel_chains":
                score += min(40, len(alerts) * 20)
            elif alert_type == "mixer_activity":
                score += min(50, len(alerts) * 25)
            elif alert_type == "taint":
                score += min(40, len(alerts) * 20)
            elif alert_type == "circularity":
                score += min(35, len(alerts) * 15)
        
        return min(100, score)
    
    def _get_connected_addresses(self, address: str) -> List[str]:
        """
        Get addresses connected to the given address with significant transactions.
        
        Returns:
            List of connected addresses
        """
        cypher = """
        MATCH (a:Address {address: $address})-[r:TRANSFER]-(other:Address)
        WHERE r.value_sum >= $min_value
        RETURN DISTINCT other.address AS address
        LIMIT 50
        """
        
        with driver.session() as session:
            records = session.execute_read(
                lambda tx: list(tx.run(
                    cypher,
                    address=address,
                    min_value=self.min_transaction_value_eth
                ))
            )
        
        return [rec["address"].lower() for rec in records if rec["address"]]


def run_crawler(
    seed_addresses: List[str],
    max_depth: int = 3,
    min_value_eth: float = 1.0,
    min_risk_score: float = 60.0,
    max_addresses: int = 5000
) -> Dict:
    """
    Convenience function to run a blockchain crawl.
    
    Args:
        seed_addresses: Starting addresses (e.g., known mixers, hacked exchanges)
        max_depth: Maximum hops from seed addresses
        min_value_eth: Minimum transaction value to follow
        min_risk_score: Minimum risk score to expand further
        max_addresses: Maximum addresses to analyze
    
    Returns:
        Crawl results with suspicious addresses found
    """
    crawler = BlockchainCrawler(
        seed_addresses=seed_addresses,
        max_depth=max_depth,
        min_transaction_value_eth=min_value_eth,
        min_risk_score_to_expand=min_risk_score,
        max_addresses=max_addresses
    )
    
    return crawler.crawl()

