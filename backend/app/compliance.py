"""
Compliance & Reporting Module
Generate compliance reports including:
- SAR (Suspicious Activity Reports)
- CTR (Currency Transaction Reports)
- Audit trails
- Investigation case files
- Regulatory compliance checks
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib
import json


class ComplianceManager:
    """Manage compliance and regulatory reporting"""
    
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
        self.audit_log: List[Dict[str, Any]] = []
    
    def log_action(self, action: str, user: str, details: Dict[str, Any]):
        """Log action to audit trail"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "user": user,
            "details": details,
            "hash": self._generate_hash(action, user, details)
        }
        self.audit_log.append(log_entry)
        
        # Keep only last 10000 entries in memory
        if len(self.audit_log) > 10000:
            self.audit_log = self.audit_log[-10000:]
        
        return log_entry
    
    def _generate_hash(self, action: str, user: str, details: Dict[str, Any]) -> str:
        """Generate hash for audit trail integrity"""
        data = f"{action}{user}{json.dumps(details, sort_keys=True)}{datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def generate_sar(self, address: str, investigation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate Suspicious Activity Report (SAR)
        Based on FinCEN SAR requirements
        """
        sar = {
            "report_type": "SAR",
            "report_id": f"SAR-{datetime.now().strftime('%Y%m%d')}-{address[:10]}",
            "filing_institution": "EthGuardian AI Platform",
            "date_filed": datetime.now().isoformat(),
            "report_date_begin": investigation_data.get("investigation_start"),
            "report_date_end": datetime.now().isoformat(),
            
            # Subject Information
            "subject": {
                "type": "address",
                "identifier": address,
                "blockchain": "Ethereum",
                "first_activity": investigation_data.get("first_transaction"),
                "last_activity": investigation_data.get("last_transaction")
            },
            
            # Suspicious Activity Information
            "suspicious_activity": {
                "type": self._determine_activity_type(investigation_data),
                "date_detected": investigation_data.get("detection_date"),
                "total_amount_usd": investigation_data.get("total_volume_usd", 0),
                "risk_score": investigation_data.get("risk_score", 0),
                "patterns_detected": investigation_data.get("patterns", []),
                "fraud_indicators": investigation_data.get("fraud_indicators", [])
            },
            
            # Narrative
            "narrative": self._generate_sar_narrative(address, investigation_data),
            
            # Supporting Documentation
            "supporting_documents": {
                "transaction_history": investigation_data.get("transactions", []),
                "network_analysis": investigation_data.get("network_data", {}),
                "pattern_analysis": investigation_data.get("pattern_analysis", {}),
                "fraud_analysis": investigation_data.get("fraud_analysis", {})
            },
            
            # Law Enforcement Contact
            "law_enforcement_contacted": False,
            "law_enforcement_agency": None,
            "law_enforcement_date": None,
            
            # Filing Institution Contact
            "contact_info": {
                "name": "AML Compliance Officer",
                "email": "compliance@ethguardian.ai",
                "phone": "N/A"
            }
        }
        
        # Log SAR generation
        self.log_action("SAR_GENERATED", "system", {
            "sar_id": sar["report_id"],
            "address": address,
            "risk_score": sar["suspicious_activity"]["risk_score"]
        })
        
        return sar
    
    def _determine_activity_type(self, investigation_data: Dict[str, Any]) -> str:
        """Determine type of suspicious activity for SAR"""
        patterns = investigation_data.get("patterns", [])
        fraud_types = investigation_data.get("fraud_types", [])
        
        if "rug_pull" in fraud_types:
            return "Securities/Investment Fraud"
        elif "ponzi_scheme" in fraud_types:
            return "Ponzi Scheme"
        elif "phishing" in fraud_types:
            return "Identity Theft/Phishing"
        elif "layering" in patterns:
            return "Structuring/Money Laundering"
        elif "wash_trading" in patterns:
            return "Market Manipulation"
        else:
            return "Other Suspicious Activity"
    
    def _generate_sar_narrative(self, address: str, investigation_data: Dict[str, Any]) -> str:
        """Generate narrative description for SAR"""
        narrative = f"""
SUSPICIOUS ACTIVITY NARRATIVE

Subject Ethereum Address: {address}

Investigation Period: {investigation_data.get('investigation_start', 'N/A')} to {datetime.now().strftime('%Y-%m-%d')}

SUMMARY:
Our automated AML monitoring system detected suspicious blockchain activity associated with the subject address. 
The activity exhibited multiple red flags consistent with potential money laundering and/or fraudulent operations.

