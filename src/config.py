import secrets
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = ""
    debug: bool = True
    secret_key: str = ""
    jwt_lifetime_seconds: int = 3600
    pokemon_tcg_api_key: str = ""
    cookie_secure: bool = False
    rate_limit_enabled: bool = True
    base_dir: Path = Path(__file__).resolve().parent.parent

    @property
    def sqlite_path(self) -> Path:
        return self.base_dir / "trackercg.db"

    @model_validator(mode="after")
    def _validate_secrets(self) -> "Settings":
        if not self.secret_key:
            if self.debug:
                self.secret_key = secrets.token_urlsafe(48)
            else:
                raise ValueError(
                    "SECRET_KEY must be set when DEBUG=false (use the .env file)"
                )
        if not self.debug and not self.pokemon_tcg_api_key:
            raise ValueError(
                "POKEMON_TCG_API_KEY must be set when DEBUG=false (use the .env file)"
            )
        return self


settings = Settings()
