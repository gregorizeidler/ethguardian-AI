from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.api import router as api_router
from app.core import init_constraints
from app.websocket_manager import ws_manager
import json

app = FastAPI(
    title="EthGuardian AI",
    description="AI-Powered Ethereum AML & Forensics Platform",
    version="1.0.0"
)

# CORS para o frontend (Vite)
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost",
    "http://127.0.0.1",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    # Cria constraints idempotentes
    init_constraints()

@app.get("/health")
def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.
    
    Clients can subscribe to topics:
    - alerts: Receive alert notifications
    - analysis: Receive analysis updates
    - transactions: Receive transaction feed
    - jobs: Receive automation job updates
    - address_{address}: Receive updates for specific address
    
    Send message: {"action": "subscribe", "topic": "alerts"}
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            action = message.get("action")
            
            if action == "subscribe":
                topic = message.get("topic")
                if topic:
                    ws_manager.subscribe(websocket, topic)
                    await ws_manager.send_personal_message({
                        "type": "subscription",
                        "message": f"Subscribed to {topic}",
                        "topic": topic
                    }, websocket)
            
            elif action == "unsubscribe":
                topic = message.get("topic")
                if topic:
                    ws_manager.unsubscribe(websocket, topic)
                    await ws_manager.send_personal_message({
                        "type": "unsubscription",
                        "message": f"Unsubscribed from {topic}",
                        "topic": topic
                    }, websocket)
            
            elif action == "ping":
                await ws_manager.send_personal_message({
                    "type": "pong",
                    "message": "pong"
                }, websocket)
    
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


app.include_router(api_router, prefix="")
