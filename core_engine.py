import asyncio
import json
import os
import io
import wave
import urllib.parse
import aiohttp
import numpy as np
import sounddevice as sd
import paho.mqtt.client as mqtt
import base64
import logging
from shazamio import Shazam
from typing import Optional, Dict, Any

# Try to import the modern config manager, fall back to simple dict loading
try:
    from core.config_manager import get_config
    USE_CONFIG_MANAGER = True
except ImportError:
    get_config = None
    USE_CONFIG_MANAGER = False

_LOGGER = logging.getLogger(__name__)

# Default configuration values
DEFAULT_CONFIG = {
    'THRESHOLD': 0.015,
    'SAMPLE_LEN': 5.0,
    'SILENCE_LIMIT': 5.0,
    'MIC_DEVICE': None,
    'SAMPLE_RATE': 48000,
}

# MQTT Topics
BASE_TOPIC = "home/vinyl"
TOPIC_STATE = f"{BASE_TOPIC}/state"
TOPIC_TITLE = f"{BASE_TOPIC}/title"
TOPIC_ARTIST = f"{BASE_TOPIC}/artist"
TOPIC_ALBUM = f"{BASE_TOPIC}/album"
TOPIC_ARTART = f"{BASE_TOPIC}/album_art"
LEGACY_TOPIC = f"{BASE_TOPIC}/now_playing"


