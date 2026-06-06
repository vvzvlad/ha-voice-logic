# AGENTS

Онбординг для агентов и людей, работающих с проектом.

## Структура

- `src/` — код приложения (HTTP-сервер, клиент Groq, обработка команд, погода, промпт).
- `tests/` — тесты на pytest.
- `data/` — рантайм-стейт (system_prompt.md, context.txt). В git не коммитится (кроме `.gitkeep`), в Docker — volume.
- `templates/` — статика, попадающая в образ (`default_prompt.md` — шаблон системного промпта).
- `ha_custom_logic_addon/` — отдельная HA-интеграция (клиент этого сервиса). Не относится к коду прокси.

## Setup

```
make install        # создаёт .venv и ставит dev/test-зависимости
cp .env.example .env  # затем заполнить значения
```

## Running tests

```
make test
```

## Running the app

```
make run
```

## Conventions

- Рантайм-стейт пишется только в `data/`.
- Конфигурация — из ENV / `.env` через `src/settings.py` (pydantic-settings), единая точка.
- Креды и адреса своих сервисов (`GROQ_API_KEY`, `WEATHER_API_KEY`, `SMARTHOME_URL`) живут только в `.env` — никаких дефолтных кред в коде.
- Все комментарии в коде — на английском.
- Рутинные действия — через `make`.
- Тесты обязательны; в CI задача `build` зависит от `test`.
