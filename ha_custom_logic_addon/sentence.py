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

    async def callback(
        sentence: str,
        result: Any | None = None,
        device_id: str | None = None,
    ) -> str:
        payload: dict[str, Any] = {"text": sentence}
        if device_id is not None:
            payload["device_id"] = device_id
        if result is not None:
            # Only include JSON-safe subset
            try:
                slots = getattr(result, "slots", None)
                if slots is not None:
                    payload["result"] = {"slots": dict(slots)}
            except Exception as exc:
                LOGGER.warning("Result slots extraction failed in callback: %s", str(exc))

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
            return "Ошибка: превышено время ожидания ответа"
        except aiohttp.ClientError as exc:
            LOGGER.error("HTTP client error in sentence callback %s: %s", endpoint_url, str(exc))
            return "Ошибка: сбой сети при обращении к сервису"

    remove = default_agent.register_trigger(sentences=["{question}"], callback=callback)
    return remove



