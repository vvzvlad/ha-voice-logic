#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# flake8: noqa
# pylint: disable=broad-exception-raised, raise-missing-from, too-many-arguments, redefined-outer-name
# pylint: disable=multiple-statements, logging-fstring-interpolation, trailing-whitespace, line-too-long
# pylint: disable=broad-exception-caught, missing-function-docstring, missing-class-docstring
# pylint: disable=f-string-without-interpolation, import-error
# pylance: disable=reportMissingImports, reportMissingModuleSource
# mypy: disable-error-code="import-untyped,call-arg,import-not-found"

"""Home Assistant integration: ha_custom_logic_addon.

Registers a wildcard trigger in the Conversation DefaultAgent and forwards
recognized sentences to an external HTTP endpoint, returning its response
as the assistant reply.
"""

from __future__ import annotations

from typing import Any

import logging

from homeassistant.core import HomeAssistant # type: ignore[import-not-found]
from homeassistant.config_entries import ConfigEntry # type: ignore[import-not-found]

from .const import DOMAIN, CONF_ENDPOINT_URL, DEFAULT_ENDPOINT_URL
from .sentence import register_wildcard_trigger

LOGGER = logging.getLogger(__name__)


async def async_setup(_hass: HomeAssistant, _config: dict) -> bool: 
    """Set up via YAML is not supported; use UI config entries only."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    endpoint_url: str = entry.options.get(CONF_ENDPOINT_URL) or entry.data.get(CONF_ENDPOINT_URL) or DEFAULT_ENDPOINT_URL

    remove_trigger = register_wildcard_trigger(hass, endpoint_url)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"remove_trigger": remove_trigger}

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    store = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if store and (remove := store.get("remove_trigger")):
        try:
            remove()
        except RuntimeError as exc:
            LOGGER.error("Trigger removal failed for entry %s: %s", entry.entry_id, str(exc))
    return True


