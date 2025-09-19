#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# flake8: noqa
# pylint: disable=broad-exception-raised, raise-missing-from, too-many-arguments, redefined-outer-name
# pylint: disable=multiple-statements, logging-fstring-interpolation, trailing-whitespace, line-too-long
# pylint: disable=broad-exception-caught, missing-function-docstring, missing-class-docstring
# pylint: disable=f-string-without-interpolation, import-error
# pylance: disable=reportMissingImports, reportMissingModuleSource
# mypy: disable-error-code="import-untyped,call-arg,import-not-found"

"""Wildcard trigger registration and HTTP forwarding logic."""

from __future__ import annotations

from typing import Any, Callable

import asyncio
import logging

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.components.conversation.default_agent import (
    DATA_DEFAULT_ENTITY,
    DefaultAgent,
)

LOGGER = logging.getLogger(__name__)


def register_wildcard_trigger(hass: HomeAssistant, endpoint_url: str) -> Callable[[], None]:
    """Register a wildcard trigger on DefaultAgent and return its remover."""
    default_agent = hass.data.get(DATA_DEFAULT_ENTITY)
    if not isinstance(default_agent, DefaultAgent):
        LOGGER.error("Conversation DefaultAgent not available in register_wildcard_trigger")
        # Return a no-op remover so unload doesn't crash
        return lambda: None

    def _extract_text(value: Any) -> str:
        """Return textual content from possible ConversationInput or plain string."""
        if isinstance(value, str):
            return value
        # Try common attributes seen in HA ConversationInput or similar
        for attr in ("text", "sentence", "utterance", "query", "input"):
            try:
                candidate = getattr(value, attr, None)
            except Exception:
                candidate = None
            if isinstance(candidate, str):
                return candidate
        # Fallback to string conversion
        try:
            return str(value)
        except Exception:
            return ""

    async def callback(
        sentence: Any,
        _result: Any | None = None,
        device_id: str | None = None,
    ) -> str:
        # Strict schema for server: { "request": {"text": str, "source": str}, "device": {"id": str}? }
        sentence_text = _extract_text(sentence)
        payload: dict[str, Any] = {
            "request": {
                "text": sentence_text,
                "source": "homeassistant.default_agent",
            }
        }
        if device_id is not None:
            payload["device"] = {"id": device_id}

        timeout = aiohttp.ClientTimeout(total=30)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    endpoint_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                ) as resp:
                    status = resp.status
                    text = await resp.text()
                    if status != 200:
                        LOGGER.error(
                            "HTTP error in sentence callback %s: status %s, body: %s",
                            endpoint_url,
                            status,
                            text,
                        )
                        return "Ошибка: внешний сервис недоступен"
                    return text
        except asyncio.TimeoutError:
            LOGGER.error("HTTP timeout in sentence callback %s: 30 seconds", endpoint_url)
            return "Ошибка: превышено время ожидания ответа LLM-прокси"
        except aiohttp.ClientError as exc:
            LOGGER.error("HTTP client error in sentence callback %s: %s", endpoint_url, str(exc))
            return "Ошибка: сбой сети при обращении к LLM-прокси"

    remove = default_agent.register_trigger(sentences=["{question}"], callback=callback)
    return remove



