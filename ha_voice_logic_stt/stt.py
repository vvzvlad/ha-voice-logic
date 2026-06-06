"""Speech-to-text entity backed by the ha-voice-logic relay."""

from __future__ import annotations

from collections.abc import AsyncIterable
import io
import logging
import wave

import aiohttp

from homeassistant.components.stt import (
    AudioBitRates,
    AudioChannels,
    AudioCodecs,
    AudioFormats,
    AudioSampleRates,
    SpeechMetadata,
    SpeechResult,
    SpeechResultState,
    SpeechToTextEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_BASE_URL, DEFAULT_BASE_URL

_LOGGER = logging.getLogger(__name__)

# The relay forces Russian transcription server-side, so this entity only
# advertises Russian. Extend this list if the backend gains more languages.
SUPPORTED_LANGUAGES = ["ru"]

# Fixed PCM/WAV parameters matching the supported_* properties below.
_CHANNELS = 1  # mono
_SAMPLE_WIDTH_BYTES = 2  # 16-bit samples
_SAMPLE_RATE = 16000  # Hz

# Timeout for a single transcription request to the relay.
_TIMEOUT = aiohttp.ClientTimeout(total=60)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the STT entity from a config entry."""
    base_url = config_entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL)
    async_add_entities([HaVoiceLogicSttEntity(config_entry, base_url)])


class HaVoiceLogicSttEntity(SpeechToTextEntity):
    """Forward captured audio to the relay and return the recognized text."""

    def __init__(self, config_entry: ConfigEntry, base_url: str) -> None:
        """Initialize the STT entity."""
        super().__init__()
        # Strip a trailing slash so the endpoint path joins cleanly.
        self._base_url = base_url.rstrip("/")
        self._attr_name = "HA Voice Logic STT"
        self._attr_unique_id = f"{config_entry.entry_id}-stt"

    @property
    def supported_languages(self) -> list[str]:
        """Return the list of supported languages."""
        return SUPPORTED_LANGUAGES

    @property
    def supported_formats(self) -> list[AudioFormats]:
        """Return the list of supported audio formats."""
        return [AudioFormats.WAV]

    @property
    def supported_codecs(self) -> list[AudioCodecs]:
        """Return the list of supported audio codecs."""
        return [AudioCodecs.PCM]

    @property
    def supported_bit_rates(self) -> list[AudioBitRates]:
        """Return the list of supported bit rates."""
        return [AudioBitRates.BITRATE_16]

    @property
    def supported_sample_rates(self) -> list[AudioSampleRates]:
        """Return the list of supported sample rates."""
        return [AudioSampleRates.SAMPLERATE_16000]

    @property
    def supported_channels(self) -> list[AudioChannels]:
        """Return the list of supported channels."""
        return [AudioChannels.CHANNEL_MONO]

    async def async_process_audio_stream(
        self, metadata: SpeechMetadata, stream: AsyncIterable[bytes]
    ) -> SpeechResult:
        """Collect raw PCM, wrap it into WAV and POST it to the relay."""
        try:
            audio = bytearray()
            async for chunk in stream:
                audio.extend(chunk)

            wav_bytes = self._pcm_to_wav(bytes(audio))

            # Reproduce the requests-style files=/data= multipart body. The relay
            # looks for the part named "file"; the "model" value is a placeholder
            # because the relay overrides the model server-side.
            form = aiohttp.FormData()
            form.add_field("model", "whisper-1")
            form.add_field(
                "file",
                wav_bytes,
                filename="audio.wav",
                content_type="audio/wav",
            )

            session = async_get_clientsession(self.hass)
            url = f"{self._base_url}/audio/transcriptions"
            async with session.post(
                url, data=form, timeout=_TIMEOUT
            ) as response:
                if response.status // 100 != 2:
                    _LOGGER.error(
                        "Relay %s returned HTTP %s", url, response.status
                    )
                    return SpeechResult("", SpeechResultState.ERROR)
                payload = await response.json(content_type=None)

            text = payload.get("text") if isinstance(payload, dict) else None
            return SpeechResult(
                text if isinstance(text, str) else "", SpeechResultState.SUCCESS
            )
        except Exception as err:  # noqa: BLE001 - any failure degrades to ERROR
            _LOGGER.error("STT processing failed: %s", err)
            return SpeechResult("", SpeechResultState.ERROR)

    @staticmethod
    def _pcm_to_wav(pcm: bytes) -> bytes:
        """Wrap raw 16-bit / 16 kHz mono PCM into an in-memory WAV container."""
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(_CHANNELS)
            wav_file.setsampwidth(_SAMPLE_WIDTH_BYTES)
            wav_file.setframerate(_SAMPLE_RATE)
            wav_file.writeframes(pcm)
        return buffer.getvalue()
