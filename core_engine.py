import asyncio
import json
import logging
import os
import socket
import tempfile
import wave
from typing import Any, Callable, Dict, Optional

import numpy as np
import sounddevice as sd

from core.config_manager import get_config

_LOGGER = logging.getLogger(__name__)

# Default configuration values
DEFAULT_CONFIG = {
    "THRESHOLD": 0.015,
    "SAMPLE_LEN": 5.0,
    "SILENCE_LIMIT": 5.0,
    "MIC_DEVICE": None,
    "SAMPLE_RATE": 48000,
}


class SpinSenseEngine:
    """Core SpinSense audio recognition engine."""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        on_state_change: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_rms_update: Optional[Callable[[float], None]] = None,
    ):
        if config:
            self.config = {**DEFAULT_CONFIG, **config}
        else:
            self.config = self._load_config()

        self.threshold = self.config.get("THRESHOLD", DEFAULT_CONFIG["THRESHOLD"])
        self.sample_len = self.config.get("SAMPLE_LEN", DEFAULT_CONFIG["SAMPLE_LEN"])
        self.silence_limit = self.config.get(
            "SILENCE_LIMIT", DEFAULT_CONFIG["SILENCE_LIMIT"]
        )
        self.sample_rate = self.config.get("SAMPLE_RATE", DEFAULT_CONFIG["SAMPLE_RATE"])

        device_name = self.config.get("MIC_DEVICE", DEFAULT_CONFIG["MIC_DEVICE"])
        device_index = self.config.get("MIC_DEVICE_INDEX")
        self.mic_device = device_index if device_index is not None else device_name

        device_display = (
            self.mic_device if self.mic_device is not None else "System Default"
        )
        _LOGGER.info(f"Audio Input Device: {device_display}")

        self._on_state_change = on_state_change
        self._on_rms_update = on_rms_update
        self.state = {
            "in_song": False,
            "last_song": "",
            "artist": "",
            "title": "",
            "album": "",
            "art_url": "",
            "silence_counter": 0,
            "current_rms": 0.0,
        }

    @staticmethod
    def _load_config() -> Dict[str, Any]:
        """Load configuration from the config manager (env vars + optional file)."""
        try:
            config = get_config()
            return {
                "THRESHOLD": config.audio.threshold,
                "SAMPLE_LEN": config.audio.sample_length,
                "SILENCE_LIMIT": config.audio.silence_interval,
                "MIC_DEVICE": config.audio.device_name,
                "MIC_DEVICE_INDEX": config.audio.device_index,
                "SAMPLE_RATE": config.audio.sample_rate,
            }
        except Exception as e:
            _LOGGER.warning(f"Error loading config: {e}, using defaults")
            return DEFAULT_CONFIG.copy()

    def _get_local_host(self) -> str:
        """Return local IP address suitable for discovery."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.8.8", 80))
                return sock.getsockname()[0]
        except Exception:
            return "127.0.0.1"

    def _notify_state_change(self) -> None:
        """Invoke the state-change callback with the current status payload."""
        if self._on_state_change is None:
            return
        payload = {
            "engine_active": True,
            "status_msg": "playing" if self.state["in_song"] else "listening",
            "rms_level": self.state["current_rms"],
            "track": {
                "title": self.state.get("title", ""),
                "artist": self.state.get("artist", ""),
                "album": self.state.get("album", ""),
                "art_url": self.state.get("art_url", ""),
            },
        }
        try:
            self._on_state_change(payload)
        except Exception:
            _LOGGER.debug("State change callback error", exc_info=True)

    async def rms_update_loop(self) -> None:
        """Push RMS level to callback at ~5 Hz, independent of the recognition loop."""
        while True:
            await asyncio.sleep(0.2)
            if self._on_rms_update is not None:
                try:
                    self._on_rms_update(self.state["current_rms"])
                except Exception:
                    _LOGGER.debug("RMS callback error", exc_info=True)

    async def recognize_audio(self) -> None:
        """Capture audio and recognize using songrec CLI."""
        _LOGGER.info(
            f"Music detected. Recording {self.sample_len}s for identification..."
        )

        recording = sd.rec(
            int(self.sample_len * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            device=self.mic_device,
        )
        sd.wait()

        # Write WAV to a temp file for songrec
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        try:
            with wave.open(tmp, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(recording.tobytes())
            tmp.close()

            _LOGGER.info("Analyzing with songrec...")
            proc = await asyncio.create_subprocess_exec(
                "songrec",
                "audio-file-to-recognized-song",
                tmp.name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                _LOGGER.warning(
                    f"songrec exited with code {proc.returncode}: {stderr.decode().strip()}"
                )
                # Still mark as playing — RMS was above threshold
                self.state["in_song"] = True
                self._notify_state_change()
                self.state["silence_counter"] = 0
                return

            out = json.loads(stdout.decode())
        finally:
            os.unlink(tmp.name)

        if "track" in out:
            track = out["track"]
            title = track.get("title", "Unknown Title")
            artist = track.get("subtitle", "Unknown Artist")

            # Try to extract album from Shazam metadata sections
            album = ""
            for section in track.get("sections", []):
                for item in section.get("metadata", []):
                    if item.get("title", "").lower() == "album":
                        album = item.get("text", "")
                        break
                if album:
                    break
            if not album:
                album = "Unknown Album"

            art_url = track.get("images", {}).get(
                "coverarthq", track.get("images", {}).get("coverart", "")
            )

            result_str = f"{artist} - {title}"

            self.state["artist"] = artist
            self.state["title"] = title
            self.state["album"] = album
            self.state["art_url"] = art_url

            if result_str != self.state["last_song"]:
                _LOGGER.info(f"NEW TRACK: {result_str}")
                _LOGGER.info(f"Album:     {album}")
                _LOGGER.info(f"Art URL:   {art_url}")
                self.state["last_song"] = result_str

            self.state["in_song"] = True
        else:
            _LOGGER.warning("Could not identify track.")
            # Still mark as playing — RMS was above threshold
            self.state["in_song"] = True

        self.state["silence_counter"] = 0
        self._notify_state_change()

    async def audio_monitor_loop(self) -> None:
        """Main audio monitoring loop."""
        _LOGGER.info("--- SPINSENSE ENGINE ACTIVE ---")

        # Log available audio devices for debugging
        try:
            devices = sd.query_devices()
            input_devices = [
                d
                for d in devices
                if isinstance(d, dict) and d.get("max_input_channels", 0) > 0
            ]
            if input_devices:
                _LOGGER.info("Available Audio Input Devices:")
                for i, d in enumerate(input_devices):
                    device_name = d.get("name", "Unknown")
                    channels = d.get("max_input_channels", 0)
                    _LOGGER.info(f"  [{i}] {device_name} - {channels} channels")
        except Exception as e:
            _LOGGER.debug(f"Could not list audio devices: {e}")

        def audio_callback(indata, frames, time, status):
            if status:
                _LOGGER.debug(f"Audio callback status: {status}")
            rms = np.sqrt(np.mean(indata**2))
            self.state["current_rms"] = float(rms)

        stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            callback=audio_callback,
            device=self.mic_device,
        )
        stream.start()

        rms_task = asyncio.create_task(self.rms_update_loop())
        try:
            while True:
                vol = self.state["current_rms"]

                # Broadcast current state every tick
                self._notify_state_change()

                if vol > self.threshold:
                    if not self.state["in_song"] or self.state["silence_counter"] > 0:
                        stream.stop()
                        stream.close()

                        await self.recognize_audio()

                        stream = sd.InputStream(
                            samplerate=self.sample_rate,
                            channels=1,
                            callback=audio_callback,
                            device=self.mic_device,
                        )
                        stream.start()
                        self.state["current_rms"] = 0.0
                else:
                    if self.state["in_song"]:
                        self.state["silence_counter"] += 1

                        if self.state["silence_counter"] >= self.silence_limit:
                            _LOGGER.info(
                                f"Record stopped after {self.silence_limit}s of silence"
                            )
                            self.state["in_song"] = False
                            self.state["last_song"] = ""
                            self.state["artist"] = ""
                            self.state["title"] = ""
                            self.state["album"] = ""
                            self.state["art_url"] = ""
                            self.state["silence_counter"] = 0
                            self._notify_state_change()

                await asyncio.sleep(1)
        finally:
            rms_task.cancel()
            try:
                await rms_task
            except asyncio.CancelledError:
                pass
            stream.stop()
            stream.close()