class SpinSenseEngine:
    """Core SpinSense audio recognition engine."""

    def __init__(
        self,
        mqtt_client: Optional[mqtt.Client] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the SpinSense engine.
        
        Args:
            mqtt_client: Optional MQTT client. If None, will be created.
            config: Optional config dict with keys like THRESHOLD, SAMPLE_LEN, etc.
        """
        self.mqtt_client = mqtt_client
        self.mqtt_enabled = mqtt_client is not None

        # Load config from parameter or file
        if config:
            self.config = {**DEFAULT_CONFIG, **config}
        else:
            self.config = self._load_config_from_file()

        self.threshold = self.config.get('THRESHOLD', DEFAULT_CONFIG['THRESHOLD'])
        self.sample_len = self.config.get('SAMPLE_LEN', DEFAULT_CONFIG['SAMPLE_LEN'])
        self.silence_limit = self.config.get('SILENCE_LIMIT', DEFAULT_CONFIG['SILENCE_LIMIT'])
        self.sample_rate = self.config.get('SAMPLE_RATE', DEFAULT_CONFIG['SAMPLE_RATE'])

        device_name = self.config.get('MIC_DEVICE', DEFAULT_CONFIG['MIC_DEVICE'])
        device_index = self.config.get('MIC_DEVICE_INDEX')
        self.mic_device = device_index if device_index is not None else device_name

        self.shazam = Shazam()
        self.state = {
            "in_song": False,
            "last_song": "",
            "artist": "",
            "title": "",
            "album": "",
            "art_url": "",
            "silence_counter": 0,
            "current_rms": 0.0
        }

    @staticmethod
    def _load_config_from_file() -> Dict[str, Any]:
        """Load configuration from config.json file or environment variables."""
        if USE_CONFIG_MANAGER:
            try:
                config = get_config()
                return {
                    'THRESHOLD': config.audio.threshold,
                    'SAMPLE_LEN': config.audio.sample_length,
                    'SILENCE_LIMIT': config.audio.silence_interval,
                    'MIC_DEVICE': config.audio.device_name,
                    'MIC_DEVICE_INDEX': config.audio.device_index,
                    'SAMPLE_RATE': config.audio.sample_rate,
                }
            except Exception as e:
                _LOGGER.warning(f"Error loading config via config_manager: {e}, falling back to file parse")
        
        # Fallback: basic file parsing
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
                return {
                    'THRESHOLD': config_data.get('Audio', {}).get('Volume_Threshold', DEFAULT_CONFIG['THRESHOLD']),
                    'SAMPLE_LEN': config_data.get('Audio', {}).get('Song_Sample_Length', DEFAULT_CONFIG['SAMPLE_LEN']),
                    'SILENCE_LIMIT': config_data.get('Audio', {}).get('Stopped_Silence_Interval', DEFAULT_CONFIG['SILENCE_LIMIT']),
                    'MIC_DEVICE': config_data.get('Hardware', {}).get('Mic_Device', DEFAULT_CONFIG['MIC_DEVICE']),
                    'MIC_DEVICE_INDEX': config_data.get('Audio', {}).get('Device_Index'),
                    'SAMPLE_RATE': config_data.get('Audio', {}).get('Sample_Rate', DEFAULT_CONFIG['SAMPLE_RATE']),
                }
        except Exception as e:
            _LOGGER.warning(f"Could not load config.json, using defaults: {e}")
            return DEFAULT_CONFIG.copy()

    def publish_state(
        self,
        status: str,
        artist: str = "",
        title: str = "",
        album: str = "",
        art_url: str = "",
        art_base64: str = "",
    ) -> None:
        """Publish state to MQTT."""
        if self.mqtt_enabled and self.mqtt_client:
            try:
                self.mqtt_client.publish(TOPIC_STATE, status, retain=True)
                self.mqtt_client.publish(TOPIC_TITLE, title, retain=True)
                self.mqtt_client.publish(TOPIC_ARTIST, artist, retain=True)
                self.mqtt_client.publish(TOPIC_ALBUM, album, retain=True)

                if art_base64:
                    self.mqtt_client.publish(TOPIC_ARTART, art_base64, retain=True)
                else:
                    self.mqtt_client.publish(TOPIC_ARTART, "", retain=True)

                # Legacy JSON payload for compatibility
                payload = json.dumps({
                    "status": status,
                    "artist": artist,
                    "title": title,
                    "album": album,
                    "art_url": art_url
                })
                self.mqtt_client.publish(LEGACY_TOPIC, payload, retain=True)
                _LOGGER.info(f"Published State -> Status: {status.upper()} | {artist} - {title}")
            except Exception as e:
                _LOGGER.error(f"Error publishing to MQTT: {e}")
        else:
            _LOGGER.info(f"[MOCK MQTT] Published State -> Status: {status.upper()} | {artist} - {title}")

    async def fetch_itunes_metadata(self, artist: str, title: str) -> tuple:
        """Fetch high-res album art and album name from iTunes API."""
        query = urllib.parse.quote_plus(f"{artist} {title}")
        url = f"https://itunes.apple.com/search?term={query}&entity=song&limit=1"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json(content_type=None)
                        if data.get("resultCount", 0) > 0:
                            result = data["results"][0]
                            album = result.get("collectionName", "")
                            # Swap 100x100 for 1000x1000 for crisp artwork
                            art_url = result.get("artworkUrl100", "").replace("100x100bb", "1000x1000bb")
                            return album, art_url
        except Exception as e:
            _LOGGER.warning(f"iTunes API error: {e}")
        return None, None

    async def fetch_image_base64(self, url: str) -> str:
        """Download image and convert to base64 string."""
        if not url:
            return ""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        img_bytes = await response.read()
                        return base64.b64encode(img_bytes).decode('utf-8')
        except Exception as e:
            _LOGGER.warning(f"Failed to encode album art to base64: {e}")
        return ""

    async def recognize_audio(self) -> None:
        """Capture and recognize audio using Shazam."""
        _LOGGER.info(f"Music detected. Recording {self.sample_len}s for identification...")
        
        # Record audio at the configured sample rate
        recording = sd.rec(
            int(self.sample_len * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype='int16',
            device=self.mic_device
        )
        sd.wait()

        # Convert to WAV format
        wav_io = io.BytesIO()
        with wave.open(wav_io, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(recording.tobytes())

        _LOGGER.info("Analyzing with Shazam...")
        out = await self.shazam.recognize(wav_io.getvalue())

        if 'track' in out:
            track = out['track']
            title = track.get('title', 'Unknown Title')
            artist = track.get('subtitle', 'Unknown Artist')

            _LOGGER.info("Fetching high-res metadata from iTunes...")
            album, art_url = await self.fetch_itunes_metadata(artist, title)

            # Fallbacks if iTunes doesn't have it
            if not art_url:
                art_url = track.get('images', {}).get('coverarthq', track.get('images', {}).get('coverart', ''))
            if not album:
                album = "Unknown Album"

            # Download and encode album art
            art_base64 = ""
            if art_url:
                _LOGGER.info("Encoding album art to Base64...")
                art_base64 = await self.fetch_image_base64(art_url)

            result_str = f"{artist} - {title}"

            # Update state
            self.state["artist"] = artist
            self.state["title"] = title
            self.state["album"] = album
            self.state["art_url"] = art_url

            if result_str != self.state["last_song"]:
                _LOGGER.info(f"🎵 NEW TRACK: {result_str}")
                _LOGGER.info(f"💿 Album:     {album}")
                _LOGGER.info(f"🖼️  Art URL:   {art_url}")
                self.publish_state("stopped")
                await asyncio.sleep(0.5)
                self.publish_state("playing", artist, title, album, art_url, art_base64)
                self.state["last_song"] = result_str
            else:
                _LOGGER.debug(f"Confirmed same track: {self.state['last_song']}")
                self.publish_state("playing", artist, title, album, art_url, art_base64)

            self.state["in_song"] = True
        else:
            _LOGGER.warning("Could not identify track.")

        self.state["silence_counter"] = 0

    async def audio_monitor_loop(self) -> None:
        """Main audio monitoring loop."""
        _LOGGER.info("--- SPINSENSE ENGINE ACTIVE ---")

        def audio_callback(indata, frames, time, status):
            """Audio callback to calculate RMS level."""
            if status:
                _LOGGER.debug(f"Audio callback status: {status}")
            rms = np.sqrt(np.mean(indata**2))
            self.state["current_rms"] = float(rms)

        # Start continuous audio stream
        stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            callback=audio_callback,
            device=self.mic_device
        )
        stream.start()

        try:
            while True:
                vol = self.state["current_rms"]

                # Send state to UDS socket if it exists (for legacy GUI)
                try:
                    if os.path.exists('/tmp/spinsense.sock'):
                        reader, writer = await asyncio.open_unix_connection('/tmp/spinsense.sock')
                        payload = json.dumps({
                            "type": "live_status",
                            "payload": {
                                "rms_level": vol,
                                "engine_active": True,
                                "status_msg": "Playing" if self.state["in_song"] else "Listening",
                                "track": {
                                    "title": self.state.get("title", ""),
                                    "artist": self.state.get("artist", ""),
                                    "album": self.state.get("album", ""),
                                    "art_url": self.state.get("art_url", "")
                                }
                            }
                        }) + "\n"
                        writer.write(payload.encode())
                        await writer.drain()
                        writer.close()
                        await writer.wait_closed()
                except Exception:
                    pass  # Socket not available, no legacy GUI

                # Check if music is playing
                if vol > self.threshold:
                    if not self.state["in_song"] or self.state["silence_counter"] > 0:
                        # Music detected! Stop stream, recognize, then restart
                        stream.stop()
                        stream.close()

                        await self.recognize_audio()

                        # Restart audio stream
                        stream = sd.InputStream(
                            samplerate=self.sample_rate,
                            channels=1,
                            callback=audio_callback,
                            device=self.mic_device
                        )
                        stream.start()
                        self.state["current_rms"] = 0.0
                    else:
                        _LOGGER.debug(".", sep="")
                else:
                    # Below threshold
                    if self.state["in_song"]:
                        self.state["silence_counter"] += 1
                        _LOGGER.debug("s", sep="")

                        if self.state["silence_counter"] >= self.silence_limit:
                            _LOGGER.info(f"Record stopped after {self.silence_limit}s of silence")
                            self.publish_state("stopped")
                            self.state["in_song"] = False
                            self.state["last_song"] = ""
                            self.state["artist"] = ""
                            self.state["title"] = ""
                            self.state["album"] = ""
                            self.state["art_url"] = ""
                            self.state["silence_counter"] = 0

                await asyncio.sleep(1)
        finally:
            stream.stop()
            stream.close()


# --- Backward Compatibility: Module-level functions ---
# These functions allow the engine to be used in standalone mode

def _create_standalone_engine() -> SpinSenseEngine:
    """Create a standalone engine with MQTT client for backward compatibility."""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    try:
        with open(config_path, 'r') as f:
            config_data = json.load(f)
    except Exception as e:
        print(f"⚠️ Could not load config.json: {e}")
        config_data = {}

    mqtt_host = config_data.get('MQTT', {}).get('Broker', {}).get('Host', '192.168.1.100')
    mqtt_user = config_data.get('MQTT', {}).get('Broker', {}).get('User', '')
    mqtt_pass = config_data.get('MQTT', {}).get('Broker', {}).get('Password', '')
    mqtt_port = config_data.get('MQTT', {}).get('Broker', {}).get('Port', 1883)

    # Create MQTT client
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if mqtt_user and mqtt_pass:
        mqtt_client.username_pw_set(mqtt_user, mqtt_pass)

    print(f"Attempting to connect to MQTT at {mqtt_host}:{mqtt_port}...")
    try:
        mqtt_client.connect(mqtt_host, mqtt_port, 60)
        mqtt_client.loop_start()
        print("✅ MQTT Connected!")
    except Exception as e:
        print(f"⚠️ MQTT Connection Failed: {e}")
        print("⚠️ Running in OFFLINE TESTING MODE (MQTT messages will print to console).")
        mqtt_client = None

    # Create engine config
    engine_config = {
        'THRESHOLD': config_data.get('Audio', {}).get('Volume_Threshold', DEFAULT_CONFIG['THRESHOLD']),
        'SAMPLE_LEN': config_data.get('Audio', {}).get('Song_Sample_Length', DEFAULT_CONFIG['SAMPLE_LEN']),
        'SILENCE_LIMIT': config_data.get('Audio', {}).get('Stopped_Silence_Interval', DEFAULT_CONFIG['SILENCE_LIMIT']),
        'MIC_DEVICE': config_data.get('Hardware', {}).get('Mic_Device'),
        'MIC_DEVICE_INDEX': config_data.get('Audio', {}).get('Device_Index'),
        'SAMPLE_RATE': config_data.get('Audio', {}).get('Sample_Rate', DEFAULT_CONFIG['SAMPLE_RATE']),
    }

    return SpinSenseEngine(mqtt_client=mqtt_client, config=engine_config)


# Module-level engine instance (created on import for backward compatibility)
_engine = None
_mqtt_client = None


def publish_state(status, artist="", title="", album="", art_url="", art_base64=""):
    """Legacy function for publishing state (backward compatibility)."""
    global _engine
    if _engine is None:
        _engine = _create_standalone_engine()
    _engine.publish_state(status, artist, title, album, art_url, art_base64)


async def recognize_audio():
    """Legacy function for recognizing audio (backward compatibility)."""
    global _engine
    if _engine is None:
        _engine = _create_standalone_engine()
    await _engine.recognize_audio()


async def audio_monitor_loop():
    """Legacy function for starting the audio monitor loop (backward compatibility)."""
    global _engine
    if _engine is None:
        _engine = _create_standalone_engine()
    await _engine.audio_monitor_loop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(audio_monitor_loop())
    except KeyboardInterrupt:
        print("\nShutting down...")
        # Cleanup will happen when engine is garbage collected