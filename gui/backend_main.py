import asyncio
import json
import os
import socket
from contextlib import asynccontextmanager

import sounddevice as sd
from config_manager import load_config, save_config
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from zeroconf import ServiceInfo
from zeroconf.asyncio import AsyncZeroconf

# This set holds all connected web browsers
active_websockets = set()

latest_engine_status = {
    "engine_active": False,
    "status_msg": "stopped",
    "rms_level": 0.0,
    "track": {"title": "", "artist": "", "album": "", "art_url": ""},
}

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
        print(f"🔎 Advertised SpinSense via zeroconf on {local_ip}:8000")
    except Exception as exc:
        print(f"⚠️ Failed to advertise zeroconf service: {exc}")


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


async def uds_server_callback(reader, writer):
    """Reads socket data from Core Engine and broadcasts to WebSockets."""
    try:
        data = await reader.readline()
        if data:
            payload = data.decode("utf-8")
            try:
                parsed = json.loads(payload)
                if isinstance(parsed, dict) and parsed.get("type") == "live_status":
                    latest_engine_status.update(parsed.get("payload", {}))
            except json.JSONDecodeError:
                pass

            # Broadcast this payload to every open browser tab
            # Iterate over a snapshot to avoid RuntimeError if the set is
            # modified during an await (e.g. a new browser tab connects).
            dead_sockets = set()
            for ws in list(active_websockets):
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead_sockets.add(ws)
            # Clean up disconnected browsers
            active_websockets.difference_update(dead_sockets)
    except Exception as e:
        print(f"Socket read error: {e}")
    finally:
        writer.close()
        await writer.wait_closed()


async def start_uds_listener():
    """Starts the Unix Domain Socket server."""
    socket_path = "/tmp/spinsense.sock"
    if os.path.exists(socket_path):
        os.remove(socket_path)

    server = await asyncio.start_unix_server(uds_server_callback, path=socket_path)
    print(f"🎧 Now listening for Core Engine on {socket_path}")

    async with server:
        await server.serve_forever()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Boot up the UDS listener and zeroconf in the background
    uds_task = asyncio.create_task(start_uds_listener())
    await register_zeroconf()
    try:
        yield
    finally:
        uds_task.cancel()
        await unregister_zeroconf()


app = FastAPI(lifespan=lifespan)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

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
def get_config():
    config = load_config()

    # If only AUDIO_DEVICE_INDEX is set (no AUDIO_DEVICE), resolve index to device name
    # so the GUI dropdown pre-selects the correct device
    device_index_str = os.getenv("AUDIO_DEVICE_INDEX", "").strip()
    audio_device = os.getenv("AUDIO_DEVICE", "").strip()
    if device_index_str and not audio_device:
        try:
            idx = int(device_index_str)
            # query_devices(idx, kind='input') raises ValueError if not an input device
            device_info = sd.query_devices(idx, kind="input")
            config["Hardware"]["Mic_Device"] = device_info["name"]
        except Exception as e:
            print(f"⚠️ Could not resolve AUDIO_DEVICE_INDEX={device_index_str}: {e}")

    return config


@app.post("/api/config")
async def update_config(request: Request):
    new_config = await request.json()
    save_config(new_config)
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


@app.post("/api/engine/start")
def start_engine():
    config = load_config()
    config["System"]["Auto_Start"] = True
    config["System"]["Engine_Status"] = "active"
    save_config(config)
    return {"status": "success"}


@app.post("/api/engine/stop")
def stop_engine():
    config = load_config()
    config["System"]["Auto_Start"] = False
    config["System"]["Engine_Status"] = "stopped"
    save_config(config)
    return {"status": "success"}


@app.websocket("/ws/live-status")
async def websocket_endpoint(websocket: WebSocket):
    """Handles real-time WebSocket connection from the browser."""
    await websocket.accept()
    active_websockets.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, Exception):
        # Use discard instead of remove: the socket may have already been
        # pruned from active_websockets by the dead_sockets cleanup in
        # uds_server_callback, so remove() would raise a KeyError.
        active_websockets.discard(websocket)
