from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    telegram_bot_token: str
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    database_url: str
    owner_telegram_id: int
    allowed_telegram_ids: str = ""

    @property
    def allowed_user_ids(self) -> set[int]:
        ids = {self.owner_telegram_id}
        for raw in self.allowed_telegram_ids.split(","):
            raw = raw.strip()
            if raw:
                ids.add(int(raw))
        return ids

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ):
        # .env takes priority over already-set OS environment variables, since
        # this project's dev sandbox predefines empty ANTHROPIC_API_KEY, etc.
        return init_settings, dotenv_settings, env_settings, file_secret_settings


settings = Settings()
