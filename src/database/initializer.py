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

        create_lfbw = """
        CREATE TABLE IF NOT EXISTS lfbw (
            lifnr VARCHAR(10),
            bukrs VARCHAR(4),
            witht VARCHAR(2),
            wt_withcd VARCHAR(2),
            wt_subjct VARCHAR(2),
            wt_exrt NUMERIC(5,0),
            wt_exdf VARCHAR(8),
            wt_exdt VARCHAR(8),
            wt_wtexm VARCHAR(15),
            wt_exrs VARCHAR(2),
            wt_wtstcd VARCHAR(16),
            wt_withtr VARCHAR(2)
        );
        """

        create_proj = """
        CREATE TABLE IF NOT EXISTS proj (
            pspid VARCHAR(24),
            post1 VARCHAR(40),
            vbukr VARCHAR(4),
            waers VARCHAR(5),
            plfaz DATE,
            plsez DATE,
            profl VARCHAR(7)
        );
        """

        with self.database.engine.begin() as connection:
            connection.execute(text(create_kna1))
            connection.execute(text(create_anla))
            connection.execute(text(create_knb1))
            connection.execute(text(create_lfa1))
            connection.execute(text(create_lfb1))
            connection.execute(text(create_lfbw))
            connection.execute(text(create_proj))

        LOGGER.info("Database tables initialized successfully")
