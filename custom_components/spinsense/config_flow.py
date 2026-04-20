"""Config flow for SpinSense integration."""

import logging
from typing import Any, Dict, Optional

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_HOST, CONF_PORT, DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SpinSenseConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SpinSense."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            host = user_input.get(CONF_HOST)
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            if not await self._async_validate_connection(host, port):
                errors["base"] = "cannot_connect"

            if not errors:
                await self.async_set_unique_id(f"{host}:{port}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"SpinSense ({host}:{port})",
                    data={"host": host, "port": port},
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_zeroconf(self, discovery_info) -> ConfigFlowResult:
        """Handle zeroconf discovery."""
        host = discovery_info.host
        if isinstance(host, bytes):
            host = host.decode("utf-8")
        host = str(host)

        port = discovery_info.port
        unique_id = f"{host}:{port}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"SpinSense ({host}:{port})",
            data={"host": host, "port": port},
        )

    async def _async_validate_connection(self, host: str, port: int) -> bool:
        """Validate HTTP connectivity to the SpinSense instance."""
        session = async_get_clientsession(self.hass)
        url = f"http://{host}:{port}/api/status"

        try:
            async with session.get(url, timeout=10) as response:
                return response.status == 200
        except Exception as err:
            _LOGGER.error("SpinSense connection validation failed: %s", err)
            return False
