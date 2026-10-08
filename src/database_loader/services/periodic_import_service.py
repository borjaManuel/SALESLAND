import shutil
from datetime import datetime, timedelta
from pathlib import Path

from config.settings import load_settings
from database.connection import Database
from database.initializer import DatabaseInitializer
from excel.reader import ExcelReader
from loaders.clase_facturas_emitidas_loader import ClaseFacturasEmitidasLoader
from loaders.contrapartida_clientes_loader import ContrapartidaClientesLoader
from loaders.contrapartida_proveedores_loader import ContrapartidaProveedoresLoader
from loaders.indicador_impuesto_loader import IndicadorImpuestoLoader
from loaders.indicadores_iva_loader import IndicadorIvaLoader
from loaders.visa_loader import VisaLoader
from logger.logger import Logger

LOGGER = Logger.get_logger(__name__)


class PeriodicImportService:

    def run(self):
        settings = load_settings()
        database = Database(settings)

        try:
            database.test_connection()

            LOGGER.info("Database connection successful")

            initializer = DatabaseInitializer(database)

            initializer.create_tables()

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
                {
                    "file": "CLASE_FACTURAS_EMITIDAS.xlsx",
                    "loader": ClaseFacturasEmitidasLoader,
                },
            ]

            available_files = self._get_available_files(
                loaders,
                settings.periodic_data_dir,
            )
            available_files.extend(
                self._get_visa_files(
                    settings.visa_data_dir,
                    settings.visa_output_dir,
                )
            )

            if not available_files:
                LOGGER.info("No Excel files available for periodic import")
                return

            for item in available_files:

                file_path = item["file"]

                LOGGER.info("Starting periodic import: %s", file_path.name)

                visa_moves = None
                if "output_dir" in item:
                    visa_moves = self._get_visa_batch_moves(
                        file_path,
                        item["numero_lote"],
                        item["output_dir"],
                    )

                dataframe = reader.read(file_path)

                loader = item["loader"](database)

                if "numero_lote" in item:
                    loader.load(dataframe, item["numero_lote"])
                else:
                    loader.load(dataframe)

                self._move_to_history(
                    file_path,
                    item["data_dir"],
                )

                if visa_moves is not None:
                    self._move_visa_batch(
                        file_path.parent,
                        item["numero_lote"],
                        item["output_dir"],
                        visa_moves,
                    )

                LOGGER.info("Periodic import completed: %s", file_path.name)

        finally:
            database.dispose()

    def _get_available_files(
        self, loaders: list[dict], periodic_data_dir: Path
    ) -> list[dict]:
        """
        Returns configured Excel files available in the existing periodic directory.
        """

        available_files = []
        minimum_age = timedelta(minutes=5)
        current_time = datetime.now()
        for item in loaders:
            file_path = periodic_data_dir / item["file"]

            if not file_path.is_file():
                continue

            file_age = current_time - datetime.fromtimestamp(file_path.stat().st_mtime)

            if file_age < minimum_age:
                LOGGER.info(
                    "Excel file is too recent and will not be imported: %s",
                    file_path.name,
                )
                continue

            available_files.append(
                {
                    "file": file_path,
                    "loader": item["loader"],
                    "data_dir": periodic_data_dir,
                }
            )

        return available_files

    def _get_visa_files(
        self, visa_data_dir: Path, visa_output_dir: Path | None
    ) -> list[dict]:
        available_files = []
        minimum_age = timedelta(minutes=5)
        current_time = datetime.now()

        if not visa_data_dir.is_dir():
            return available_files

        for batch_dir in visa_data_dir.iterdir():
            if not batch_dir.is_dir() or batch_dir.name == "history":
                continue

            file_path = batch_dir / "REFERENCIA FRAS.VISA.xlsx"
            if not file_path.is_file():
                continue

            try:
                numero_lote = int(batch_dir.name)
            except ValueError as error:
                raise ValueError(
                    f"VISA batch folder must be numeric: {batch_dir.name}"
                ) from error

            if numero_lote < 1:
                raise ValueError("VISA batch number must be positive")

            if visa_output_dir is None:
                raise RuntimeError(
                    "VISA_OUTPUT_DIR must be configured to process VISA batches"
                )

            file_age = current_time - datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_age < minimum_age:
                LOGGER.info(
                    "VISA Excel is too recent and will not be imported: %s",
                    file_path,
                )
                continue

            available_files.append(
                {
                    "file": file_path,
                    "loader": VisaLoader,
                    "numero_lote": numero_lote,
                    "data_dir": visa_data_dir,
                    "output_dir": visa_output_dir,
                }
            )

        return available_files

    def _move_to_history(self, file_path: Path, periodic_data_dir: Path) -> None:
        """
        Moves a successfully processed file to the history folder
        and adds the processing timestamp to its filename.
        """

        history_folder = periodic_data_dir / "history"
        if file_path.parent != periodic_data_dir:
            history_folder = history_folder / file_path.parent.name
        history_folder.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        history_file = (
            history_folder / f"{file_path.stem}_{timestamp}{file_path.suffix}"
        )

        shutil.move(file_path, history_file)

        LOGGER.info("File moved to history: %s", history_file)

    def _get_visa_batch_moves(
        self, excel_path: Path, numero_lote: int, visa_output_dir: Path
    ) -> list[tuple[Path, Path]]:
        """
        Returns the source and target paths of the VISA batch files to move,
        adding the "visa" and batch number suffixes to each filename.
        Fails before any processing if a target file already exists.
        """

        batch_dir = excel_path.parent
        target_dir = visa_output_dir / batch_dir.name

        moves = [
            (
                file_path,
                target_dir / f"{file_path.stem}_visa_{numero_lote}{file_path.suffix}",
            )
            for file_path in batch_dir.iterdir()
            if file_path.is_file() and file_path != excel_path
        ]

        existing = [target.name for _, target in moves if target.exists()]
        if existing:
            raise FileExistsError(
                f"VISA files already exist in {target_dir}: {', '.join(existing)}"
            )

        return moves

    def _move_visa_batch(
        self,
        batch_dir: Path,
        numero_lote: int,
        visa_output_dir: Path,
        moves: list[tuple[Path, Path]],
    ) -> None:
        """
        Moves the remaining files of a processed VISA batch to the output
        folder and removes the batch folder once it is empty.
        """

        target_dir = visa_output_dir / batch_dir.name
        target_dir.mkdir(parents=True, exist_ok=True)

        for file_path, target in moves:
            shutil.move(file_path, target)

        LOGGER.info(
            "VISA batch %s moved to %s. Files: %s",
            numero_lote,
            target_dir,
            len(moves),
        )

        if any(batch_dir.iterdir()):
            LOGGER.warning("VISA batch folder is not empty, keeping it: %s", batch_dir)
            return

        batch_dir.rmdir()
