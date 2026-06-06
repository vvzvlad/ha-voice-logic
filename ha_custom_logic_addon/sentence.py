"""Wildcard sentence trigger registration and HTTP forwarding."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import logging
from typing import TYPE_CHECKING, Any

import aiohttp

from homeassistant.components.conversation import ConversationInput
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DEFAULT_TIMEOUT, REQUEST_SOURCE

if TYPE_CHECKING:
    from hassil.recognize import RecognizeResult

_LOGGER = logging.getLogger(__name__)

# A sentence-trigger callback receives the recognized conversation input and the
# matcher result, and returns the assistant reply (or None to fall through).
SentenceTriggerCallback = Callable[
    [ConversationInput, "RecognizeResult"], Awaitable[str | None]
]

# Wildcard template that matches any sentence and captures the whole utterance.
_WILDCARD_SENTENCES = ["{question}"]


def async_register_wildcard_trigger(
    hass: HomeAssistant, endpoint_url: str
) -> CALLBACK_TYPE:
    """Register a wildcard sentence trigger and return a remover callback."""

    async def _handle_sentence(
        user_input: ConversationInput, _result: RecognizeResult
    ) -> str | None:
        """Forward the recognized sentence and return the endpoint's reply."""
        return await _forward_sentence(hass, endpoint_url, user_input)

    return _register_trigger(hass, _WILDCARD_SENTENCES, _handle_sentence)


def _register_trigger(
    hass: HomeAssistant,
    sentences: list[str],
    handler: SentenceTriggerCallback,
) -> CALLBACK_TYPE:
    """Register a sentence trigger, handling the HA API change across versions.

    HA >= 2025.12 exposes ``register_trigger`` on the conversation AgentManager
    (keyword ``trigger_callback``); older releases expose it on the DefaultAgent
    stored under ``DATA_DEFAULT_ENTITY`` (keyword ``callback``). The trigger
    callback signature is identical in both.
    """
    try:
        from homeassistant.components.conversation.agent_manager import (
            get_agent_manager,
        )

        manager = get_agent_manager(hass)
    except ImportError:
        manager = None

    if manager is not None and hasattr(manager, "register_trigger"):
        return manager.register_trigger(
            sentences=sentences, trigger_callback=handler
        )

    from homeassistant.components.conversation.default_agent import (
        DATA_DEFAULT_ENTITY,
    )

    default_agent = hass.data.get(DATA_DEFAULT_ENTITY)
    if default_agent is not None:
        return default_agent.register_trigger(
            sentences=sentences, callback=handler
        )

    _LOGGER.error(
        "Conversation default agent is unavailable; the sentence trigger was "
        "not registered"
    )
    return lambda: None


async def _forward_sentence(
    hass: HomeAssistant, endpoint_url: str, user_input: ConversationInput
) -> str:
    """Forward a recognized sentence to the endpoint and return its text reply."""
    payload: dict[str, Any] = {
        "request": {"text": user_input.text, "source": REQUEST_SOURCE}
    }
    if user_input.device_id is not None:
        payload["device"] = {"id": user_input.device_id}

    session = async_get_clientsession(hass)
    try:
        async with session.post(
            endpoint_url,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT),
        ) as response:
            body = await response.text()
            if response.status != 200:
                _LOGGER.error(
                    "Endpoint %s returned HTTP %s: %s",
                    endpoint_url,
                    response.status,
                    body,
                )
                return "Ошибка: внешний сервис недоступен"
            return body
    except TimeoutError:
        _LOGGER.error(
            "Timed out after %ss waiting for %s", DEFAULT_TIMEOUT, endpoint_url
        )
        return "Ошибка: превышено время ожидания ответа LLM-прокси"
    except aiohttp.ClientError as err:
        _LOGGER.error("Network error contacting %s: %s", endpoint_url, err)
        return "Ошибка: сбой сети при обращении к LLM-прокси"
