from sqlalchemy import text

from database.connection import Database
from logger.logger import Logger

LOGGER = Logger.get_logger(__name__)


class DatabaseInitializer:
    """
    Responsible for initializing the database structure.

    Creates required tables if they do not already exist.
    """

    def __init__(self, database: Database):
        self.database = database

    def create_tables(self) -> None:
        """
        Creates application database tables.

        The method ensures that required tables exist before
        starting the data import process.
        """

        create_kna1 = """
        CREATE TABLE IF NOT EXISTS kna1 (

            kunnr VARCHAR(10),
            land1 VARCHAR(3),
            name1 VARCHAR(35),
            ort01 VARCHAR(35),
            pstlz VARCHAR(10),
            regio VARCHAR(3),
            aufsd VARCHAR(2),
            sortl VARCHAR(10),
            stras VARCHAR(35),
            telf1 VARCHAR(16),
            name2 VARCHAR(35),
            anred VARCHAR(15),
            erdat DATE,
            ernam VARCHAR(12),
            ktokd VARCHAR(4),
            faksd VARCHAR(2),
            spras VARCHAR(2),
            stcd1 VARCHAR(16),
            kokrs VARCHAR(4),
            stceg VARCHAR(20),
            stcd5 VARCHAR(16)

        );
        """

        create_anla = """
        CREATE TABLE IF NOT EXISTS anla (
            bukrs VARCHAR(4),
            anln1 VARCHAR(12),
            anln2 VARCHAR(4),
            anlkl VARCHAR(8),
            txt50 VARCHAR(50),
            erdat DATE
        );
        """

        create_knb1 = """
        CREATE TABLE IF NOT EXISTS knb1 (
            kunnr VARCHAR(10),
            bukrs VARCHAR(4),
            akont VARCHAR(10),
            zwels VARCHAR(10),
            zterm VARCHAR(4),
            ernam VARCHAR(12),
            sperr VARCHAR(1),
            loevm VARCHAR(1),
            erdat DATE
        );
        """

        create_lfa1 = """
        CREATE TABLE IF NOT EXISTS lfa1 (
            lifnr VARCHAR(10),
            land1 VARCHAR(3),
            name1 VARCHAR(35),
            ort01 VARCHAR(35),
            pstlz VARCHAR(10),
            regio VARCHAR(3),
            stras VARCHAR(35),
            erdat DATE,
            ernam VARCHAR(12),
            ktokk VARCHAR(4),
            spras VARCHAR(3),
            stcd1 VARCHAR(16),
            stceg VARCHAR(20)
        );
        """

        create_lfb1 = """
        CREATE TABLE IF NOT EXISTS lfb1 (
            lifnr VARCHAR(10),
            bukrs VARCHAR(4),
            pernr VARCHAR(8),
            erdat DATE,
            ernam VARCHAR(12),
            sperr VARCHAR(1),
            loevm VARCHAR(1),
            zuawa VARCHAR(3),
            akont VARCHAR(10),
            zwels VARCHAR(10),
            zahls VARCHAR(1),
            zterm VARCHAR(4),
            qland VARCHAR(3),
            qsskz VARCHAR(3)
        );
        """

        with self.database.engine.begin() as connection:
            connection.execute(text(create_kna1))
            connection.execute(text(create_anla))
            connection.execute(text(create_knb1))
            connection.execute(text(create_lfa1))
            connection.execute(text(create_lfb1))

        LOGGER.info("Database tables initialized successfully")
