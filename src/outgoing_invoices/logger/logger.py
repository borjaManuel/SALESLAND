"""Centralized logger for the invoice Excel loader."""

import logging
from logging.handlers import RotatingFileHandler

from config.paths import LOG_DIR


class InvoiceExcelLogger:
    """Configure logging for the invoice Excel loader.

    Logs are written to both the console and a rotating log file.

    - Maximum log file size: 5 MB.
    - Retains up to 5 backup files.
    - UTF-8 encoding.
    """

    _logger: logging.Logger | None = None

    @classmethod
    def get_logger(
        cls,
        name: str = "invoice_excel_loader",
    ) -> logging.Logger:
        """Return a named logger for the invoice Excel loader."""
        if cls._logger is not None:
            return cls._logger.getChild(name)

        LOG_DIR.mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger("invoice_excel")
        logger.setLevel(logging.INFO)
        logger.propagate = False

        if not logger.handlers:
            formatter = logging.Formatter(
                fmt=(
                    "%(asctime)s | %(levelname)-8s | %(name)s | "
                    "%(filename)s:%(lineno)d | %(message)s"
                ),
                datefmt="%Y-%m-%d %H:%M:%S",
            )

            file_handler = RotatingFileHandler(
                filename=LOG_DIR / "invoice_excel.log",
                maxBytes=5 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)

            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)

            logger.addHandler(file_handler)
            logger.addHandler(console_handler)

        cls._logger = logger
        return logger.getChild(name)
