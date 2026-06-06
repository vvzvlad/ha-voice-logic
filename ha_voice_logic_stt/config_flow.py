"""Config flow for the HA Voice Logic STT integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_BASE_URL, DEFAULT_BASE_URL, DOMAIN


class HaVoiceLogicSttConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial configuration of the integration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step initiated by the user."""
        if user_input is not None:
            return self.async_create_entry(
                title="HA Voice Logic STT",
                data={CONF_BASE_URL: user_input[CONF_BASE_URL]},
            )

        schema = vol.Schema(
            {vol.Required(CONF_BASE_URL, default=DEFAULT_BASE_URL): str}
        )
        return self.async_show_form(step_id="user", data_schema=schema)
