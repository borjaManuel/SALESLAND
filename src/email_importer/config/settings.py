import os
from dataclasses import dataclass
from pathlib import Path

from config.paths import SRC_DIR
from dotenv import load_dotenv

load_dotenv(SRC_DIR / "email_importer" / ".env")


@dataclass(frozen=True)
class Settings:
    imap_server: str
    imap_port: int
    imap_user: str
    imap_password: str
    imap_folder: str
    pdf_output_folder: Path
    log_level: str


def load_settings() -> Settings:
    """
    Loads the application configuration from the .env file and validates
    that all required environment variables are present.

    Returns:
        Settings: The application configuration.

    Raises:
        RuntimeError: If any required environment variable is missing.
    """
    required = [
        "IMAP_SERVER",
        "IMAP_PORT",
        "IMAP_USER",
        "IMAP_PASSWORD",
        "IMAP_FOLDER",
        "PDF_OUTPUT_FOLDER",
    ]

    missing = [variable for variable in required if not os.getenv(variable)]

    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    return Settings(
        imap_server=os.environ["IMAP_SERVER"],
        imap_port=int(os.environ["IMAP_PORT"]),
        imap_user=os.environ["IMAP_USER"],
        imap_password=os.environ["IMAP_PASSWORD"],
        imap_folder=os.environ["IMAP_FOLDER"],
        pdf_output_folder=Path(os.environ["PDF_OUTPUT_FOLDER"]),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
