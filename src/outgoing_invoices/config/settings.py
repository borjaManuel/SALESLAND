import os
from dataclasses import dataclass
from pathlib import Path

from config.paths import SRC_DIR
from dotenv import load_dotenv

load_dotenv(SRC_DIR / "outgoing_invoices" / ".env")


@dataclass(frozen=True)
class Settings:
    csv_output_folder: Path
    excel_input_folder: Path


def load_settings() -> Settings:
    """
    Loads the application configuration from the .env file and validates
    that all required environment variables are present.

    Returns:
        Settings: The application configuration.

    Raises:
        RuntimeError: If any required environment variable is missing.
    """
    required = ["CSV_OUTPUT_FOLDER", "EXCEL_INPUT_FOLDER"]

    missing = [x for x in required if not os.getenv(x)]

    if missing:
        raise RuntimeError(f"Faltan las variables: {', '.join(missing)}")

    return Settings(
        csv_output_folder=Path(os.environ["CSV_OUTPUT_FOLDER"]),
        excel_input_folder=Path(os.environ["EXCEL_INPUT_FOLDER"]),
    )
