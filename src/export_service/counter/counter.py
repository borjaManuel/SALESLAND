import re
from pathlib import Path

from logger.logger import Logger

logger = Logger.get_logger(__name__)


def get_last_number(folder: Path) -> int:
    """
    Returns the highest numeric prefix found in a folder.

    Expected filename format:
        0001_filename.pdf
        0002_filename.csv

    Args:
        folder: Monthly destination folder.

    Returns:
        Highest numeric prefix found. Returns 0 if no valid prefix exists.
    """
    if not folder.exists():
        logger.info("Folder does not exist: %s", folder)
        return 0

    if not folder.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {folder}")

    last_number = 0

    for file in folder.iterdir():

        if not file.is_file():
            continue

        match = re.match(r"^(\d+)_", file.name)

        if not match:
            continue

        number = int(match.group(1))

        if number > last_number:
            last_number = number

    logger.info(
        "Last number found in folder %s: %04d",
        folder,
        last_number,
    )

    return last_number
