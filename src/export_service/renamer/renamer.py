from dataclasses import dataclass
from pathlib import Path

from logger.logger import Logger
from matcher.matcher import FilePair

logger = Logger.get_logger(__name__)


@dataclass(frozen=True)
class RenamedPair:
    pdf: Path
    csv: Path


def rename_pair(
    pair: FilePair,
    number: int,
    output_folder: Path,
) -> RenamedPair:
    """
    Generates the destination paths for a matched PDF/CSV pair.

    Args:
        pair: Matched PDF/CSV pair.
        number: Number assigned to the pair.
        output_folder: Monthly destination folder.

    Returns:
        PDF/CSV pair with destination paths.
    """
    pdf_name = f"{number:04d}_{pair.pdf.name}"
    csv_name = f"{number:04d}_{pair.csv.name}"

    renamed_pair = RenamedPair(
        pdf=output_folder / pdf_name,
        csv=output_folder / csv_name,
    )

    logger.info(
        "Generated destination names: %s / %s",
        renamed_pair.pdf,
        renamed_pair.csv,
    )

    return renamed_pair
