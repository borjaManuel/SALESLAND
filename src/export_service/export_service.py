from datetime import datetime
from pathlib import Path

from config.settings import load_settings
from counter.counter import get_last_number
from logger.logger import Logger
from matcher.matcher import FilePair, match_files
from mover.mover import move_pair
from renamer.renamer import rename_pair
from scanner.scanner import scan_files

logger = Logger.get_logger(__name__)


MONTHS = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}


def run_export() -> None:
    """
    Executes the complete export process.
    """
    logger.info("Starting export service")

    settings = load_settings()

    files = scan_files(settings)

    if not files:
        logger.info("No files found to process")
        return

    pairs = match_files(files)

    if not pairs:
        logger.info("No PDF/CSV pairs found to process")
        return

    # Group pairs by month using the CSV modification date.
    pairs_by_month: dict[str, list[FilePair]] = {}

    for pair in pairs:
        modification_date = datetime.fromtimestamp(pair.csv.stat().st_mtime)

        month = MONTHS[modification_date.month]

        pairs_by_month.setdefault(month, []).append(pair)

    # Process each month independently.
    for month, month_pairs in pairs_by_month.items():

        month_folder = settings.sftp_output_folder / month

        # Sort by CSV modification date/time.
        month_pairs.sort(key=lambda pair: pair.csv.stat().st_mtime)

        # Get the last number used in this month.
        last_number = get_last_number(month_folder)

        logger.info(
            "Processing %d pairs for %s. Starting number: %04d",
            len(month_pairs),
            month,
            last_number + 1,
        )

        # Assign consecutive numbers.
        for index, pair in enumerate(month_pairs, start=1):

            number = last_number + index

            renamed_pair = rename_pair(
                pair,
                number,
                month_folder,
            )

            move_pair(
                pair,
                renamed_pair,
            )

    logger.info("Export service finished successfully")


if __name__ == "__main__":
    run_export()
