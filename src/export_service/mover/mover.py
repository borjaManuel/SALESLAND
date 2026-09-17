import shutil

from logger.logger import Logger
from matcher.matcher import FilePair
from renamer.renamer import RenamedPair

logger = Logger.get_logger(__name__)


def move_pair(pair: FilePair, renamed_pair: RenamedPair) -> None:
    """
    Moves a matched PDF/CSV pair to their destination paths.

    Args:
        pair: Original PDF/CSV pair.
        renamed_pair: Destination PDF/CSV pair.

    Raises:
        OSError: If any file cannot be moved.
    """
    try:
        renamed_pair.pdf.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(pair.pdf, renamed_pair.pdf)
        shutil.move(pair.csv, renamed_pair.csv)

        logger.info(
            "Moved pair: %s / %s -> %s / %s",
            pair.pdf.name,
            pair.csv.name,
            renamed_pair.pdf.name,
            renamed_pair.csv.name,
        )

    except OSError:
        logger.exception(
            "Error moving pair: %s / %s",
            pair.pdf.name,
            pair.csv.name,
        )
        raise
