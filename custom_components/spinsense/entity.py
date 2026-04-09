"""Base entity for SpinSense integration."""

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


class SpinSenseEntity(Entity):
    """Base entity for SpinSense."""

    def __init__(self, hass, config_entry, device_name: str = "SpinSense"):
        """Initialize the entity."""
        self.hass = hass
        self._config_entry = config_entry
        self._device_name = device_name
        self._attr_has_entity_name = True
        self._attr_should_poll = False

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name=self._device_name,
            manufacturer="SpinSense",
            model="Vinyl Record Player",
        )
