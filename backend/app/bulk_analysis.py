"""
Bulk Address Analysis Module
Analyze thousands of addresses in batch
"""

from typing import Dict, Any, List
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed


class BulkAnalyzer:
    """Analyze multiple addresses in parallel"""
    
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
        self.max_workers = 10
    
    def analyze_address_quick(self, address: str) -> Dict[str, Any]:
        """Quick analysis of single address"""
        from .pattern_detection import PatternDetector
        from .fraud_detection import FraudDetector
        from .ml_models import get_address_risk_score
        
        try:
            pattern_detector = PatternDetector(self.driver)
            fraud_detector = FraudDetector(self.driver)
            
            # Quick checks only
            layering = pattern_detector.detect_layering(address, depth=3, time_window_hours=24)
            wash_trading = pattern_detector.detect_wash_trading(address)
            phishing = fraud_detector.detect_phishing(address)
            risk_score = get_address_risk_score(self.driver, address)
            
            return {
                "address": address,
                "risk_score": risk_score,
                "layering_detected": layering.get("detected", False),
                "wash_trading_detected": wash_trading.get("detected", False),
                "phishing_detected": phishing.get("detected", False),
                "status": "analyzed"
            }
        except Exception as e:
            return {
                "address": address,
                "status": "error",
                "error": str(e)
            }
    
    def bulk_analyze(self, addresses: List[str], parallel: bool = True) -> Dict[str, Any]:
        """
        Analyze multiple addresses
        
        Args:
            addresses: List of addresses to analyze
            parallel: Use parallel processing
        
        Returns:
            Analysis results for all addresses
        """
        start_time = datetime.now()
        results = []
        
        if parallel and len(addresses) > 1:
            # Parallel processing
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_address = {
                    executor.submit(self.analyze_address_quick, addr): addr 
                    for addr in addresses
                }
                
                for future in as_completed(future_to_address):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        addr = future_to_address[future]
                        results.append({
                            "address": addr,
                            "status": "error",
                            "error": str(e)
                        })
        else:
            # Sequential processing
            for addr in addresses:
                result = self.analyze_address_quick(addr)
                results.append(result)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Calculate statistics
        analyzed = sum(1 for r in results if r["status"] == "analyzed")
        errors = sum(1 for r in results if r["status"] == "error")
        high_risk = sum(1 for r in results if r.get("risk_score", 0) > 70)
        
        return {
            "total_addresses": len(addresses),
            "analyzed": analyzed,
            "errors": errors,
            "high_risk_count": high_risk,
            "duration_seconds": duration,
            "addresses_per_second": len(addresses) / duration if duration > 0 else 0,
            "results": results
        }
    
    def bulk_analyze_from_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze addresses from a file (one address per line)"""
        try:
            with open(file_path, 'r') as f:
                addresses = [line.strip() for line in f if line.strip()]
            
            return self.bulk_analyze(addresses)
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to read file: {str(e)}"
            }
    
    def export_results_csv(self, results: List[Dict[str, Any]], output_path: str):
        """Export bulk analysis results to CSV"""
        import csv
        
        with open(output_path, 'w', newline='') as f:
            if not results:
                return
            
            fieldnames = list(results[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)


# Global bulk analyzer
bulk_analyzer = None

def get_bulk_analyzer(driver):
    """Get or create bulk analyzer"""
    global bulk_analyzer
    if bulk_analyzer is None:
        bulk_analyzer = BulkAnalyzer(driver)
    return bulk_analyzer

