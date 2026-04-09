"""Config flow for SpinSense integration."""

import voluptuous as vol
from typing import Any, Dict, Optional
import logging

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_MQTT_HOST,
    CONF_MQTT_PORT,
    CONF_MQTT_USER,
    CONF_MQTT_PASSWORD,
    DEFAULT_MQTT_PORT,
)

_LOGGER = logging.getLogger(__name__)


class SpinSenseConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SpinSense."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            if not await self._async_validate_mqtt(
                user_input.get(CONF_MQTT_HOST),
                user_input.get(CONF_MQTT_PORT, DEFAULT_MQTT_PORT),
                user_input.get(CONF_MQTT_USER),
                user_input.get(CONF_MQTT_PASSWORD),
            ):
                errors["base"] = "invalid_mqtt"

            if not errors:
                await self.async_set_unique_id(user_input.get(CONF_MQTT_HOST))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"SpinSense ({user_input.get(CONF_MQTT_HOST)})",
                    data=user_input,
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_MQTT_HOST): str,
                vol.Required(CONF_MQTT_PORT, default=DEFAULT_MQTT_PORT): int,
                vol.Optional(CONF_MQTT_USER, default=""): str,
                vol.Optional(CONF_MQTT_PASSWORD, default=""): str,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    @staticmethod
    async def _async_validate_mqtt(
        host: str, port: int, user: str, password: str
    ) -> bool:
        """Validate MQTT connection."""
        import paho.mqtt.client as mqtt

        def on_connect(client, userdata, flags, rc, properties=None):
            userdata["connected"] = rc == 0

        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            userdata = {"connected": False}
            client.user_data_set(userdata)
            client.on_connect = on_connect

            if user:
                client.username_pw_set(user, password)

            client.connect(host, port, keepalive=5)
            client.loop_start()

            # Wait max 5 seconds for connection
            import asyncio
            for _ in range(50):
                if userdata.get("connected"):
                    client.loop_stop()
                    client.disconnect()
                    return True
                await asyncio.sleep(0.1)

            client.loop_stop()
            client.disconnect()
            return False
        except Exception as e:
            _LOGGER.error("MQTT validation error: %s", e)
            return False
