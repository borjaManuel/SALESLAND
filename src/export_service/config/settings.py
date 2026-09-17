import os
from dataclasses import dataclass
from pathlib import Path

from config.paths import SRC_DIR
from dotenv import load_dotenv

load_dotenv(SRC_DIR / "export_service" / ".env")


@dataclass(frozen=True)
class Settings:
    kodak_output_folder: Path
    sftp_output_folder: Path
    sftp_error_folder: Path


def load_settings() -> Settings:
    """
    Loads the application configuration from the .env file and validates
    that all required environment variables are present.

    Returns:
        Settings: The application configuration.

    Raises:
        RuntimeError: If any required environment variable is missing.
    """
    required = ["KODAK_OUTPUT_FOLDER", "SFTP_OUTPUT_FOLDER", "SFTP_ERROR_FOLDER"]

    missing = [x for x in required if not os.getenv(x)]

    if missing:
        raise RuntimeError(f"Faltan las variables: {', '.join(missing)}")

    return Settings(
        kodak_output_folder=Path(os.environ["KODAK_OUTPUT_FOLDER"]),
        sftp_output_folder=Path(os.environ["SFTP_OUTPUT_FOLDER"]),
        sftp_error_folder=Path(os.environ["SFTP_ERROR_FOLDER"]),
    )