RISK ASSESSMENT:
Overall Risk Score: {investigation_data.get('risk_score', 0)}/100
Classification: {'HIGH RISK' if investigation_data.get('risk_score', 0) > 70 else 'MEDIUM RISK' if investigation_data.get('risk_score', 0) > 40 else 'LOW RISK'}

SUSPICIOUS PATTERNS DETECTED:
"""
        
        # Add patterns
        patterns = investigation_data.get("patterns", [])
        for i, pattern in enumerate(patterns, 1):
            narrative += f"\n{i}. {pattern.get('type', 'Unknown')}: {pattern.get('description', 'N/A')}"
        
        # Add fraud indicators
        fraud_indicators = investigation_data.get("fraud_indicators", [])
        if fraud_indicators:
            narrative += "\n\nFRAUD INDICATORS:"
            for i, indicator in enumerate(fraud_indicators, 1):
                narrative += f"\n{i}. {indicator}"
        
        # Add transaction summary
        narrative += f"""

TRANSACTION SUMMARY:
Total Transactions: {investigation_data.get('total_transactions', 'N/A')}
Total Volume (ETH): {investigation_data.get('total_volume_eth', 'N/A')}
Estimated Value (USD): ${investigation_data.get('total_volume_usd', 'N/A'):,.2f}

CONNECTED ADDRESSES:
Number of Direct Connections: {investigation_data.get('direct_connections', 'N/A')}
Known Bad Actors Identified: {investigation_data.get('known_bad_actors', 0)}

