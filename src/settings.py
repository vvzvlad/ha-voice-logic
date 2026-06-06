"""Single source of configuration via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Credentials for external public APIs — required, no defaults.
    # Missing in the environment → Settings() raises on startup.
    groq_api_key: str
    weather_api_key: str

    # Own service address — required, no default (depends on deployment).
    smarthome_url: str

    # Non-secret configuration — sensible defaults are fine.
    groq_model: str = "openai/gpt-oss-120b"
    weather_city: str = "Moscow"
    # Optional proxy for the Groq API only (e.g. "socks5h://10.31.41.70:1080");
    # empty string means a direct request.
    groq_proxy: str = ""
    log_level: str = "INFO"
    port: int = 8081

    # Runtime state — always under data/.
    system_prompt_path: str = "data/system_prompt.md"
    context_path: str = "data/context.txt"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
