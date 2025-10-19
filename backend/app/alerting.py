"""
Smart Alerting System
Multi-channel alert system with customizable rules including:
- Email notifications
- Telegram bot integration  
- Discord webhooks
- Slack integration
- Threshold-based alerts
- Pattern-matching alerts
- ML anomaly alerts
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import json
import os


class AlertChannel:
    """Base class for alert channels"""
    
    def send_alert(self, alert: Dict[str, Any]) -> bool:
        """Send alert through this channel"""
        raise NotImplementedError


class EmailChannel(AlertChannel):
    """Email alert channel"""
    
    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str, from_email: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
    
    def send_alert(self, alert: Dict[str, Any], to_email: str) -> bool:
        """Send alert via email"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"🚨 AML Alert: {alert['alert_type']} - Risk {alert['risk_score']}"
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            # Create HTML content
            html = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .header {{ background: linear-gradient(135deg, #a855f7, #06b6d4); color: white; padding: 20px; }}
                    .content {{ padding: 20px; }}
                    .alert-box {{ background: #fff3cd; border-left: 4px solid #ff6b6b; padding: 15px; margin: 15px 0; }}
                    .high-risk {{ background: #ffe0e0; border-color: #dc2626; }}
                    .medium-risk {{ background: #fff3cd; border-color: #FFA94D; }}
                    .low-risk {{ background: #d1f0e0; border-color: #10b981; }}
                    .detail {{ margin: 10px 0; padding: 10px; background: #f8f9fa; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🛡️ EthGuardian AI Alert</h1>
                    <p>Suspicious Activity Detected</p>
                </div>
                <div class="content">
                    <div class="alert-box {self._get_risk_class(alert['risk_score'])}">
                        <h2>{alert['alert_type']}</h2>
                        <p><strong>Risk Score:</strong> {alert['risk_score']}/100</p>
                        <p><strong>Address:</strong> <code>{alert['address']}</code></p>
                        <p><strong>Time:</strong> {alert['timestamp']}</p>
                    </div>
                    
                    <div class="detail">
                        <h3>Details:</h3>
                        <pre>{json.dumps(alert.get('details', {}), indent=2)}</pre>
                    </div>
                    
                    <div class="detail">
                        <h3>Recommended Actions:</h3>
                        <ul>
                            <li>Investigate transaction history</li>
                            <li>Check for connections to known bad actors</li>
                            <li>Review compliance requirements</li>
                            <li>Consider filing SAR if threshold met</li>
                        </ul>
                    </div>
                </div>
            </body>
            </html>
            """
            
            part = MIMEText(html, 'html')
            msg.attach(part)
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            print(f"Email send failed: {e}")
            return False
    
    def _get_risk_class(self, risk_score: int) -> str:
        """Get CSS class based on risk score"""
        if risk_score >= 70:
            return "high-risk"
        elif risk_score >= 40:
            return "medium-risk"
        else:
            return "low-risk"


class TelegramChannel(AlertChannel):
    """Telegram bot alert channel"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
    
    def send_alert(self, alert: Dict[str, Any]) -> bool:
        """Send alert via Telegram"""
        try:
            # Format message with emoji based on risk
            risk_emoji = "🔴" if alert['risk_score'] >= 70 else "🟡" if alert['risk_score'] >= 40 else "🟢"
            
            message = f"""
{risk_emoji} *AML ALERT*

*Type:* {alert['alert_type']}
*Risk Score:* {alert['risk_score']}/100
*Address:* `{alert['address']}`
*Time:* {alert['timestamp']}

*Details:*
```
{json.dumps(alert.get('details', {}), indent=2)}
```

🔍 Investigate immediately if risk score > 70
            """
            
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "Markdown"
                }
            )
            
            return response.status_code == 200
        except Exception as e:
            print(f"Telegram send failed: {e}")
            return False


class DiscordChannel(AlertChannel):
    """Discord webhook alert channel"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def send_alert(self, alert: Dict[str, Any]) -> bool:
        """Send alert via Discord webhook"""
        try:
            # Color based on risk score
            color = 0xdc2626 if alert['risk_score'] >= 70 else 0xFFA94D if alert['risk_score'] >= 40 else 0x10b981
            
            embed = {
                "embeds": [{
                    "title": f"🚨 AML Alert: {alert['alert_type']}",
                    "description": f"Suspicious activity detected on address `{alert['address']}`",
                    "color": color,
                    "fields": [
                        {
                            "name": "Risk Score",
                            "value": f"{alert['risk_score']}/100",
                            "inline": True
                        },
                        {
                            "name": "Timestamp",
                            "value": alert['timestamp'],
                            "inline": True
                        },
                        {
                            "name": "Details",
                            "value": f"```json\n{json.dumps(alert.get('details', {}), indent=2)[:1000]}\n```",
                            "inline": False
                        }
                    ],
                    "footer": {
                        "text": "EthGuardian AI - AML Monitoring Platform"
                    },
                    "timestamp": datetime.now().isoformat()
                }]
            }
            
            response = requests.post(self.webhook_url, json=embed)
            return response.status_code == 204
        except Exception as e:
            print(f"Discord send failed: {e}")
            return False


class SlackChannel(AlertChannel):
    """Slack webhook alert channel"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def send_alert(self, alert: Dict[str, Any]) -> bool:
        """Send alert via Slack webhook"""
        try:
            # Color based on risk score
            color = "danger" if alert['risk_score'] >= 70 else "warning" if alert['risk_score'] >= 40 else "good"
            
            payload = {
                "attachments": [{
                    "color": color,
                    "title": f"🚨 AML Alert: {alert['alert_type']}",
                    "text": f"Suspicious activity detected",
                    "fields": [
                        {
                            "title": "Address",
                            "value": f"`{alert['address']}`",
                            "short": False
                        },
                        {
                            "title": "Risk Score",
                            "value": f"{alert['risk_score']}/100",
                            "short": True
                        },
                        {
                            "title": "Timestamp",
                            "value": alert['timestamp'],
                            "short": True
                        },
                        {
                            "title": "Details",
                            "value": f"```{json.dumps(alert.get('details', {}), indent=2)[:500]}```",
                            "short": False
                        }
                    ],
                    "footer": "EthGuardian AI",
                    "ts": int(datetime.now().timestamp())
                }]
            }
            
            response = requests.post(self.webhook_url, json=payload)
            return response.status_code == 200
        except Exception as e:
            print(f"Slack send failed: {e}")
            return False


class AlertManager:
    """Manage alerts and routing to different channels"""
    
    def __init__(self):
        self.channels: Dict[str, AlertChannel] = {}
        self.alert_rules: List[Dict[str, Any]] = []
        self.alert_history: List[Dict[str, Any]] = []
    
    def add_channel(self, name: str, channel: AlertChannel):
        """Add an alert channel"""
        self.channels[name] = channel
    
    def add_rule(self, rule: Dict[str, Any]):
        """
        Add an alert rule
        Rule structure:
        {
            "name": "High Risk Address",
            "condition": {"risk_score_min": 70},
            "channels": ["email", "telegram"],
            "enabled": True
        }
        """
        self.alert_rules.append(rule)
    
    def create_alert(self, alert_type: str, address: str, risk_score: int, details: Dict[str, Any]) -> Dict[str, Any]:
        """Create a structured alert"""
        alert = {
            "id": f"alert_{datetime.now().timestamp()}_{address[:10]}",
            "alert_type": alert_type,
            "address": address,
            "risk_score": risk_score,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "status": "new"
        }
        
        return alert
    
    def should_alert(self, alert: Dict[str, Any], rule: Dict[str, Any]) -> bool:
        """Check if alert matches rule conditions"""
        if not rule.get("enabled", True):
            return False
        
        condition = rule.get("condition", {})
        
        # Check risk score threshold
        if "risk_score_min" in condition:
            if alert["risk_score"] < condition["risk_score_min"]:
                return False
        
        # Check alert type
        if "alert_types" in condition:
            if alert["alert_type"] not in condition["alert_types"]:
                return False
        
        # Check address watchlist
        if "watchlist" in condition:
            if alert["address"] not in condition["watchlist"]:
                return False
        
        return True
    
    def process_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Process alert and send to appropriate channels"""
        results = {
            "alert": alert,
            "sent_to": [],
            "failed": []
        }
        
        # Check which rules match
        for rule in self.alert_rules:
            if self.should_alert(alert, rule):
                # Send to all channels specified in rule
                for channel_name in rule.get("channels", []):
                    if channel_name in self.channels:
                        channel = self.channels[channel_name]
                        try:
                            success = channel.send_alert(alert)
                            if success:
                                results["sent_to"].append(channel_name)
                            else:
                                results["failed"].append(channel_name)
                        except Exception as e:
                            print(f"Failed to send to {channel_name}: {e}")
                            results["failed"].append(channel_name)
        
        # Store in history
        alert["sent_to"] = results["sent_to"]
        alert["status"] = "sent" if results["sent_to"] else "failed"
        self.alert_history.append(alert)
        
        # Keep only last 1000 alerts
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]
        
        return results
    
    def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent alert history"""
        return self.alert_history[-limit:]
    
    def get_alerts_by_address(self, address: str) -> List[Dict[str, Any]]:
        """Get all alerts for a specific address"""
        return [a for a in self.alert_history if a["address"] == address]


# Global alert manager instance
alert_manager = AlertManager()


def setup_demo_channels():
    """Setup demo alert channels (to be configured via environment variables)"""
    
    # Email (configure via env vars)
    email_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    email_port = int(os.getenv("SMTP_PORT", "587"))
    email_user = os.getenv("SMTP_USER", "")
    email_pass = os.getenv("SMTP_PASS", "")
    email_from = os.getenv("EMAIL_FROM", "")
    
    if email_user and email_pass:
        email_channel = EmailChannel(email_host, email_port, email_user, email_pass, email_from)
        alert_manager.add_channel("email", email_channel)
    
    # Telegram (configure via env vars)
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat = os.getenv("TELEGRAM_CHAT_ID", "")
    
    if telegram_token and telegram_chat:
        telegram_channel = TelegramChannel(telegram_token, telegram_chat)
        alert_manager.add_channel("telegram", telegram_channel)
    
    # Discord (configure via env vars)
    discord_webhook = os.getenv("DISCORD_WEBHOOK_URL", "")
    
    if discord_webhook:
        discord_channel = DiscordChannel(discord_webhook)
        alert_manager.add_channel("discord", discord_channel)
    
    # Slack (configure via env vars)
    slack_webhook = os.getenv("SLACK_WEBHOOK_URL", "")
    
    if slack_webhook:
        slack_channel = SlackChannel(slack_webhook)
        alert_manager.add_channel("slack", slack_channel)
    
    # Add default rules
    alert_manager.add_rule({
        "name": "Critical Risk Alert",
        "condition": {"risk_score_min": 80},
        "channels": ["email", "telegram", "discord", "slack"],
        "enabled": True
    })
    
    alert_manager.add_rule({
        "name": "High Risk Alert",
        "condition": {"risk_score_min": 60},
        "channels": ["telegram", "discord"],
        "enabled": True
    })
    
    alert_manager.add_rule({
        "name": "Medium Risk Alert",
        "condition": {"risk_score_min": 40},
        "channels": ["discord"],
        "enabled": True
    })


# Initialize on import
setup_demo_channels()

