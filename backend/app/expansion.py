"""
Auto-Expansion System - Reactive Address Investigation
Automatically expands investigation when high-risk addresses are detected.
"""
import logging
from typing import List, Dict, Set, Optional
from datetime import datetime
from .core import driver, ingest_address
from .aml_analytics import run_all_analytics
from .ml_models import get_address_risk_score, run_gds_feature_engineering

logger = logging.getLogger("aml.expansion")


class AutoExpansion:
    """
    Automatically expands investigation to connected addresses when risks are detected.
    """
    
    def __init__(
        self,
        trigger_risk_score: float = 70.0,
        expansion_depth: int = 2,
        min_connection_value_eth: float = 0.5,
        max_addresses_per_expansion: int = 50,
        analyze_connected: bool = True
    ):
        self.trigger_risk_score = trigger_risk_score
        self.expansion_depth = expansion_depth
        self.min_connection_value_eth = min_connection_value_eth
        self.max_addresses_per_expansion = max_addresses_per_expansion
        self.analyze_connected = analyze_connected
        
        self.expanded_addresses: Set[str] = set()
        self.expansion_map: Dict[str, List[str]] = {}
        self.stats = {
            "initial_addresses": 0,
            "expansions_triggered": 0,
            "total_addresses_analyzed": 0,
            "high_risk_found": 0
        }
    
    def analyze_with_expansion(self, initial_address: str) -> Dict:
        """
        Analyze an address and automatically expand if high risk is detected.
        
        Args:
            initial_address: Starting address
        
        Returns:
            Complete analysis with expansion results
        """
        logger.info(f"Starting analysis with auto-expansion for {initial_address}")
        self.stats["initial_addresses"] = 1
        
        results = {
            "initial_address": initial_address,
            "initial_analysis": None,
            "expansions": [],
            "stats": self.stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Analyze initial address
        initial_analysis = self._full_analysis(initial_address)
        results["initial_analysis"] = initial_analysis
        self.expanded_addresses.add(initial_address.lower())
        
        if not initial_analysis:
            logger.warning(f"Could not analyze initial address {initial_address}")
            return results
        
        # Check if expansion is needed
        risk_score = initial_analysis.get("risk_score", 0)
        logger.info(f"Initial address risk score: {risk_score:.1f}")
        
        if risk_score >= self.trigger_risk_score:
            logger.info(f"Risk score {risk_score:.1f} >= trigger {self.trigger_risk_score}. Expanding...")
            expansion_results = self._expand_from_address(initial_address, depth=0)
            results["expansions"] = expansion_results
        else:
            logger.info(f"Risk score {risk_score:.1f} below trigger. No expansion needed.")
        
        results["stats"] = self.stats
        return results
    
    def _expand_from_address(self, address: str, depth: int) -> List[Dict]:
        """
        Recursively expand investigation from a high-risk address.
        
        Args:
            address: Address to expand from
            depth: Current depth level
        
        Returns:
            List of expansion results
        """
        if depth >= self.expansion_depth:
            logger.info(f"Max expansion depth {self.expansion_depth} reached")
            return []
        
        expansion_results = []
        
        # Get connected addresses
        connected = self._get_connected_addresses(address)
        logger.info(f"Found {len(connected)} connected addresses to {address}")
        
        self.expansion_map[address] = connected
        self.stats["expansions_triggered"] += 1
        
        # Analyze each connected address
        for conn_addr in connected:
            if conn_addr in self.expanded_addresses:
                continue
            
            logger.info(f"Analyzing connected address {conn_addr} (depth {depth+1})")
            
            analysis = self._full_analysis(conn_addr)
            self.expanded_addresses.add(conn_addr)
            self.stats["total_addresses_analyzed"] += 1
            
            if not analysis:
                continue
            
            expansion_result = {
                "address": conn_addr,
                "parent_address": address,
                "depth": depth + 1,
                "analysis": analysis
            }
            expansion_results.append(expansion_result)
            
            risk_score = analysis.get("risk_score", 0)
            if risk_score >= self.trigger_risk_score:
                self.stats["high_risk_found"] += 1
                logger.info(f"High risk detected in {conn_addr} ({risk_score:.1f}). Expanding further...")
                
                # Recursive expansion
                sub_expansions = self._expand_from_address(conn_addr, depth + 1)
                expansion_result["sub_expansions"] = sub_expansions
        
        return expansion_results
    
    def _full_analysis(self, address: str) -> Optional[Dict]:
        """
        Perform complete analysis: ingest, detect patterns, calculate risk.
        
        Args:
            address: Address to analyze
        
        Returns:
            Analysis results or None if failed
        """
        try:
            # Ingest transactions
            ingest_result = ingest_address(address, limit=500)
            if ingest_result.get("ingested", 0) == 0:
                logger.warning(f"No transactions found for {address}")
                return None
            
            # Run AML analytics
            with driver.session() as session:
                analytics = session.execute_write(lambda tx: run_all_analytics(tx, address))
            
            # Calculate risk score (simplified for speed)
            alert_count = sum(len(v) for v in analytics.values())
            risk_score = self._calculate_risk_score(analytics)
            
            return {
                "address": address,
                "risk_score": risk_score,
                "alert_count": alert_count,
                "alerts": analytics,
                "transactions_ingested": ingest_result.get("ingested", 0)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing {address}: {e}")
            return None
    
    def _calculate_risk_score(self, analytics: Dict) -> float:
        """Calculate risk score from analytics results."""
        score = 0.0
        
        weights = {
            "structuring": 15,
            "peel_chains": 25,
            "mixer_activity": 30,
            "taint": 25,
            "circularity": 20
        }
        
        for alert_type, alerts in analytics.items():
            if alerts and alert_type in weights:
                score += min(weights[alert_type] * 2, len(alerts) * weights[alert_type])
        
        return min(100, score)
    
    def _get_connected_addresses(self, address: str) -> List[str]:
        """
        Get addresses with significant connections to the given address.
        
        Args:
            address: Source address
        
        Returns:
            List of connected addresses
        """
        cypher = """
        MATCH (a:Address {address: $address})-[r:TRANSFER]-(other:Address)
        WHERE r.value_sum >= $min_value
        WITH other, sum(r.value_sum) AS total_value
        ORDER BY total_value DESC
        RETURN other.address AS address
        LIMIT $limit
        """
        
        with driver.session() as session:
            records = session.execute_read(
                lambda tx: list(tx.run(
                    cypher,
                    address=address,
                    min_value=self.min_connection_value_eth,
                    limit=self.max_addresses_per_expansion
                ))
            )
        
        return [rec["address"].lower() for rec in records if rec["address"]]


def analyze_with_auto_expansion(
    address: str,
    trigger_score: float = 70.0,
    expansion_depth: int = 2,
    min_value_eth: float = 0.5
) -> Dict:
    """
    Convenience function to analyze an address with automatic expansion.
    
    Args:
        address: Initial address to analyze
        trigger_score: Risk score that triggers expansion
        expansion_depth: How many levels to expand
        min_value_eth: Minimum connection value to follow
    
    Returns:
        Complete analysis with expansion results
    """
    expander = AutoExpansion(
        trigger_risk_score=trigger_score,
        expansion_depth=expansion_depth,
        min_connection_value_eth=min_value_eth
    )
    
    return expander.analyze_with_expansion(address)

