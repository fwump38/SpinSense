# gui/ipc_manager.py
import asyncio
import json
import random
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Sends a JSON message to all connected browsers."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass # Ignore dropped connections

manager = ConnectionManager()

# --- The Mock Generator for UI Development ---
async def mock_core_engine_stream():
    """Simulates the Core engine sending RMS data at ~5 FPS."""
    while True:
        # Generate a fake RMS volume level between 0.0 and 0.1
        fake_rms = random.uniform(0.0, 0.1)
        
        payload = {
            "type": "live_status",
            "payload": {
                "rms_level": round(fake_rms, 4),
                "engine_active": True,
                "status_msg": "Listening (Mock Data)",
                "track": {
                    "title": "Waiting for drop...",
                    "artist": "",
                    "album": "",
                    "art_url": ""
                }
            }
        }
        await manager.broadcast(payload)
        await asyncio.sleep(0.2) # 5 times a second (200ms)

# --- The Real Unix Domain Socket Listener (For the Final Integration) ---
async def handle_uds_client(reader, writer):
    """Reads real data from the Core engine via /tmp/spinsense.sock."""
    while True:
        data = await reader.readline()
        if not data:
            break
        try:
            payload = json.loads(data.decode())
            await manager.broadcast(payload)
        except json.JSONDecodeError:
            pass