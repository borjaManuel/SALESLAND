from config.settings import load_settings
from database.connection import Database
from logger.logger import Logger

LOGGER = Logger.get_logger(__name__)


def run():
    """
    Executes the application configuration checks.

    This includes:
        - Loading and validating the application settings.
        - Verifying the PostgreSQL database connection.

    Raises:
        RuntimeError: If the application settings are invalid.
        SQLAlchemyError: If the database connection cannot be established.
    """
    LOGGER.info("Comprobando configuración...")

    settings = load_settings()

    LOGGER.info("✓ Configuración cargada")

    database = Database(settings)

    database.test_connection()

    LOGGER.info("✓ PostgreSQL conectado")

    database.dispose()

    LOGGER.info("Todo correcto.")


if __name__ == "__main__":
    run()
