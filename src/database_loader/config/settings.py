import os
from dataclasses import dataclass

from config.paths import SRC_DIR
from dotenv import load_dotenv

load_dotenv(SRC_DIR / "database_loader" / ".env")


@dataclass(frozen=True)
class Settings:
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str


def load_settings() -> Settings:
    """
    Loads the application configuration from the .env file and validates
    that all required environment variables are present.

    Returns:
        Settings: The application configuration.

    Raises:
        RuntimeError: If any required environment variable is missing.
    """
    required = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]

    missing = [x for x in required if not os.getenv(x)]

    if missing:
        raise RuntimeError(f"Faltan las variables: {', '.join(missing)}")

    return Settings(
        db_host=os.environ["DB_HOST"],
        db_port=int(os.environ["DB_PORT"]),
        db_name=os.environ["DB_NAME"],
        db_user=os.environ["DB_USER"],
        db_password=os.environ["DB_PASSWORD"],
    )
