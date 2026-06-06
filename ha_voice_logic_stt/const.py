"""Constants for the HA Voice Logic STT integration."""

DOMAIN = "ha_voice_logic_stt"

CONF_BASE_URL = "base_url"
# Base URL of the ha-voice-logic relay, including the OpenAI-style /v1 prefix.
# The transcription endpoint is "{base_url}/audio/transcriptions".
DEFAULT_BASE_URL = "http://ha_voice_logic:8081/v1"
