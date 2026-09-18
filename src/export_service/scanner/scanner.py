from datetime import datetime, timedelta
from pathlib import Path

from config.settings import Settings
from logger.logger import Logger

logger = Logger.get_logger(__name__)


def scan_files(settings: Settings) -> list[Path]:
    """
    Scans the Kodak output folder and returns PDF and CSV files
    older than 5 minutes.

    Args:
        settings: Application configuration.

    Returns:
        List of PDF and CSV files found in the Kodak output folder
        that are older than 5 minutes.

    Raises:
        FileNotFoundError: If the Kodak output folder does not exist.
        NotADirectoryError: If the Kodak output path is not a directory.
    """
    source_folder = settings.kodak_output_folder

    if not source_folder.exists():
        logger.error("Kodak output folder does not exist: %s", source_folder)
        raise FileNotFoundError(f"Kodak output folder does not exist: {source_folder}")

    if not source_folder.is_dir():
        logger.error("Kodak output path is not a directory: %s", source_folder)
        raise NotADirectoryError(
            f"Kodak output path is not a directory: {source_folder}"
        )

    logger.info("Scanning Kodak output folder: %s", source_folder)

    minimum_age = timedelta(minutes=5)
    current_time = datetime.now()

    files = [
        file
        for file in source_folder.iterdir()
        if (
            file.is_file()
            and file.suffix.lower() in {".pdf", ".csv"}
            and current_time - datetime.fromtimestamp(file.stat().st_mtime)
            >= minimum_age
        )
    ]

    logger.info("Found %d PDF/CSV files older than 5 minutes", len(files))

    return files
