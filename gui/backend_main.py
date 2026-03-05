# gui/backend_main.py
import asyncio
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
import uvicorn

from config_manager import load_config, save_config
from audio_utils import get_audio_devices
from ipc_manager import manager, mock_core_engine_stream

# We use lifespan to start our background tasks when FastAPI boots
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the mock data generator so we have volume data for the UI
    task = asyncio.create_task(mock_core_engine_stream())
    
    # Future: When the Core is ready, we will swap the mock task with this:
    # server = await asyncio.start_unix_server(handle_uds_client, '/tmp/spinsense.sock')
    
    yield
    task.cancel()

app = FastAPI(title="SpinSense Web GUI API", lifespan=lifespan)

# --- REST API Endpoints (From Phase 1) ---
@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "SpinSense backend is running."}

@app.get("/api/config")
def get_config():
    return load_config()

@app.post("/api/config")
def update_config(new_config: dict):
    success = save_config(new_config)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid config format.")
    return {"status": "success"}

@app.get("/api/devices")
def list_devices():
    return {"devices": get_audio_devices()}

# --- WebSockets (New in Phase 2) ---
@app.websocket("/ws/live-status")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # We just keep the connection open. The server pushes data to the client.
            await websocket.receive_text() 
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run("backend_main:app", host="0.0.0.0", port=5000, reload=True)