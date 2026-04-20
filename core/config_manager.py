"""Configuration manager for SpinSense with environment variable support."""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

_LOGGER = logging.getLogger(__name__)


@dataclass
class AudioConfig:
    """Audio configuration."""

    threshold: float = 0.015
    sample_length: float = 5.0
    sample_rate: int = 48000
    silence_interval: float = 5.0
    device_name: Optional[str] = None
    device_index: Optional[int] = None


class SpinSenseConfig:
    """Configuration manager that reads from environment variables."""

    def __init__(self):
        self.audio = AudioConfig()
        self._load_from_environment()

    def _load_from_environment(self) -> None:
        """Load configuration from environment variables."""
        if audio_threshold := os.getenv("AUDIO_THRESHOLD"):
            try:
                self.audio.threshold = float(audio_threshold)
            except ValueError:
                _LOGGER.warning(f"Invalid AUDIO_THRESHOLD value: {audio_threshold}")

        if audio_sample_length := os.getenv("AUDIO_SAMPLE_LENGTH"):
            try:
                self.audio.sample_length = float(audio_sample_length)
            except ValueError:
                _LOGGER.warning(
                    f"Invalid AUDIO_SAMPLE_LENGTH value: {audio_sample_length}"
                )

        if audio_sample_rate := os.getenv("AUDIO_SAMPLE_RATE"):
            try:
                self.audio.sample_rate = int(audio_sample_rate)
            except ValueError:
                _LOGGER.warning(f"Invalid AUDIO_SAMPLE_RATE value: {audio_sample_rate}")

        if silence_interval := os.getenv("SILENCE_INTERVAL"):
            try:
                self.audio.silence_interval = float(silence_interval)
            except ValueError:
                _LOGGER.warning(f"Invalid SILENCE_INTERVAL value: {silence_interval}")

        if audio_device := os.getenv("AUDIO_DEVICE"):
            if audio_device.strip():
                self.audio.device_name = audio_device.strip()

        if audio_device_index := os.getenv("AUDIO_DEVICE_INDEX"):
            try:
                self.audio.device_index = int(audio_device_index)
            except ValueError:
                _LOGGER.warning(
                    f"Invalid AUDIO_DEVICE_INDEX value: {audio_device_index}"
                )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "threshold": self.audio.threshold,
            "sample_length": self.audio.sample_length,
            "sample_rate": self.audio.sample_rate,
            "silence_interval": self.audio.silence_interval,
            "device_name": self.audio.device_name,
            "device_index": self.audio.device_index,
        }


_config_instance: Optional[SpinSenseConfig] = None


def get_config() -> SpinSenseConfig:
    global _config_instance
    if _config_instance is None:
        _config_instance = SpinSenseConfig()
    return _config_instance


def reload_config() -> SpinSenseConfig:
    global _config_instance
    _config_instance = SpinSenseConfig()
    return _config_instance
