"""The SpinSense integration."""

import asyncio
import logging
from typing import Final

import paho.mqtt.client as mqtt

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: Final = [Platform.MEDIA_PLAYER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SpinSense from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Store the config entry
    hass.data[DOMAIN][entry.entry_id] = {
        "config": entry.data,
        "mqtt_client": None,
    }

    # Setup MQTT connection
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    mqtt_host = entry.data.get("mqtt_host")
    mqtt_port = entry.data.get("mqtt_port", 1883)
    mqtt_user = entry.data.get("mqtt_user", "")
    mqtt_password = entry.data.get("mqtt_password", "")

    if mqtt_user and mqtt_password:
        mqtt_client.username_pw_set(mqtt_user, mqtt_password)

    try:
        mqtt_client.connect(mqtt_host, mqtt_port, keepalive=60)
        mqtt_client.loop_start()
        hass.data[DOMAIN][entry.entry_id]["mqtt_client"] = mqtt_client
        _LOGGER.info("Connected to MQTT broker at %s:%s", mqtt_host, mqtt_port)
    except Exception as e:
        _LOGGER.error("Failed to connect to MQTT broker: %s", e)
        return False

    # Forward entry setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Add listener for when entry is unloaded
    entry.add_update_listener(async_update_listener)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        mqtt_client = hass.data[DOMAIN][entry.entry_id].get("mqtt_client")
        if mqtt_client:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()

        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
