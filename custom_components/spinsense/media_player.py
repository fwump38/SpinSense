"""Media player platform for SpinSense."""

import asyncio
import json
import logging
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CONF_MQTT_HOST,
    CONF_MQTT_PORT,
    CONF_MQTT_USER,
    CONF_MQTT_PASSWORD,
    TOPIC_STATE,
    TOPIC_TITLE,
    TOPIC_ARTIST,
    TOPIC_ALBUM,
    TOPIC_ALBUM_ART,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_STOPPED,
    STATE_IDLE,
    STATE_OFF,
)
from .entity import SpinSenseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SpinSense media player."""
    entities = [
        SpinSenseMediaPlayer(hass, config_entry),
    ]
    async_add_entities(entities)


class SpinSenseMediaPlayer(SpinSenseEntity, MediaPlayerEntity):
    """Representation of SpinSense as a media player."""

    _attr_supported_features = 0

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the media player."""
        super().__init__(hass, config_entry, "Vinyl Record Player")

        self._attr_unique_id = f"{DOMAIN}_{config_entry.entry_id}"
        self._attr_name = "Vinyl Record Player"

        self._state = MediaPlayerState.IDLE
        self._title = None
        self._artist = None
        self._album = None
        self._album_art_url = None

        self._mqtt_host = config_entry.data.get(CONF_MQTT_HOST)
        self._mqtt_port = config_entry.data.get(CONF_MQTT_PORT, 1883)
        self._mqtt_user = config_entry.data.get(CONF_MQTT_USER, "")
        self._mqtt_password = config_entry.data.get(CONF_MQTT_PASSWORD, "")

        self._subscriptions = {}

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT topics when added to hass."""
        await super().async_added_to_hass()

        # Get MQTT client from integration data
        mqtt_client = self.hass.data[DOMAIN][self._config_entry.entry_id].get("mqtt_client")

        if mqtt_client:
            # Subscribe to all relevant topics
            topics = [
                (TOPIC_STATE, 0),
                (TOPIC_TITLE, 0),
                (TOPIC_ARTIST, 0),
                (TOPIC_ALBUM, 0),
                (TOPIC_ALBUM_ART, 0),
            ]

            def on_message(client, userdata, msg):
                """Handle MQTT message."""
                self.hass.async_create_task(self._async_handle_mqtt_message(msg))

            for topic, qos in topics:
                try:
                    mqtt_client.subscribe(topic, qos)
                    self._subscriptions[topic] = True
                except Exception as e:
                    _LOGGER.error("Failed to subscribe to topic %s: %s", topic, e)

            mqtt_client.on_message = on_message
            _LOGGER.info("Subscribed to SpinSense MQTT topics")

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from MQTT topics when removed."""
        mqtt_client = self.hass.data[DOMAIN][self._config_entry.entry_id].get("mqtt_client")

        if mqtt_client:
            for topic in self._subscriptions:
                try:
                    mqtt_client.unsubscribe(topic)
                except Exception as e:
                    _LOGGER.error("Failed to unsubscribe from topic %s: %s", topic, e)

        await super().async_will_remove_from_hass()

    async def _async_handle_mqtt_message(self, msg: Any) -> None:
        """Handle incoming MQTT message."""
        topic = msg.topic
        payload = msg.payload.decode("utf-8", errors="ignore")

        try:
            if topic == TOPIC_STATE:
                # Map payload to MediaPlayerState
                state_map = {
                    STATE_PLAYING: MediaPlayerState.PLAYING,
                    STATE_PAUSED: MediaPlayerState.PAUSED,
                    STATE_STOPPED: MediaPlayerState.IDLE,
                    STATE_IDLE: MediaPlayerState.IDLE,
                    STATE_OFF: MediaPlayerState.OFF,
                }
                self._state = state_map.get(payload.lower(), MediaPlayerState.IDLE)

            elif topic == TOPIC_TITLE:
                self._title = payload or None

            elif topic == TOPIC_ARTIST:
                self._artist = payload or None

            elif topic == TOPIC_ALBUM:
                self._album = payload or None

            elif topic == TOPIC_ALBUM_ART:
                self._album_art_url = payload or None

            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Error processing MQTT message from %s: %s", topic, e)

    @property
    def state(self) -> MediaPlayerState | None:
        """Return the state of the player."""
        return self._state

    @property
    def media_title(self) -> str | None:
        """Return the title of current playing media."""
        return self._title

    @property
    def media_artist(self) -> str | None:
        """Return the artist of current playing media."""
        return self._artist

    @property
    def media_album_name(self) -> str | None:
        """Return the album name of current playing media."""
        return self._album

    @property
    def entity_picture(self) -> str | None:
        """Return the album art."""
        if not self._album_art_url:
            return None
        if self._album_art_url.startswith(("data:", "http://", "https://")):
            return self._album_art_url
        # Assume raw base64 when the payload is not a URL
        return f"data:image/jpeg;base64,{self._album_art_url}"

    async def async_play_media(
        self, media_type: str, media_id: str, **kwargs: Any
    ) -> None:
        """Play a piece of media."""
        # This is handled externally by the core engine
        _LOGGER.debug("Play media called (not supported for vinyl)")

    async def async_media_play(self) -> None:
        """Send play command."""
        # This is handled externally by the core engine
        _LOGGER.debug("Play command called (not supported for vinyl)")

    async def async_media_pause(self) -> None:
        """Send pause command."""
        # This is handled externally by the core engine
        _LOGGER.debug("Pause command called (not supported for vinyl)")

    async def async_media_stop(self) -> None:
        """Send stop command."""
        # This is handled externally by the core engine
        _LOGGER.debug("Stop command called (not supported for vinyl)")
