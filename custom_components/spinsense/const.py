"""Constants for the SpinSense integration."""

DOMAIN = "spinsense"
DEFAULT_NAME = "Vinyl Record Player"
DEFAULT_MQTT_TOPIC_BASE = "home/vinyl"

# Config keys
CONF_MQTT_HOST = "mqtt_host"
CONF_MQTT_PORT = "mqtt_port"
CONF_MQTT_USER = "mqtt_user"
CONF_MQTT_PASSWORD = "mqtt_password"
CONF_AUDIO_DEVICE = "audio_device"
CONF_AUDIO_THRESHOLD = "audio_threshold"
CONF_AUDIO_SAMPLE_LENGTH = "audio_sample_length"
CONF_AUDIO_SAMPLE_RATE = "audio_sample_rate"
CONF_SILENCE_INTERVAL = "silence_interval"

# Default config values
DEFAULT_MQTT_PORT = 1883
DEFAULT_AUDIO_THRESHOLD = 0.015
DEFAULT_AUDIO_SAMPLE_LENGTH = 5.0
DEFAULT_AUDIO_SAMPLE_RATE = 48000
DEFAULT_SILENCE_INTERVAL = 5.0

# MQTT Topics
TOPIC_STATE = f"{DEFAULT_MQTT_TOPIC_BASE}/state"
TOPIC_TITLE = f"{DEFAULT_MQTT_TOPIC_BASE}/title"
TOPIC_ARTIST = f"{DEFAULT_MQTT_TOPIC_BASE}/artist"
TOPIC_ALBUM = f"{DEFAULT_MQTT_TOPIC_BASE}/album"
TOPIC_ALBUM_ART = f"{DEFAULT_MQTT_TOPIC_BASE}/album_art"
TOPIC_NOW_PLAYING = f"{DEFAULT_MQTT_TOPIC_BASE}/now_playing"

# State values
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"
STATE_IDLE = "idle"
STATE_OFF = "off"
STATE_STOPPED = "stopped"

# Update intervals
SCAN_INTERVAL = 10  # seconds
