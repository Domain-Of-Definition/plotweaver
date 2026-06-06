from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    app_name: str = "PlotWeaver"
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = "deepseek-chat"
    openai_temperature: float = 0.2
    openai_response_format: str = "json_object"
    frontend_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