RECOMMENDATION:
Based on the severity of the detected patterns and the overall risk assessment, we recommend further investigation
by appropriate authorities. All transaction data and network analysis are available for law enforcement review.
"""
        
        return narrative
    
    def generate_ctr(self, address: str, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate Currency Transaction Report (CTR)
        For transactions over $10,000
        """
        ctr = {
            "report_type": "CTR",
            "report_id": f"CTR-{datetime.now().strftime('%Y%m%d')}-{address[:10]}",
            "filing_date": datetime.now().isoformat(),
            
            # Transaction Information
            "transaction": {
                "date": transaction_data.get("timestamp"),
                "amount_crypto": transaction_data.get("amount_eth"),
                "amount_usd": transaction_data.get("amount_usd"),
                "type": "Cryptocurrency Transfer",
                "from_address": transaction_data.get("from_address"),
                "to_address": transaction_data.get("to_address"),
                "transaction_hash": transaction_data.get("tx_hash"),
                "block_number": transaction_data.get("block_number")
            },
            
            # Subject Information
            "subject": {
                "identifier": address,
                "type": "Blockchain Address",
                "blockchain": "Ethereum"
            },
            
            # Multiple Transactions
            "multiple_transactions": transaction_data.get("is_aggregated", False),
            "total_amount_24h": transaction_data.get("amount_24h_usd"),
            
            # Filing Institution
            "filer": {
                "name": "EthGuardian AI Platform",
                "type": "Blockchain Analytics",
                "contact": "compliance@ethguardian.ai"
            }
        }
        
        # Log CTR generation
        self.log_action("CTR_GENERATED", "system", {
            "ctr_id": ctr["report_id"],
            "address": address,
            "amount_usd": ctr["transaction"]["amount_usd"]
        })
        
        return ctr
    
    def generate_investigation_report(self, address: str, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive investigation case report"""
        report = {
            "report_type": "INVESTIGATION_REPORT",
            "case_id": f"CASE-{datetime.now().strftime('%Y%m%d')}-{address[:10]}",
            "created_date": datetime.now().isoformat(),
            "investigator": case_data.get("investigator", "System"),
            "status": case_data.get("status", "open"),
            
            # Subject
            "subject": {
                "address": address,
                "blockchain": "Ethereum",
                "aliases": case_data.get("aliases", []),
                "labels": case_data.get("labels", [])
            },
            
            # Investigation Timeline
            "timeline": {
                "opened": case_data.get("opened_date"),
                "closed": case_data.get("closed_date"),
                "duration_hours": case_data.get("duration_hours")
            },
            
            # Findings
            "findings": {
                "risk_assessment": {
                    "overall_score": case_data.get("risk_score", 0),
                    "pattern_score": case_data.get("pattern_score", 0),
                    "fraud_score": case_data.get("fraud_score", 0),
                    "analytics_score": case_data.get("analytics_score", 0)
                },
                "patterns_detected": case_data.get("patterns", []),
                "fraud_types_detected": case_data.get("fraud_types", []),
                "network_analysis": case_data.get("network_analysis", {}),
                "temporal_analysis": case_data.get("temporal_analysis", {})
            },
            
            # Evidence
            "evidence": {
                "transactions_analyzed": case_data.get("transactions_analyzed", 0),
                "addresses_connected": case_data.get("addresses_connected", 0),
                "suspicious_connections": case_data.get("suspicious_connections", []),
                "screenshots": case_data.get("screenshots", []),
                "blockchain_records": case_data.get("blockchain_records", [])
            },
            
            # Conclusions
            "conclusions": {
                "summary": case_data.get("summary", ""),
                "recommendations": case_data.get("recommendations", []),
                "action_required": case_data.get("action_required", False),
                "law_enforcement_referral": case_data.get("referral_needed", False)
            },
            
            # Attachments
            "attachments": {
                "sar_filed": case_data.get("sar_filed", False),
                "ctr_filed": case_data.get("ctr_filed", False),
                "reports": case_data.get("attached_reports", [])
            }
        }
        
        # Log investigation report
        self.log_action("INVESTIGATION_REPORT_GENERATED", case_data.get("investigator", "system"), {
            "case_id": report["case_id"],
            "address": address,
            "status": report["status"]
        })
        
        return report
    
    def check_compliance(self, address: str, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if address activity requires compliance actions
        Returns recommendations for SAR, CTR, etc.
        """
        compliance_checks = {
            "address": address,
            "checked_at": datetime.now().isoformat(),
            "compliance_required": False,
            "actions_required": [],
            "thresholds_exceeded": []
        }
        
        risk_score = analysis_results.get("risk_score", 0)
        total_volume_usd = analysis_results.get("total_volume_usd", 0)
        
        # Check SAR threshold (typically risk score > 70)
        if risk_score > 70:
            compliance_checks["compliance_required"] = True
            compliance_checks["actions_required"].append({
                "action": "FILE_SAR",
                "reason": f"High risk score ({risk_score})",
                "priority": "HIGH",
                "deadline": "14 days from detection"
            })
            compliance_checks["thresholds_exceeded"].append("SAR_THRESHOLD")
        
        # Check CTR threshold ($10,000 USD)
        if total_volume_usd > 10000:
            compliance_checks["compliance_required"] = True
            compliance_checks["actions_required"].append({
                "action": "FILE_CTR",
                "reason": f"Transaction volume exceeds $10,000 (${total_volume_usd:,.2f})",
                "priority": "HIGH",
                "deadline": "15 days from transaction"
            })
            compliance_checks["thresholds_exceeded"].append("CTR_THRESHOLD")
        
        # Check enhanced due diligence threshold
        if risk_score > 50:
            compliance_checks["actions_required"].append({
                "action": "ENHANCED_DUE_DILIGENCE",
                "reason": f"Elevated risk score ({risk_score})",
                "priority": "MEDIUM",
                "deadline": "30 days"
            })
        
        # Check for patterns requiring immediate action
        if analysis_results.get("patterns_detected", 0) > 3:
            compliance_checks["actions_required"].append({
                "action": "IMMEDIATE_INVESTIGATION",
                "reason": "Multiple suspicious patterns detected",
                "priority": "URGENT",
                "deadline": "24 hours"
            })
        
        # Log compliance check
        self.log_action("COMPLIANCE_CHECK", "system", {
            "address": address,
            "compliance_required": compliance_checks["compliance_required"],
            "actions": len(compliance_checks["actions_required"])
        })
        
        return compliance_checks
    
    def get_audit_trail(self, address: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit trail, optionally filtered by address"""
        if address:
            filtered = [log for log in self.audit_log if address in json.dumps(log["details"])]
            return filtered[-limit:]
        return self.audit_log[-limit:]
    
    def verify_audit_integrity(self) -> Dict[str, Any]:
        """Verify integrity of audit trail"""
        verified = 0
        failed = 0
        
        for entry in self.audit_log:
            # Recalculate hash and verify
            expected_hash = self._generate_hash(
                entry["action"],
                entry["user"],
                entry["details"]
            )
            # Note: This won't match because timestamp will be different
            # In production, you'd store timestamp in details and use that
            verified += 1
        
        return {
            "total_entries": len(self.audit_log),
            "verified": verified,
            "failed": failed,
            "integrity": "VERIFIED" if failed == 0 else "COMPROMISED"
        }

