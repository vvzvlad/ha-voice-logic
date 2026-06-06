"""The HA Custom Logic integration.

Registers a wildcard sentence trigger on the Conversation default agent and
forwards every recognized sentence to an external HTTP endpoint, returning the
endpoint's response as the assistant reply.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_ENDPOINT_URL, DEFAULT_ENDPOINT_URL
from .sentence import async_register_wildcard_trigger

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HA Custom Logic from a config entry."""
    endpoint_url = entry.options.get(
        CONF_ENDPOINT_URL,
        entry.data.get(CONF_ENDPOINT_URL, DEFAULT_ENDPOINT_URL),
    )

    # The remover returned by the trigger registration is kept on the entry so
    # async_unload_entry can detach the trigger cleanly.
    entry.runtime_data = async_register_wildcard_trigger(hass, endpoint_url)

    # Reload the entry (re-registering the trigger with the new URL) whenever the
    # user changes the options.
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and remove the registered trigger."""
    remove_trigger = entry.runtime_data
    if remove_trigger is not None:
        remove_trigger()
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
