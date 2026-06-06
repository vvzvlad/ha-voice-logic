"""Constants for the HA Custom Logic integration."""

DOMAIN = "ha_custom_logic_addon"

CONF_ENDPOINT_URL = "endpoint_url"
DEFAULT_ENDPOINT_URL = "http://ha_voice_logic:8081"

# Timeout (seconds) for a single forwarded request to the external endpoint.
DEFAULT_TIMEOUT = 30

# Value reported to the endpoint so it can tell where the sentence came from.
REQUEST_SOURCE = "homeassistant.default_agent"
