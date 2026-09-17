from dataclasses import dataclass
from pathlib import Path

from logger.logger import Logger

logger = Logger.get_logger(__name__)


@dataclass(frozen=True)
class FilePair:
    pdf: Path
    csv: Path


def match_files(files: list[Path]) -> list[FilePair]:
    """
    Matches PDF and CSV files with the same base filename.

    Args:
        files: Files found by the scanner.

    Returns:
        List of matched PDF/CSV pairs.
    """
    pdf_files = {file.stem: file for file in files if file.suffix.lower() == ".pdf"}

    csv_files = {file.stem: file for file in files if file.suffix.lower() == ".csv"}

    common_names = pdf_files.keys() & csv_files.keys()

    pairs = [
        FilePair(
            pdf=pdf_files[name],
            csv=csv_files[name],
        )
        for name in common_names
    ]

    logger.info("Found %d PDF/CSV pairs", len(pairs))

    return pairs
