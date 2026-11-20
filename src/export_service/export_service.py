import re
from collections.abc import Callable
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


# VISA files are named "<factura>_<DD-MM-YYYY[_N]>" after their batch.
VISA_BATCH_DATE_PATTERN = re.compile(r"_\d{2}-(?P<month>\d{2})-\d{4}(?:_\d+)?$")


def get_month_from_csv(pair: FilePair) -> str:
    """
    Returns the month folder of a pair from the CSV modification date.
    """
    modification_date = datetime.fromtimestamp(pair.csv.stat().st_mtime)

    return MONTHS[modification_date.month]


def get_month_from_visa_batch(pair: FilePair) -> str:
    """
    Returns the month folder of a VISA pair from the batch date in its
    filename (e.g. "1_13-11-2026.pdf" -> "noviembre"). Falls back to the
    CSV modification date when the filename has no valid batch date.
    """
    match = VISA_BATCH_DATE_PATTERN.search(pair.pdf.stem)

    if match:
        month = int(match.group("month"))

        if month in MONTHS:
            return MONTHS[month]

    logger.warning(
        "VISA file without a valid batch date, using CSV date instead: %s",
        pair.pdf.name,
    )

    return get_month_from_csv(pair)


def export_folder(
    source_folder: Path,
    output_folder: Path,
    get_month: Callable[[FilePair], str],
) -> None:
    """
    Moves the PDF/CSV pairs of a Kodak output folder to the monthly
    folders of the output folder, adding a consecutive numeric prefix
    per month.
    """
    files = scan_files(source_folder)

    if not files:
        logger.info("No files found to process in %s", source_folder)
        return

    pairs = match_files(files)

    if not pairs:
        logger.info("No PDF/CSV pairs found to process in %s", source_folder)
        return

    pairs_by_month: dict[str, list[FilePair]] = {}

    for pair in pairs:
        pairs_by_month.setdefault(get_month(pair), []).append(pair)

    # Process each month independently.
    for month, month_pairs in pairs_by_month.items():

        month_folder = output_folder / month

        # Sort by CSV modification date/time, then by name for equal dates.
        month_pairs.sort(key=lambda pair: (pair.csv.stat().st_mtime, pair.pdf.name))

        # Get the last number used in this month.
        last_number = get_last_number(month_folder)

        logger.info(
            "Processing %d pairs for %s. Starting number: %04d",
            len(month_pairs),
            month_folder,
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


def run_export() -> None:
    """
    Executes the complete export process for incoming invoices and,
    when configured, for VISA invoices.
    """
    logger.info("Starting export service")

    settings = load_settings()

    # Incoming invoices: month from the CSV modification date.
    export_folder(
        settings.kodak_output_folder,
        settings.sftp_output_folder,
        get_month_from_csv,
    )

    # VISA invoices: month from the batch date in the filename.
    visa_output_folder = settings.visa_sftp_output_folder
    visa_source_folder = settings.visa_kodak_output_folder

    if visa_output_folder is None:
        logger.info("VISA_SFTP_OUTPUT_FOLDER is not configured, skipping VISA export")
    elif not visa_source_folder.is_dir():
        logger.error("VISA Kodak output folder does not exist: %s", visa_source_folder)
    else:
        export_folder(
            visa_source_folder,
            visa_output_folder,
            get_month_from_visa_batch,
        )

    logger.info("Export service finished successfully")


if __name__ == "__main__":
    run_export()
