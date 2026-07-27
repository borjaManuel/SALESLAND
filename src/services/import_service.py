from config.paths import DATA_DIR
from config.settings import load_settings
from database.connection import Database
from database.initializer import DatabaseInitializer
from excel.reader import ExcelReader
from loaders.kna1_loader import Kna1Loader
from logger.logger import Logger

LOGGER = Logger.get_logger(__name__)


class ImportService:
    """
    Service responsible for orchestrating the data import process.

    This service handles the application workflow, including configuration
    loading, database connection validation, and execution of the required
    data loaders.
    """

    def run(self):
        """
        Executes the data import workflow.

        The process includes:
            - Loading and validating application settings.
            - Establishing a connection with the PostgreSQL database.
            - Validating database connectivity.
            - Executing the KNA1 data loader.
            - Releasing database resources after execution.

        Raises:
            RuntimeError: If the application configuration is invalid.
            SQLAlchemyError: If the database connection or operation fails.
        """

        settings = load_settings()

        database = Database(settings)

        try:
            database.test_connection()

            LOGGER.info("Database connection successful")

            initializer = DatabaseInitializer(database)
            initializer.create_tables()

            reader = ExcelReader()

            dataframe = reader.read(DATA_DIR / "KNA1.xlsx")

            kna1_loader = Kna1Loader(database)

            kna1_loader.load(dataframe)

        finally:
            database.dispose()
