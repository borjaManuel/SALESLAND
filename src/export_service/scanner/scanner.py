from pathlib import Path

from config.settings import Settings
from logger.logger import Logger

logger = Logger.get_logger(__name__)


def scan_files(settings: Settings) -> list[Path]:
    """
    Scans the Kodak output folder and returns all PDF and CSV files.

    Args:
        settings: Application configuration.

    Returns:
        List of PDF and CSV files found in the Kodak output folder.

    Raises:
        FileNotFoundError: If the Kodak output folder does not exist.
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

    files = [
        file
        for file in source_folder.iterdir()
        if file.is_file() and file.suffix.lower() in {".pdf", ".csv"}
    ]

    logger.info("Found %d PDF/CSV files", len(files))

    return files
