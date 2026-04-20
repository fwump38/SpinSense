import json
import os

from pydantic import BaseModel

# Path points to the root directory, one level up from /gui/
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")


# --- Pydantic Models for Strict Type Validation ---
class SystemConfig(BaseModel):
    Auto_Start: bool = False
    Engine_Status: str = "stopped"


class HardwareConfig(BaseModel):
    Mic_Device: str = "default"


class AudioConfig(BaseModel):
    Volume_Threshold: float = 0.0062
    Song_Sample_Length: float = 10.0
    New_Song_Silence_Interval: float = 10.0
    Stopped_Silence_Interval: float = 30.0


class SpinSenseConfig(BaseModel):
    System: SystemConfig = SystemConfig()
    Hardware: HardwareConfig = HardwareConfig()
    Audio: AudioConfig = AudioConfig()


# --- Core Functions ---
def get_default_config() -> dict:
    """Returns the default configuration as a dictionary."""
    return SpinSenseConfig().dict()


def load_config() -> dict:
    """Loads config.json. Recreates it with defaults if missing or invalid."""
    if not os.path.exists(CONFIG_PATH):
        save_config(get_default_config())

    try:
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)
            # Passing data to SpinSenseConfig validates the types automatically
            validated = SpinSenseConfig(**data)
            config = validated.dict()
    except Exception as e:
        print(f"⚠️ Error loading config, regenerating defaults: {e}")
        defaults = get_default_config()
        save_config(defaults)
        config = defaults

    # AUDIO_DEVICE env var takes precedence over file config
    audio_device = os.getenv("AUDIO_DEVICE", "").strip()
    if audio_device:
        config["Hardware"]["Mic_Device"] = audio_device

    return config


def save_config(data: dict) -> bool:
    """Validates and saves a dictionary to config.json."""
    try:
        validated = SpinSenseConfig(**data)
        with open(CONFIG_PATH, "w") as f:
            json.dump(validated.dict(), f, indent=2)
        return True
    except Exception as e:
        print(f"❌ Error saving config (Validation failed): {e}")
        return False
