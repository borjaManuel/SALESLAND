import logging
from logging.handlers import RotatingFileHandler

from config.paths import LOG_DIR


class Logger:
    """
    Centralized export service logger.

    - Automatic log rotation.
    - Maximum file size: 5 MB.
    - Retains up to 5 backup log files.
    - Simultaneous output to both console and log file.
    """

    _logger: logging.Logger | None = None

    @classmethod
    def get_logger(cls, name: str = "export_service") -> logging.Logger:

        if cls._logger is not None:
            return cls._logger.getChild(name)

        LOG_DIR.mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger("export_service")
        logger.setLevel(logging.INFO)
        logger.propagate = False

        if not logger.handlers:

            formatter = logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

            file_handler = RotatingFileHandler(
                filename=LOG_DIR / "import_service.log",
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
