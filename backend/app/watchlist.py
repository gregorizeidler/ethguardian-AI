"""
Watchlist Monitoring Module
24/7 monitoring of specific addresses with automatic alerts
"""

from typing import Dict, Any, List, Set
from datetime import datetime
import asyncio
import threading


class WatchlistManager:
    """Manage watchlist of addresses for 24/7 monitoring"""
    
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
        self.watchlist: Dict[str, Dict[str, Any]] = {}
        self.monitoring_active = False
        self.monitor_thread = None
    
    def add_to_watchlist(self, address: str, reason: str = "", tags: List[str] = None, alert_threshold: int = 50) -> Dict[str, Any]:
        """Add address to watchlist"""
        if tags is None:
            tags = []
        
        entry = {
            "address": address,
            "added_at": datetime.now().isoformat(),
            "reason": reason,
            "tags": tags,
            "alert_threshold": alert_threshold,
            "last_check": None,
            "alerts_triggered": 0,
            "status": "active"
        }
        
        self.watchlist[address] = entry
        return {"ok": True, "entry": entry}
    
    def remove_from_watchlist(self, address: str) -> bool:
        """Remove address from watchlist"""
        if address in self.watchlist:
            del self.watchlist[address]
            return True
        return False
    
    def get_watchlist(self) -> List[Dict[str, Any]]:
        """Get all watchlist entries"""
        return list(self.watchlist.values())
    
    def get_watchlist_entry(self, address: str) -> Dict[str, Any]:
        """Get specific watchlist entry"""
        return self.watchlist.get(address)
    
    def update_watchlist_entry(self, address: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update watchlist entry"""
        if address not in self.watchlist:
            return {"ok": False, "error": "Address not in watchlist"}
        
        self.watchlist[address].update(updates)
        return {"ok": True, "entry": self.watchlist[address]}
    
    def check_address(self, address: str) -> Dict[str, Any]:
        """Check a single watchlist address for new activity"""
        from .pattern_detection import PatternDetector
        from .fraud_detection import FraudDetector
        from .alerting import alert_manager
        
        pattern_detector = PatternDetector(self.driver)
        fraud_detector = FraudDetector(self.driver)
        
        try:
            # Run analyses
            patterns = pattern_detector.detect_all_patterns(address)
            fraud = fraud_detector.detect_all_fraud_types(address)
            
            # Get highest risk score
            risk_score = max(
                patterns.get("overall_pattern_score", 0),
                fraud.get("overall_fraud_score", 0)
            )
            
            # Update last check time
            self.watchlist[address]["last_check"] = datetime.now().isoformat()
            
            # Check if alert threshold exceeded
            entry = self.watchlist[address]
            if risk_score >= entry["alert_threshold"]:
                # Trigger alert
                alert = alert_manager.create_alert(
                    alert_type="WATCHLIST_ALERT",
                    address=address,
                    risk_score=int(risk_score),
                    details={
                        "watchlist_reason": entry["reason"],
                        "tags": entry["tags"],
                        "patterns": patterns,
                        "fraud": fraud
                    }
                )
                alert_manager.process_alert(alert)
                
                entry["alerts_triggered"] += 1
                
                return {
                    "address": address,
                    "alert_triggered": True,
                    "risk_score": risk_score,
                    "patterns": patterns,
                    "fraud": fraud
                }
            
            return {
                "address": address,
                "alert_triggered": False,
                "risk_score": risk_score
            }
            
        except Exception as e:
            return {
                "address": address,
                "error": str(e)
            }
    
    def check_all_addresses(self) -> List[Dict[str, Any]]:
        """Check all watchlist addresses"""
        results = []
        for address in list(self.watchlist.keys()):
            if self.watchlist[address]["status"] == "active":
                result = self.check_address(address)
                results.append(result)
        return results
    
    def start_monitoring(self, check_interval_minutes: int = 60):
        """Start continuous monitoring"""
        if self.monitoring_active:
            return {"ok": False, "message": "Monitoring already active"}
        
        self.monitoring_active = True
        
        def monitor_loop():
            while self.monitoring_active:
                print(f"[Watchlist] Checking {len(self.watchlist)} addresses...")
                results = self.check_all_addresses()
                alerts = sum(1 for r in results if r.get("alert_triggered"))
                print(f"[Watchlist] Check complete. {alerts} alerts triggered.")
                
                # Sleep for interval
                for _ in range(check_interval_minutes * 60):
                    if not self.monitoring_active:
                        break
                    asyncio.sleep(1)
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        return {"ok": True, "message": "Monitoring started"}
    
    def stop_monitoring(self):
        """Stop continuous monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        return {"ok": True, "message": "Monitoring stopped"}
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get monitoring status"""
        return {
            "monitoring_active": self.monitoring_active,
            "watchlist_size": len(self.watchlist),
            "active_addresses": sum(1 for e in self.watchlist.values() if e["status"] == "active"),
            "total_alerts_triggered": sum(e["alerts_triggered"] for e in self.watchlist.values())
        }


# Global watchlist manager
watchlist_manager = None

def get_watchlist_manager(driver):
    """Get or create watchlist manager"""
    global watchlist_manager
    if watchlist_manager is None:
        watchlist_manager = WatchlistManager(driver)
    return watchlist_manager

