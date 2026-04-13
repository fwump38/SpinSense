"""Configuration manager for SpinSense with environment variable support."""

import os
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

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


@dataclass
class SystemConfig:
    """System configuration."""
    auto_start: bool = False
    engine_status: str = "stopped"


class SpinSenseConfig:
    """Main configuration manager with environment variable support."""

    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration manager.
        
        Args:
            config_file: Path to config.json file. If None, uses default location.
        """
        self.config_file = config_file or self._find_config_file()
        self.system = SystemConfig()
        self.audio = AudioConfig()
        
        # Load from file first, then override with environment variables
        self._load_from_file()
        self._load_from_environment()

    @staticmethod
    def _find_config_file() -> Optional[str]:
        """Find config.json file in common locations."""
        possible_paths = [
            os.path.join(os.path.dirname(__file__), '..', 'config.json'),
            '/app/config.json',
            'config.json',
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return os.path.abspath(path)
        
        _LOGGER.warning("No config.json found in standard locations")
        return None

    def _load_from_file(self) -> None:
        """Load configuration from JSON file."""
        if not self.config_file or not os.path.exists(self.config_file):
            _LOGGER.info("No config.json file found, using defaults")
            return

        try:
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
            
            # System config
            system_data = config_data.get('System', {})
            self.system.auto_start = system_data.get('Auto_Start', False)
            self.system.engine_status = system_data.get('Engine_Status', 'stopped')
            
            # Audio config
            audio_data = config_data.get('Audio', {})
            self.audio.threshold = audio_data.get('Volume_Threshold', 0.015)
            self.audio.sample_length = audio_data.get('Song_Sample_Length', 5.0)
            self.audio.sample_rate = audio_data.get('Sample_Rate', 48000)
            self.audio.silence_interval = audio_data.get('Stopped_Silence_Interval', 5.0)
            
            # Hardware config
            hardware_data = config_data.get('Hardware', {})
            device_name = hardware_data.get('Mic_Device')
            if device_name and device_name not in ('', 'default'):
                self.audio.device_name = device_name

            _LOGGER.info(f"Loaded configuration from {self.config_file}")
        
        except json.JSONDecodeError as e:
            _LOGGER.error(f"Invalid JSON in config file: {e}")
        except Exception as e:
            _LOGGER.error(f"Error loading config file: {e}")

    def _load_from_environment(self) -> None:
        """Load configuration from environment variables (overrides file config)."""
        # Audio settings
        if audio_threshold := os.getenv('AUDIO_THRESHOLD'):
            try:
                self.audio.threshold = float(audio_threshold)
                _LOGGER.info(f"Audio threshold from env: {self.audio.threshold}")
            except ValueError:
                _LOGGER.warning(f"Invalid AUDIO_THRESHOLD value: {audio_threshold}")
        
        if audio_sample_length := os.getenv('AUDIO_SAMPLE_LENGTH'):
            try:
                self.audio.sample_length = float(audio_sample_length)
                _LOGGER.info(f"Audio sample length from env: {self.audio.sample_length}")
            except ValueError:
                _LOGGER.warning(f"Invalid AUDIO_SAMPLE_LENGTH value: {audio_sample_length}")
        
        if audio_sample_rate := os.getenv('AUDIO_SAMPLE_RATE'):
            try:
                self.audio.sample_rate = int(audio_sample_rate)
                _LOGGER.info(f"Audio sample rate from env: {self.audio.sample_rate}")
            except ValueError:
                _LOGGER.warning(f"Invalid AUDIO_SAMPLE_RATE value: {audio_sample_rate}")
        
        if silence_interval := os.getenv('SILENCE_INTERVAL'):
            try:
                self.audio.silence_interval = float(silence_interval)
                _LOGGER.info(f"Silence interval from env: {self.audio.silence_interval}")
            except ValueError:
                _LOGGER.warning(f"Invalid SILENCE_INTERVAL value: {silence_interval}")
        
        if audio_device := os.getenv('AUDIO_DEVICE'):
            if audio_device.strip():  # Only set if not empty
                self.audio.device_name = audio_device.strip()
                _LOGGER.info(f"Audio device from env: {self.audio.device_name}")
        
        if audio_device_index := os.getenv('AUDIO_DEVICE_INDEX'):
            try:
                self.audio.device_index = int(audio_device_index)
                _LOGGER.info(f"Audio device index from env: {self.audio.device_index}")
            except ValueError:
                _LOGGER.warning(f"Invalid AUDIO_DEVICE_INDEX value: {audio_device_index}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'System': {
                'Auto_Start': self.system.auto_start,
                'Engine_Status': self.system.engine_status,
            },
            'Audio': {
                'Volume_Threshold': self.audio.threshold,
                'Song_Sample_Length': self.audio.sample_length,
                'Sample_Rate': self.audio.sample_rate,
                'Stopped_Silence_Interval': self.audio.silence_interval,
                'Device_Name': self.audio.device_name,
                'Device_Index': self.audio.device_index,
            },
            'Hardware': {
                'Mic_Device': self.audio.device_name,
            }
        }

    def save_to_file(self, filepath: str) -> bool:
        """Save current configuration to file."""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
            _LOGGER.info(f"Configuration saved to {filepath}")
            return True
        except Exception as e:
            _LOGGER.error(f"Failed to save configuration: {e}")
            return False


# Singleton instance
_config_instance: Optional[SpinSenseConfig] = None


def get_config(config_file: Optional[str] = None) -> SpinSenseConfig:
    """Get or create the configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = SpinSenseConfig(config_file)
    return _config_instance


def reload_config(config_file: Optional[str] = None) -> SpinSenseConfig:
    """Reload configuration (useful for hot-reload scenarios)."""
    global _config_instance
    _config_instance = SpinSenseConfig(config_file)
    return _config_instance
