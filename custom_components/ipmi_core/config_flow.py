"""UI configuration for IPMI Core."""

from __future__ import annotations

import asyncio

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.helpers import selector
import voluptuous as vol

from .client import IpmiCoreClient, IpmiCoreError
from .const import (
    CONF_POLL_SECONDS,
    DEFAULT_POLL_SECONDS,
    DEFAULT_PORT,
    DOMAIN,
    MAX_POLL_SECONDS,
    MIN_POLL_SECONDS,
    OPERATION_TIMEOUT,
)


class IpmiCoreConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Create one configuration entry per BMC endpoint."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = int(user_input[CONF_PORT])
            unique_id = f"{host.lower()}:{port}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            client = IpmiCoreClient(
                host=host,
                port=port,
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
            )
            try:
                async with asyncio.timeout(OPERATION_TIMEOUT):
                    await self.hass.async_add_executor_job(client.get_power)
            except (TimeoutError, IpmiCoreError):
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_NAME].strip(),
                    data={**user_input, CONF_HOST: host, CONF_PORT: port},
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="Servidor IPMI"): str,
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=65535)
                ),
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
                vol.Required(CONF_POLL_SECONDS, default=DEFAULT_POLL_SECONDS): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_POLL_SECONDS, max=MAX_POLL_SECONDS),
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
