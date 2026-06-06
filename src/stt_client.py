"""Groq Whisper speech-to-text (STT) proxy client."""

import logging
import re

import requests  # type: ignore
from requests_toolbelt.multipart.decoder import MultipartDecoder  # type: ignore

from src.settings import settings

logger = logging.getLogger(__name__)

GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

# Empty OpenAI-style transcription result. HA reads it as "not recognized"
# and keeps the voice pipeline alive instead of crashing on errors.
_EMPTY_RESULT = b'{"text": ""}'


def _extract_file_part(body, content_type):
    """Return (filename, file_bytes, file_content_type) for the multipart
    part named "file", or None if it cannot be found."""
    decoder = MultipartDecoder(body, content_type)
    for part in decoder.parts:
        disposition = part.headers.get(b"Content-Disposition", b"")
        if isinstance(disposition, bytes):
            disposition = disposition.decode("utf-8", "ignore")
        name_match = re.search(r'(?:^|;|\s)name="([^"]*)"', disposition)
        if not name_match or name_match.group(1) != "file":
            continue
        filename_match = re.search(r'filename="([^"]*)"', disposition)
        filename = filename_match.group(1) if filename_match else None
        part_ct = part.headers.get(b"Content-Type")
        if isinstance(part_ct, bytes):
            part_ct = part_ct.decode("utf-8", "ignore")
        return filename, part.content, part_ct
    return None


def transcribe_audio(body, content_type):
    """Proxy an OpenAI-compatible multipart STT request to Groq Whisper.

    Returns a (status_code, body_bytes) tuple. On any failure returns
    (200, b'{"text": ""}') so the HA voice pipeline degrades gracefully.
    The incoming Authorization header is ignored; the real key from
    settings is used instead.
    """
    try:
        extracted = _extract_file_part(body, content_type)
    except Exception as e:  # malformed / non-multipart body
        logger.error(f"STT multipart parse failed: {str(e)}")
        return 200, _EMPTY_RESULT

    if extracted is None:
        logger.error("STT request has no 'file' part")
        return 200, _EMPTY_RESULT

    filename, file_bytes, file_content_type = extracted

    # Force our own parameters; transcription is fixed to Russian, JSON output.
    files = {
        "file": (
            filename or "audio.wav",
            file_bytes,
            file_content_type or "application/octet-stream",
        )
    }
    data = {
        "model": settings.groq_stt_model,
        "language": "ru",
        "response_format": "json",
        "temperature": "0",
    }
    headers = {"Authorization": f"Bearer {settings.groq_api_key}"}
    _proxies = (
        {"https": settings.groq_proxy, "http": settings.groq_proxy}
        if settings.groq_proxy
        else None
    )

    try:
        r = requests.post(
            GROQ_STT_URL,
            headers=headers,
            files=files,
            data=data,
            proxies=_proxies,
            verify=False,
            timeout=60,
        )
    except requests.RequestException as e:
        logger.error(f"STT request to Groq failed: {str(e)}")
        return 200, _EMPTY_RESULT

    if r.status_code != 200:
        # Log Groq's status and body, but never propagate the failure.
        logger.error(f"Groq STT error: {r.status_code} - {r.text}")
        return 200, _EMPTY_RESULT

    logger.info(f"Groq STT response status: {r.status_code}")
    # Pass Groq's JSON body through unchanged (OpenAI format: {"text": "..."}).
    return r.status_code, r.content
