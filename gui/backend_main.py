import asyncio
import json
import socket
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import sounddevice as sd
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from zeroconf import ServiceInfo
from zeroconf.asyncio import AsyncZeroconf

# Allow imports from the project root (one level up from gui/)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core_engine import SpinSenseEngine

# This set holds all connected web browsers
active_websockets: set[WebSocket] = set()

latest_engine_status = {
    "engine_active": False,
    "status_msg": "stopped",
    "rms_level": 0.0,
    "track": {"title": "", "artist": "", "album": "", "art_url": ""},
}

# Engine instance — created during lifespan
engine: SpinSenseEngine | None = None

zeroconf_instance = None
zeroconf_info = None


def _get_local_ip() -> str:
    """Attempt to determine the local outbound IP address."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except Exception:
        return "127.0.0.1"


async def register_zeroconf() -> None:
    """Advertise SpinSense via zeroconf/mDNS."""
    global zeroconf_instance, zeroconf_info

    local_ip = _get_local_ip()
    hostname = socket.gethostname().replace(" ", "-")
    service_name = f"SpinSense-{hostname}"
    service_type = "_spinsense._tcp.local."
    service_full_name = f"{service_name}.{service_type}"

    properties = {
        "path": b"/api/status",
        "version": b"1.0",
    }

    try:
        zeroconf_info = ServiceInfo(
            type_=service_type,
            name=service_full_name,
            addresses=[socket.inet_aton(local_ip)],
            port=8000,
            properties=properties,
            server=f"{hostname}.local.",
        )
        zeroconf_instance = AsyncZeroconf()
        await zeroconf_instance.async_register_service(zeroconf_info)
        print(f"Advertised SpinSense via zeroconf on {local_ip}:8000")
    except Exception as exc:
        print(f"Failed to advertise zeroconf service: {exc}")


async def unregister_zeroconf() -> None:
    """Stop zeroconf service advertisement."""
    global zeroconf_instance, zeroconf_info
    if zeroconf_instance is not None and zeroconf_info is not None:
        try:
            await zeroconf_instance.async_unregister_service(zeroconf_info)
        except Exception:
            pass
        await zeroconf_instance.async_close()
        zeroconf_instance = None
        zeroconf_info = None


def on_engine_state_change(payload: dict) -> None:
    """Callback invoked by the engine on every state change / tick."""
    latest_engine_status.update(payload)

    message = json.dumps({"type": "live_status", "payload": payload})

    dead_sockets: set[WebSocket] = set()
    for ws in list(active_websockets):
        try:
            asyncio.ensure_future(ws.send_text(message))
        except Exception:
            dead_sockets.add(ws)
    active_websockets.difference_update(dead_sockets)


def on_engine_rms_update(rms: float) -> None:
    """Fast RMS callback — fires at ~5 Hz for smooth meter updates."""
    latest_engine_status["rms_level"] = rms
    message = json.dumps({"type": "rms_update", "payload": {"rms_level": rms}})
    dead_sockets: set[WebSocket] = set()
    for ws in list(active_websockets):
        try:
            asyncio.ensure_future(ws.send_text(message))
        except Exception:
            dead_sockets.add(ws)
    active_websockets.difference_update(dead_sockets)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine

    # Create and start the engine
    engine = SpinSenseEngine(
        on_state_change=on_engine_state_change,
        on_rms_update=on_engine_rms_update,
    )
    engine_task = asyncio.create_task(engine.audio_monitor_loop())
    latest_engine_status["engine_active"] = True

    await register_zeroconf()
    try:
        yield
    finally:
        engine_task.cancel()
        try:
            await engine_task
        except asyncio.CancelledError:
            pass
        latest_engine_status["engine_active"] = False
        await unregister_zeroconf()


app = FastAPI(lifespan=lifespan)

# Resolve paths relative to this file so it works regardless of cwd
_gui_dir = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(_gui_dir / "static")), name="static")
templates = Jinja2Templates(directory=str(_gui_dir / "templates"))

# --- Routes ---


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/info")
def get_info():
    return {
        "name": "SpinSense",
        "version": "1.0",
        "status_url": "/api/status",
        "websocket_url": "/ws/live-status",
        "zeroconf_service": "_spinsense._tcp.local.",
    }


@app.get("/api/status")
def get_status():
    return latest_engine_status


@app.get("/api/health")
def get_health():
    return {
        "status": "ok",
        "engine_active": latest_engine_status.get("engine_active", False),
    }


@app.get("/api/config")
def get_config_route():
    if engine is None:
        return {}
    return {
        "threshold": engine.threshold,
        "sample_length": engine.sample_len,
        "sample_rate": engine.sample_rate,
        "silence_interval": engine.silence_limit,
        "device_name": engine.mic_device,
    }


@app.post("/api/config")
async def update_config(request: Request):
    data = await request.json()
    if engine is None:
        return {"status": "error", "message": "engine not running"}

    if "threshold" in data:
        engine.threshold = float(data["threshold"])
    if "sample_length" in data:
        engine.sample_len = float(data["sample_length"])
    if "sample_rate" in data:
        engine.sample_rate = int(data["sample_rate"])
    if "silence_interval" in data:
        engine.silence_limit = float(data["silence_interval"])

    return {"status": "success"}


@app.get("/api/devices")
def get_audio_devices():
    """Returns mic devices as objects so the frontend JS can read them."""
    try:
        devices = sd.query_devices()
        mics = [{"name": d["name"]} for d in devices if d["max_input_channels"] > 0]
        unique_mics = list({m["name"]: m for m in mics}.values())
        return {"devices": unique_mics}
    except Exception as e:
        print(f"Error querying devices: {e}")
        return {"devices": []}


@app.websocket("/ws/live-status")
async def websocket_endpoint(websocket: WebSocket):
    """Handles real-time WebSocket connection from the browser."""
    await websocket.accept()
    active_websockets.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, Exception):
        active_websockets.discard(websocket)
