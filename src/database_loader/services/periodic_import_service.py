import shutil
from datetime import datetime
from pathlib import Path

from config.settings import load_settings
from database.connection import Database
from excel.reader import ExcelReader
from loaders.contrapartida_clientes_loader import ContrapartidaClientesLoader
from loaders.contrapartida_proveedores_loader import ContrapartidaProveedoresLoader
from loaders.indicador_impuesto_loader import IndicadorImpuestoLoader
from loaders.indicadores_iva_loader import IndicadorIvaLoader
from logger.logger import Logger

LOGGER = Logger.get_logger(__name__)


class PeriodicImportService:

    def run(self):
        settings = load_settings()
        database = Database(settings)

        try:
            database.test_connection()

            LOGGER.info("Database connection successful")

            reader = ExcelReader()

            loaders = [
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
                {
                    "file": "INDICADOR_IVA.xlsx",
                    "loader": IndicadorIvaLoader,
                },
            ]

            for item in loaders:

                file_path = settings.periodic_data_dir / item["file"]

                if not file_path.exists():
                    LOGGER.warning(
                        "Excel file does not exist, skipping import: %s",
                        file_path,
                    )
                    continue

                LOGGER.info(
                    "Starting periodic import: %s",
                    file_path.name,
                )

                dataframe = reader.read(file_path)

                loader = item["loader"](database)

                loader.load(dataframe)

                self._move_to_history(
                    file_path,
                    settings.periodic_data_dir,
                )

                LOGGER.info(
                    "Periodic import completed: %s",
                    file_path.name,
                )

        finally:
            database.dispose()

    def _move_to_history(
        self,
        file_path: Path,
        periodic_data_dir: Path,
    ) -> None:
        """
        Moves a successfully processed file to the history folder
        and adds the processing timestamp to its filename.
        """

        history_folder = periodic_data_dir / "history"
        history_folder.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        history_file = (
            history_folder / f"{file_path.stem}_{timestamp}{file_path.suffix}"
        )

        shutil.move(file_path, history_file)

        LOGGER.info(
            "File moved to history: %s",
            history_file,
        )
