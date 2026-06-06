"""Config and options flow for the HA Custom Logic integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback

from .const import CONF_ENDPOINT_URL, DEFAULT_ENDPOINT_URL, DOMAIN


class HaCustomLogicConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial configuration of the integration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step initiated by the user."""
        if user_input is not None:
            return self.async_create_entry(
                title="HA Custom Logic",
                data={CONF_ENDPOINT_URL: user_input[CONF_ENDPOINT_URL]},
            )

        schema = vol.Schema(
            {vol.Required(CONF_ENDPOINT_URL, default=DEFAULT_ENDPOINT_URL): str}
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> HaCustomLogicOptionsFlow:
        """Return the options flow handler."""
        return HaCustomLogicOptionsFlow()


class HaCustomLogicOptionsFlow(OptionsFlow):
    """Handle updating the endpoint URL after the integration is set up."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the integration options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(
            CONF_ENDPOINT_URL,
            self.config_entry.data.get(CONF_ENDPOINT_URL, DEFAULT_ENDPOINT_URL),
        )
        schema = vol.Schema(
            {vol.Required(CONF_ENDPOINT_URL, default=current): str}
        )
        return self.async_show_form(step_id="init", data_schema=schema)
