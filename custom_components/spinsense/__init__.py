"""The SpinSense integration."""

import asyncio
import logging
from typing import Final

from aiohttp import WSMsgType
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_HOST, CONF_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: Final = [Platform.MEDIA_PLAYER]


class SpinSenseAPI:
    """HTTP/WebSocket client for SpinSense."""

    def __init__(self, hass: HomeAssistant, host: str, port: int):
        self.hass = hass
        self.host = host
        self.port = port
        self.session = async_get_clientsession(hass)
        self._ws = None
        self._task = None
        self._listeners = []
        self._connected = False
        self._http_available = False
        self.state = {
            "engine_active": False,
            "status_msg": "stopped",
            "rms_level": 0.0,
            "track": {"title": "", "artist": "", "album": "", "art_url": ""},
        }

    async def async_initialize(self) -> None:
        await self._refresh_status()
        self._task = self.hass.async_create_background_task(
            self._websocket_loop(), "spinsense_websocket_loop"
        )

    async def async_stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._ws is not None:
            await self._ws.close()

    def async_add_listener(self, callback):
        self._listeners.append(callback)

        def remove() -> None:
            if callback in self._listeners:
                self._listeners.remove(callback)

        return remove

    def _notify_listeners(self) -> None:
        for listener in list(self._listeners):
            self.hass.async_create_task(listener())

    async def _refresh_status(self) -> None:
        try:
            response = await self._request("api/status")
            self._update_state(response)
            self._http_available = True
            self._connected = True
        except Exception as exc:
            self._http_available = False
            self._connected = False
            _LOGGER.warning("Could not fetch initial SpinSense status: %s", exc)
            raise

    async def _request(self, path: str) -> dict:
        url = f"http://{self.host}:{self.port}/{path.lstrip('/')}"
        async with self.session.get(url, timeout=10) as response:
            if response.status != 200:
                raise RuntimeError(f"Unexpected status code {response.status}")
            return await response.json()

    async def _websocket_loop(self) -> None:
        url = f"ws://{self.host}:{self.port}/ws/live-status"
        while True:
            try:
                self._ws = await self.session.ws_connect(url, timeout=10)
                self._connected = True
                _LOGGER.info("Connected to SpinSense websocket at %s", url)

                async for message in self._ws:
                    if message.type == WSMsgType.TEXT:
                        self._handle_message(message.json())
                    elif message.type == WSMsgType.ERROR:
                        break
                    elif message.type == WSMsgType.CLOSED:
                        break
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self._connected = False
                _LOGGER.warning("SpinSense websocket connection lost: %s", exc)
                try:
                    await self._refresh_status()
                except Exception:
                    pass
            finally:
                if self._ws is not None:
                    await self._ws.close()
                    self._ws = None
                self._connected = False
            await asyncio.sleep(5)

    def is_available(self) -> bool:
        """Return whether SpinSense is currently connected or reachable over HTTP."""
        return self._connected or self._http_available

    def _handle_message(self, message: dict) -> None:
        if not isinstance(message, dict):
            return

        payload = (
            message.get("payload") if message.get("type") == "live_status" else message
        )
        if isinstance(payload, dict):
            self._update_state(payload)

    def _update_state(self, payload: dict) -> None:
        if not isinstance(payload, dict):
            return

        self.state["engine_active"] = payload.get(
            "engine_active", self.state["engine_active"]
        )
        self.state["status_msg"] = payload.get("status_msg", self.state["status_msg"])
        self.state["rms_level"] = payload.get("rms_level", self.state["rms_level"])

        track = payload.get("track", {})
        if isinstance(track, dict):
            self.state["track"]["title"] = track.get(
                "title", self.state["track"]["title"]
            )
            self.state["track"]["artist"] = track.get(
                "artist", self.state["track"]["artist"]
            )
            self.state["track"]["album"] = track.get(
                "album", self.state["track"]["album"]
            )
            self.state["track"]["art_url"] = track.get(
                "art_url", self.state["track"]["art_url"]
            )

        self._notify_listeners()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SpinSense from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    host = entry.data.get(CONF_HOST)
    port = entry.data.get(CONF_PORT, 8000)
    api = SpinSenseAPI(hass, host, port)

    try:
        await api.async_initialize()
    except Exception as exc:
        _LOGGER.warning("SpinSense not reachable, will retry: %s", exc)
        raise ConfigEntryNotReady(
            f"Cannot connect to SpinSense at {host}:{port}"
        ) from exc

    hass.data[DOMAIN][entry.entry_id] = {
        "config": entry.data,
        "api": api,
    }

    entry.async_on_unload(api.async_stop)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        api = hass.data[DOMAIN][entry.entry_id].get("api")
        if api is not None:
            await api.async_stop()
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
