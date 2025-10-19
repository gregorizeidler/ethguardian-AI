"""
WebSocket Manager for Real-Time Updates
Push notifications to connected clients
"""

from typing import Dict, Any, List, Set
from fastapi import WebSocket
import json
import asyncio
from datetime import datetime


class WebSocketManager:
    """Manage WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriptions: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection",
            "message": "Connected to EthGuardian AI",
            "timestamp": datetime.now().isoformat()
        }, websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # Remove from all subscriptions
        for topic in self.subscriptions:
            if websocket in self.subscriptions[topic]:
                self.subscriptions[topic].remove(websocket)
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send message to specific client"""
        try:
            await websocket.send_json(message)
        except:
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
    
    async def broadcast_to_topic(self, topic: str, message: Dict[str, Any]):
        """Broadcast message to clients subscribed to specific topic"""
        if topic not in self.subscriptions:
            return
        
        disconnected = []
        for connection in self.subscriptions[topic]:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
    
    def subscribe(self, websocket: WebSocket, topic: str):
        """Subscribe client to topic"""
        if topic not in self.subscriptions:
            self.subscriptions[topic] = set()
        self.subscriptions[topic].add(websocket)
    
    def unsubscribe(self, websocket: WebSocket, topic: str):
        """Unsubscribe client from topic"""
        if topic in self.subscriptions and websocket in self.subscriptions[topic]:
            self.subscriptions[topic].remove(websocket)
    
    async def send_alert(self, alert: Dict[str, Any]):
        """Send alert notification to all clients"""
        message = {
            "type": "alert",
            "data": alert,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast_to_topic("alerts", message)
    
    async def send_analysis_update(self, address: str, analysis: Dict[str, Any]):
        """Send analysis update for an address"""
        message = {
            "type": "analysis_update",
            "address": address,
            "data": analysis,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast_to_topic(f"address_{address}", message)
        await self.broadcast_to_topic("analysis", message)
    
    async def send_transaction_feed(self, transaction: Dict[str, Any]):
        """Send real-time transaction to feed"""
        message = {
            "type": "transaction",
            "data": transaction,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast_to_topic("transactions", message)
    
    async def send_job_update(self, job_id: str, status: Dict[str, Any]):
        """Send automation job status update"""
        message = {
            "type": "job_update",
            "job_id": job_id,
            "data": status,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast_to_topic("jobs", message)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        return {
            "active_connections": len(self.active_connections),
            "topics": list(self.subscriptions.keys()),
            "subscriptions_by_topic": {
                topic: len(subs) for topic, subs in self.subscriptions.items()
            }
        }


# Global WebSocket manager
ws_manager = WebSocketManager()

