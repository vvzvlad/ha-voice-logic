#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# flake8: noqa
# pylint: disable=broad-exception-raised, raise-missing-from, too-many-arguments, redefined-outer-name
# pylint: disable=multiple-statements, logging-fstring-interpolation, trailing-whitespace, line-too-long
# pylint: disable=broad-exception-caught, missing-function-docstring, missing-class-docstring
# pylint: disable=f-string-without-interpolation, import-error
# pylance: disable=reportMissingImports, reportMissingModuleSource
# mypy: disable-error-code="import-untyped,call-arg,import-not-found"

"""Config flow for ha_custom_logic_addon."""

from __future__ import annotations
from typing import Any
import voluptuous as vol # type: ignore[import-untyped]
from homeassistant import config_entries # type: ignore[import-untyped]
from . import DOMAIN, CONF_ENDPOINT_URL, DEFAULT_ENDPOINT_URL


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ha_custom_logic_addon."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(
                title="HA Custom Logic",
                data={CONF_ENDPOINT_URL: user_input[CONF_ENDPOINT_URL]},
            )

        schema = vol.Schema({
            vol.Required(CONF_ENDPOINT_URL, default=DEFAULT_ENDPOINT_URL): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data={CONF_ENDPOINT_URL: user_input[CONF_ENDPOINT_URL]})

        current = (
            self.entry.options.get(CONF_ENDPOINT_URL)
            or self.entry.data.get(CONF_ENDPOINT_URL)
            or DEFAULT_ENDPOINT_URL
        )
        schema = vol.Schema({vol.Required(CONF_ENDPOINT_URL, default=current): str})
        return self.async_show_form(step_id="init", data_schema=schema)


async def async_get_options_flow(config_entry: config_entries.ConfigEntry):
    return OptionsFlowHandler(config_entry)


