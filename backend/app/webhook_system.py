"""
Webhook System
Send real-time notifications via HTTP webhooks
"""

from typing import Dict, Any, List, Optional
import requests
import json
from datetime import datetime
import hashlib
import hmac


class WebhookManager:
    """Manage webhook subscriptions and delivery"""
    
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
        
        # Webhook events
        self.events = [
            "alert.created",
            "alert.updated",
            "case.created",
            "case.updated",
            "case.closed",
            "analysis.completed",
            "transaction.detected",
            "risk.threshold_exceeded"
        ]
    
    def register_webhook(self, url: str, events: List[str], user_id: str, 
                        secret: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
        """Register a new webhook endpoint"""
        
        # Validate events
        invalid_events = [e for e in events if e not in self.events]
        if invalid_events:
            return {
                "error": f"Invalid events: {invalid_events}",
                "valid_events": self.events
            }
        
        webhook_id = f"wh_{int(datetime.now().timestamp())}_{user_id}"
        
        query = """
        CREATE (w:Webhook {
            webhook_id: $webhook_id,
            url: $url,
            events: $events,
            user_id: $user_id,
            secret: $secret,
            description: $description,
            active: true,
            created_at: $timestamp,
            delivery_count: 0,
            failure_count: 0
        })
        RETURN w
        """
        
        with self.driver.session() as session:
            result = session.run(
                query,
                webhook_id=webhook_id,
                url=url,
                events=events,
                user_id=user_id,
                secret=secret or "",
                description=description or "",
                timestamp=int(datetime.now().timestamp())
            )
            
            return {
                "webhook_id": webhook_id,
                "url": url,
                "events": events,
                "active": True,
                "message": "Webhook registered successfully"
            }
    
    def send_webhook(self, event: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send webhook to all subscribed endpoints"""
        
        # Get all active webhooks subscribed to this event
        query = """
        MATCH (w:Webhook)
        WHERE w.active = true AND $event IN w.events
        RETURN w
        """
        
        with self.driver.session() as session:
            result = session.run(query, event=event)
            webhooks = list(result)
            
            delivery_results = []
            
            for record in webhooks:
                webhook = dict(record["w"])
                
                # Prepare payload
                webhook_payload = {
                    "event": event,
                    "timestamp": datetime.now().isoformat(),
                    "data": payload
                }
                
                # Add signature if secret is configured
                signature = None
                if webhook.get("secret"):
                    signature = self._generate_signature(
                        json.dumps(webhook_payload),
                        webhook["secret"]
                    )
                
                # Send HTTP POST request
                delivery_result = self._deliver_webhook(
                    webhook["webhook_id"],
                    webhook["url"],
                    webhook_payload,
                    signature
                )
                
                delivery_results.append(delivery_result)
            
            return {
                "event": event,
                "webhooks_triggered": len(webhooks),
                "successful_deliveries": len([r for r in delivery_results if r["success"]]),
                "failed_deliveries": len([r for r in delivery_results if not r["success"]]),
                "results": delivery_results
            }
    
    def _deliver_webhook(self, webhook_id: str, url: str, payload: Dict[str, Any], 
                        signature: Optional[str] = None) -> Dict[str, Any]:
        """Deliver webhook to endpoint"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "EthGuardian-Webhook/1.0"
        }
        
        if signature:
            headers["X-Webhook-Signature"] = signature
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            success = response.status_code < 400
            
            # Update delivery stats
            self._update_delivery_stats(webhook_id, success)
            
            # Log delivery
            self._log_delivery(webhook_id, success, response.status_code)
            
            return {
                "webhook_id": webhook_id,
                "url": url,
                "success": success,
                "status_code": response.status_code,
                "response": response.text[:200]  # First 200 chars
            }
        
        except requests.exceptions.RequestException as e:
            # Update failure stats
            self._update_delivery_stats(webhook_id, False)
            
            # Log delivery failure
            self._log_delivery(webhook_id, False, 0, str(e))
            
            return {
                "webhook_id": webhook_id,
                "url": url,
                "success": False,
                "error": str(e)
            }
    
    def _generate_signature(self, payload: str, secret: str) -> str:
        """Generate HMAC signature for webhook payload"""
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def _update_delivery_stats(self, webhook_id: str, success: bool):
        """Update delivery statistics"""
        if success:
            query = """
            MATCH (w:Webhook {webhook_id: $webhook_id})
            SET w.delivery_count = w.delivery_count + 1,
                w.last_delivery = timestamp()
            """
        else:
            query = """
            MATCH (w:Webhook {webhook_id: $webhook_id})
            SET w.failure_count = w.failure_count + 1,
                w.last_failure = timestamp()
            WITH w
            WHERE w.failure_count > 10
            SET w.active = false
            """
        
        with self.driver.session() as session:
            session.run(query, webhook_id=webhook_id)
    
    def _log_delivery(self, webhook_id: str, success: bool, status_code: int, 
                     error: Optional[str] = None):
        """Log webhook delivery"""
        query = """
        MATCH (w:Webhook {webhook_id: $webhook_id})
        CREATE (log:WebhookLog {
            log_id: randomUUID(),
            webhook_id: $webhook_id,
            success: $success,
            status_code: $status_code,
            error: $error,
            timestamp: timestamp()
        })
        CREATE (w)-[:HAS_LOG]->(log)
        """
        
        with self.driver.session() as session:
            session.run(
                query,
                webhook_id=webhook_id,
                success=success,
                status_code=status_code,
                error=error or ""
            )
    
    def get_user_webhooks(self, user_id: str) -> Dict[str, Any]:
        """Get all webhooks for a user"""
        query = """
        MATCH (w:Webhook {user_id: $user_id})
        RETURN w
        ORDER BY w.created_at DESC
        """
        
        with self.driver.session() as session:
            result = session.run(query, user_id=user_id)
            records = list(result)
            
            webhooks = [dict(record["w"]) for record in records]
            
            return {
                "user_id": user_id,
                "webhooks": webhooks,
                "total": len(webhooks)
            }
    
    def delete_webhook(self, webhook_id: str, user_id: str) -> Dict[str, Any]:
        """Delete a webhook"""
        query = """
        MATCH (w:Webhook {webhook_id: $webhook_id, user_id: $user_id})
        DETACH DELETE w
        RETURN count(w) as deleted
        """
        
        with self.driver.session() as session:
            result = session.run(query, webhook_id=webhook_id, user_id=user_id)
            record = result.single()
            
            if record["deleted"] > 0:
                return {"message": "Webhook deleted successfully"}
            else:
                return {"error": "Webhook not found"}
    
    def test_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """Send a test payload to webhook"""
        query = """
        MATCH (w:Webhook {webhook_id: $webhook_id})
        RETURN w
        """
        
        with self.driver.session() as session:
            result = session.run(query, webhook_id=webhook_id)
            record = result.single()
            
            if not record:
                return {"error": "Webhook not found"}
            
            webhook = dict(record["w"])
            
            # Test payload
            test_payload = {
                "event": "test.webhook",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "message": "This is a test webhook",
                    "webhook_id": webhook_id
                }
            }
            
            signature = None
            if webhook.get("secret"):
                signature = self._generate_signature(
                    json.dumps(test_payload),
                    webhook["secret"]
                )
            
            result = self._deliver_webhook(
                webhook_id,
                webhook["url"],
                test_payload,
                signature
            )
            
            return result
    
    def get_available_events(self) -> Dict[str, Any]:
        """Get list of available webhook events"""
        return {
            "events": self.events,
            "descriptions": {
                "alert.created": "Triggered when a new alert is created",
                "alert.updated": "Triggered when an alert is updated",
                "case.created": "Triggered when a new case is created",
                "case.updated": "Triggered when a case is updated",
                "case.closed": "Triggered when a case is closed",
                "analysis.completed": "Triggered when analysis completes",
                "transaction.detected": "Triggered when suspicious transaction detected",
                "risk.threshold_exceeded": "Triggered when risk score exceeds threshold"
            }
        }


# Global webhook manager
def get_webhook_manager(driver):
    return WebhookManager(driver)

