import os
import re
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

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
    periodic_data_dir: Path

    @property
    def db_schema(self) -> str | None:
        """
        PostgreSQL schema where the tables are created and loaded
        (e.g. "exchange"). When not set, the database default is used.
        """
        value = os.getenv("DB_SCHEMA", "").strip()
        if not value:
            return None

        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
            raise RuntimeError(f"DB_SCHEMA is not a valid schema name: {value}")

        return value

    @property
    def visa_data_dir(self) -> Path | None:
        """Shared folder where the customer leaves the VISA batches."""
        value = os.getenv("VISA_DATA_DIR")
        return Path(value) if value else None

    @property
    def visa_output_dir(self) -> Path | None:
        """Local folder watched by InfoInput for the VISA invoices."""
        value = os.getenv("VISA_OUTPUT_DIR")
        return Path(value) if value else None

    @property
    def visa_minimum_age(self) -> timedelta:
        """
        Time a VISA batch must remain unchanged before being imported,
        so that batches still being copied are skipped.
        """
        value = os.getenv("VISA_MINIMUM_AGE_MINUTES", "").strip()
        if not value:
            return timedelta(minutes=2)

        try:
            minutes = float(value)
        except ValueError as error:
            raise RuntimeError(
                f"VISA_MINIMUM_AGE_MINUTES must be a number: {value}"
            ) from error

        if minutes < 0:
            raise RuntimeError("VISA_MINIMUM_AGE_MINUTES cannot be negative")

        return timedelta(minutes=minutes)

    @property
    def visa_history_dir(self) -> Path:
        """Local folder where the processed VISA Excel files are kept."""
        value = os.getenv("VISA_HISTORY_DIR")
        if value:
            return Path(value)
        return self.periodic_data_dir / "history" / "visa"


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
        periodic_data_dir=Path(os.environ["PERIODIC_DATA_DIR"]),
    )
