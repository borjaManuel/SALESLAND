from config.paths import DATA_DIR
from config.settings import load_settings
from database.connection import Database
from database.initializer import DatabaseInitializer
from excel.reader import ExcelReader
from loaders.anla_loader import AnlaLoader
from loaders.contrapartida_clientes_loader import ContrapartidaClientesLoader
from loaders.contrapartida_proveedores_loader import ContrapartidaProveedoresLoader
from loaders.indicador_impuesto_loader import IndicadorImpuestoLoader
from loaders.kna1_loader import Kna1Loader
from loaders.knb1_loader import Knb1Loader
from loaders.lfa1_loader import Lfa1Loader
from loaders.lfb1_loader import Lfb1Loader
from loaders.lfbw_loader import LfbwLoader
from loaders.proj_loader import ProjLoader
from loaders.ska1_loader import Ska1Loader
from loaders.t007a_loader import T007aLoader
from loaders.t059z_loader import T059zLoader
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

            loaders = [
                {"file": "KNA1.xlsx", "loader": Kna1Loader},
                {"file": "ANLA.xlsx", "loader": AnlaLoader},
                {"file": "KNB1.xlsx", "loader": Knb1Loader},
                {"file": "LFA1.xlsx", "loader": Lfa1Loader},
                {"file": "LFB1.xlsx", "loader": Lfb1Loader},
                {"file": "LFBW.xlsx", "loader": LfbwLoader},
                {"file": "PROJ.xlsx", "loader": ProjLoader},
                {"file": "SKA1.xlsx", "loader": Ska1Loader},
                {"file": "T007A.xlsx", "loader": T007aLoader},
                {"file": "T059Z.xlsx", "loader": T059zLoader},
                {
                    "file": "CONTRAPARTIDA_CLIENTES.xlsx",
                    "loader": ContrapartidaClientesLoader,
                },
                {
                    "file": "CONTRAPARTIDA_PROVEEDORES.xlsx",
                    "loader": ContrapartidaProveedoresLoader,
                },
                {
                    "file": "INDICADOR_IMPUESTO.xlsx",
                    "loader": IndicadorImpuestoLoader,
                },
            ]

            for item in loaders:

                LOGGER.info("Starting import: %s", item["file"])

                dataframe = reader.read(DATA_DIR / item["file"])

                loader = item["loader"](database)

                loader.load(dataframe)

                LOGGER.info("Import completed: %s", item["file"])

        finally:

            database.dispose()
