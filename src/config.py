import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Settings:
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", f"sqlite:///./trackercg.db"
        )
    )
    debug: bool = field(
        default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true"
    )
    secret_key: str = field(
        default_factory=lambda: os.getenv(
            "SECRET_KEY", "changeme-in-production"
        )
    )
    jwt_lifetime_seconds: int = field(
        default_factory=lambda: int(
            os.getenv("JWT_LIFETIME_SECONDS", "3600")
        )
    )
    base_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)


settings = Settings()
