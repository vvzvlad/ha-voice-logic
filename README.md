# ha-voice-logic

LLM-прокси для голосового ассистента Home Assistant.

Сервис принимает POST с распознанным текстом (`{"request": {"text": "..."}}`),
обращается к Groq API, исполняет команды умного дома через теги
`<command>device_id:value</command>` в ответе модели (POST на `SMARTHOME_URL`),
а также добавляет текущую дату/время и погоду в системный промпт.
Ответ возвращается plain-text.

## Запуск

```
make install            # создаёт .venv и ставит зависимости
cp .env.example .env     # затем заполнить значения
make run                 # запускает сервер (по умолчанию порт 8081)
```

## Переменные окружения

Все берутся из `.env` (см. `.env.example`):

- `GROQ_API_KEY` — ключ Groq API. **Обязательная.**
- `GROQ_MODEL` — модель Groq (по умолчанию `openai/gpt-oss-120b`).
- `GROQ_PROXY` — опциональный SOCKS/HTTP-прокси для внешних запросов (Groq API и OpenWeatherMap); пусто = прямой запрос.
- `WEATHER_API_KEY` — ключ OpenWeatherMap. **Обязательная.**
- `WEATHER_CITY` — город для погоды (по умолчанию `Moscow`).
- `SMARTHOME_URL` — эндпоинт для команд умного дома. **Обязательная.**
- `LOG_LEVEL` — уровень логирования (по умолчанию `INFO`).

## HA-интеграция

Каталог `ha_custom_logic_addon/` — это отдельная Home Assistant интеграция-клиент,
которая ходит к этому сервису.

## Деплой

Образ публикуется в `ghcr.io`, разворачивается через `docker-compose.yml`,
автообновление — через watchtower (label `com.centurylinklabs.watchtower.enable`).
Сервис внутренний: HA-интеграция обращается к нему по docker-сети
на `http://ha_voice_logic:8081`, порт на хост не публикуется.
