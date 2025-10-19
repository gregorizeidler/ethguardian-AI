"""
EthGuardian API Client
"""

import requests
from typing import Dict, Any, List, Optional


class EthGuardianClient:
    """Python SDK for EthGuardian API"""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        """
        Initialize EthGuardian client
        
        Args:
            base_url: Base URL of the API
            api_key: Optional API key for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})
    
    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make GET request"""
        url = f"{self.base_url}/api{endpoint}"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def _post(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make POST request"""
        url = f"{self.base_url}/api{endpoint}"
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def _put(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make PUT request"""
        url = f"{self.base_url}/api{endpoint}"
        response = self.session.put(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def _delete(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make DELETE request"""
        url = f"{self.base_url}/api{endpoint}"
        response = self.session.delete(url, params=params)
        response.raise_for_status()
        return response.json()
    
    # Core Analysis Methods
    def ingest(self, address: str) -> Dict[str, Any]:
        """Ingest address data from blockchain"""
        return self._post(f"/ingest/{address}")
    
    def analyze(self, address: str) -> Dict[str, Any]:
        """Run full analysis on address"""
        return self._post(f"/analyze/{address}")
    
    def get_profile(self, address: str) -> Dict[str, Any]:
        """Get address profile"""
        return self._get(f"/profile/{address}")
    
    def get_graph(self, address: str) -> Dict[str, Any]:
        """Get transaction graph"""
        return self._get(f"/graph/{address}")
    
    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get all alerts"""
        return self._get("/alerts")
    
    # Pattern Detection
    def detect_patterns(self, address: str) -> Dict[str, Any]:
        """Detect suspicious patterns"""
        return self._get(f"/patterns/{address}")
    
    def detect_layering(self, address: str) -> Dict[str, Any]:
        """Detect layering patterns"""
        return self._get(f"/patterns/{address}/layering")
    
    def detect_peel_chains(self, address: str) -> Dict[str, Any]:
        """Detect peel chain patterns"""
        return self._get(f"/patterns/{address}/peel-chains")
    
    def detect_wash_trading(self, address: str) -> Dict[str, Any]:
        """Detect wash trading"""
        return self._get(f"/patterns/{address}/wash-trading")
    
    # Fraud Detection
    def detect_fraud(self, address: str) -> Dict[str, Any]:
        """Detect fraud patterns"""
        return self._get(f"/fraud/{address}")
    
    def detect_rug_pull(self, address: str) -> Dict[str, Any]:
        """Detect rug pull pattern"""
        return self._get(f"/fraud/{address}/rug-pull")
    
    def detect_ponzi(self, address: str) -> Dict[str, Any]:
        """Detect Ponzi scheme"""
        return self._get(f"/fraud/{address}/ponzi")
    
    def detect_phishing(self, address: str) -> Dict[str, Any]:
        """Detect phishing"""
        return self._get(f"/fraud/{address}/phishing")
    
    def detect_mev_bot(self, address: str) -> Dict[str, Any]:
        """Detect MEV bot"""
        return self._get(f"/fraud/{address}/mev-bot")
    
    # Advanced Detection
    def detect_mixer_usage(self, address: str) -> Dict[str, Any]:
        """Detect mixer/tumbler usage"""
        return self._get(f"/advanced/mixer/{address}")
    
    def analyze_smart_contracts(self, address: str) -> Dict[str, Any]:
        """Analyze smart contract interactions"""
        return self._get(f"/advanced/contracts/{address}")
    
    def analyze_token_holdings(self, address: str) -> Dict[str, Any]:
        """Analyze token holdings"""
        return self._get(f"/advanced/tokens/{address}")
    
    def detect_bridge_usage(self, address: str) -> Dict[str, Any]:
        """Detect bridge usage"""
        return self._get(f"/advanced/bridges/{address}")
    
    def analyze_all_advanced(self, address: str) -> Dict[str, Any]:
        """Run all advanced detection"""
        return self._get(f"/advanced/all/{address}")
    
    # NFT Fraud
    def detect_nft_wash_trading(self, address: str) -> Dict[str, Any]:
        """Detect NFT wash trading"""
        return self._get(f"/nft/wash-trading/{address}")
    
    def detect_fake_collection(self, contract: str) -> Dict[str, Any]:
        """Detect fake NFT collection"""
        return self._get(f"/nft/fake-collection/{contract}")
    
    def track_stolen_nft(self, contract: str, token_id: str) -> Dict[str, Any]:
        """Track stolen NFT"""
        return self._get(f"/nft/stolen/{contract}/{token_id}")
    
    # Machine Learning
    def predict_future_risk(self, address: str, forecast_days: int = 7) -> Dict[str, Any]:
        """LSTM-based risk prediction"""
        return self._get(f"/ml/lstm/{address}", {"forecast_days": forecast_days})
    
    def detect_anomalies_ml(self, address: str) -> Dict[str, Any]:
        """Autoencoder anomaly detection"""
        return self._get(f"/ml/autoencoder/{address}")
    
    def hierarchical_clustering(self, min_addresses: int = 10) -> Dict[str, Any]:
        """Hierarchical clustering"""
        return self._get("/ml/clustering", {"min_addresses": min_addresses})
    
    def deep_pattern_recognition(self, address: str) -> Dict[str, Any]:
        """Deep learning pattern recognition"""
        return self._get(f"/ml/deep-pattern/{address}")
    
    # Cross-Chain
    def detect_cross_chain_movement(self, address: str, chain: str = "ethereum") -> Dict[str, Any]:
        """Detect cross-chain movement"""
        return self._get(f"/cross-chain/movement/{address}", {"chain": chain})
    
    def correlate_addresses(self, address: str) -> Dict[str, Any]:
        """Correlate addresses across chains"""
        return self._get(f"/cross-chain/correlation/{address}")
    
    def assess_multi_chain_risk(self, address: str) -> Dict[str, Any]:
        """Assess multi-chain risk"""
        return self._get(f"/cross-chain/risk/{address}")
    
    # Case Management
    def create_case(self, title: str, address: str, case_type: str, priority: str,
                   assigned_to: str, created_by: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Create investigation case"""
        data = {
            "title": title,
            "address": address,
            "case_type": case_type,
            "priority": priority,
            "assigned_to": assigned_to,
            "created_by": created_by,
            "description": description
        }
        return self._post("/cases/create", data)
    
    def get_case(self, case_id: str, user: str, user_role: str) -> Dict[str, Any]:
        """Get case details"""
        return self._get(f"/cases/{case_id}", {"user": user, "user_role": user_role})
    
    def add_evidence(self, case_id: str, evidence_type: str, description: str,
                    source: str, added_by: str, user_role: str) -> Dict[str, Any]:
        """Add evidence to case"""
        data = {
            "evidence_type": evidence_type,
            "description": description,
            "source": source,
            "added_by": added_by,
            "user_role": user_role
        }
        return self._post(f"/cases/{case_id}/evidence", data)
    
    def get_user_cases(self, user: str, user_role: str, status_filter: Optional[str] = None) -> Dict[str, Any]:
        """Get all cases for user"""
        params = {"user_role": user_role}
        if status_filter:
            params["status_filter"] = status_filter
        return self._get(f"/cases/user/{user}", params)
    
    # Compliance
    def generate_sar(self, address: str, analyst: str, findings: str) -> Dict[str, Any]:
        """Generate SAR report"""
        data = {"address": address, "analyst": analyst, "findings": findings}
        return self._post("/compliance/sar", data)
    
    def generate_ctr(self, address: str, amount: float, analyst: str) -> Dict[str, Any]:
        """Generate CTR report"""
        data = {"address": address, "amount": amount, "analyst": analyst}
        return self._post("/compliance/ctr", data)
    
    def check_compliance(self, address: str) -> Dict[str, Any]:
        """Check compliance status"""
        return self._get(f"/compliance/check/{address}")
    
    # Reports
    def generate_pdf_report(self, address: str) -> Dict[str, Any]:
        """Generate PDF report"""
        data = {"address": address, "format": "pdf"}
        return self._post("/reports/pdf", data)
    
    def generate_excel_report(self, address: str) -> Dict[str, Any]:
        """Generate Excel report"""
        data = {"address": address}
        return self._post("/reports/excel", data)
    
    # Watchlist
    def add_to_watchlist(self, address: str, reason: str, added_by: str,
                        risk_threshold: int = 70, auto_alert: bool = True) -> Dict[str, Any]:
        """Add address to watchlist"""
        data = {
            "address": address,
            "reason": reason,
            "added_by": added_by,
            "risk_threshold": risk_threshold,
            "auto_alert": auto_alert
        }
        return self._post("/watchlist/add", data)
    
    def get_watchlist(self) -> Dict[str, Any]:
        """Get all watchlist entries"""
        return self._get("/watchlist")
    
    def remove_from_watchlist(self, address: str) -> Dict[str, Any]:
        """Remove from watchlist"""
        return self._delete(f"/watchlist/{address}")
    
    def start_watchlist_monitoring(self) -> Dict[str, Any]:
        """Start 24/7 watchlist monitoring"""
        return self._post("/watchlist/monitoring/start")
    
    def stop_watchlist_monitoring(self) -> Dict[str, Any]:
        """Stop watchlist monitoring"""
        return self._post("/watchlist/monitoring/stop")
    
    # Bulk Analysis
    def bulk_analyze(self, addresses: List[str], max_workers: int = 5) -> Dict[str, Any]:
        """Analyze multiple addresses in parallel"""
        data = {"addresses": addresses, "max_workers": max_workers}
        return self._post("/bulk/analyze", data)
    
    # Graph Tools
    def shortest_path(self, from_address: str, to_address: str) -> Dict[str, Any]:
        """Find shortest path between addresses"""
        params = {"from_address": from_address, "to_address": to_address}
        return self._get("/graph/shortest-path", params)
    
    def common_neighbors(self, address1: str, address2: str) -> Dict[str, Any]:
        """Find common neighbors"""
        params = {"address1": address1, "address2": address2}
        return self._get("/graph/common-neighbors", params)
    
    def detect_community(self, address: str) -> Dict[str, Any]:
        """Detect community/cluster"""
        return self._get(f"/graph/community/{address}")
    
    # Webhooks
    def register_webhook(self, url: str, events: List[str], user_id: str,
                        secret: Optional[str] = None) -> Dict[str, Any]:
        """Register webhook"""
        data = {
            "url": url,
            "events": events,
            "user_id": user_id,
            "secret": secret
        }
        return self._post("/webhooks/register", data)
    
    def get_user_webhooks(self, user_id: str) -> Dict[str, Any]:
        """Get user webhooks"""
        return self._get(f"/webhooks/user/{user_id}")
    
    def delete_webhook(self, webhook_id: str, user_id: str) -> Dict[str, Any]:
        """Delete webhook"""
        return self._delete(f"/webhooks/{webhook_id}", {"user_id": user_id})
    
    def test_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """Test webhook"""
        return self._post(f"/webhooks/{webhook_id}/test")

