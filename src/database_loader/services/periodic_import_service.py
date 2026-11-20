import re
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
from loaders.emitidas_iban_vto_factoring_loader import EmitidasIbanVTOFactoringLoader
from loaders.indicador_impuesto_loader import IndicadorImpuestoLoader
from loaders.indicadores_iva_loader import IndicadorIvaLoader
from loaders.visa_loader import VisaLoader
from logger.logger import Logger

LOGGER = Logger.get_logger(__name__)

VISA_EXCEL_NAME = "REFERENCIA FRAS.VISA.xlsx"

# Batch folders are named after their date, with an optional sequence
# number when there is more than one batch on the same day.
VISA_BATCH_NAME_PATTERN = re.compile(r"(?P<fecha>\d{2}-\d{2}-\d{4})(?:_\d+)?")


class PeriodicImportService:

    def run(self, include_periodic: bool = True, include_visa: bool = True):
        """
        Imports the available periodic Excel files and/or VISA batches.

        periodic_import.py imports only the periodic files and
        visa_import.py only the VISA batches, so that each one can be
        scheduled with its own frequency without processing the same
        files twice.
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
                {
                    "file": "EMITIDA_IBAN_VTO_FACTORING.xlsx",
                    "loader": EmitidasIbanVTOFactoringLoader,
                },
            ]

            available_files = []

            if include_periodic:
                available_files.extend(
                    self._get_available_files(
                        loaders,
                        settings.periodic_data_dir,
                    )
                )

            if include_visa:
                try:
                    available_files.extend(
                        self._get_visa_files(
                            settings.visa_data_dir,
                            settings.visa_output_dir,
                            settings.visa_history_dir,
                            settings.visa_minimum_age,
                        )
                    )
                except OSError:
                    LOGGER.exception("Error reading VISA batches, skipping them")

            if not available_files:
                LOGGER.info("No Excel files available for import")
                return

            failed = []

            for item in available_files:

                file_path = item["file"]

                try:
                    self._process_item(item, reader, database)
                except Exception:
                    # A wrong file must not block the remaining files and
                    # VISA batches. It is kept in place to be fixed and
                    # retried on the next execution.
                    LOGGER.exception("Periodic import failed: %s", file_path)
                    failed.append(str(file_path))

            if failed:
                raise RuntimeError(
                    f"Periodic import failed for {len(failed)} file(s): "
                    + ", ".join(failed)
                )

        finally:
            database.dispose()

    def _process_item(self, item: dict, reader: ExcelReader, database: Database):
        """
        Loads one periodic Excel file or VISA batch and moves its files.
        """

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
            item["history_dir"],
        )

        if visa_moves is not None:
            self._move_visa_batch(
                file_path.parent,
                item["numero_lote"],
                item["output_dir"],
                visa_moves,
            )

        LOGGER.info("Periodic import completed: %s", file_path.name)

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
                    "history_dir": periodic_data_dir / "history",
                }
            )

        return available_files

    def _get_visa_files(
        self,
        visa_data_dir: Path | None,
        visa_output_dir: Path | None,
        visa_history_dir: Path,
        minimum_age: timedelta,
    ) -> list[dict]:
        """
        Returns the VISA batches available in the shared folder.

        Each batch is a folder named after its date (DD-MM-YYYY, or
        DD-MM-YYYY_N when there is more than one batch on the same day)
        containing the reference Excel and the invoice PDFs. A batch is
        only processed once none of its files has been modified during
        the last minimum_age, so batches still being copied are skipped.
        """

        available_files = []
        current_time = datetime.now()

        if visa_data_dir is None:
            LOGGER.info("VISA_DATA_DIR is not configured, skipping VISA batches")
            return available_files

        if not visa_data_dir.is_dir():
            LOGGER.error("VISA shared folder is not accessible: %s", visa_data_dir)
            return available_files

        for batch_dir in sorted(visa_data_dir.iterdir()):
            if not batch_dir.is_dir():
                continue

            file_path = batch_dir / VISA_EXCEL_NAME
            if not file_path.is_file():
                continue

            numero_lote = batch_dir.name
            if not self._is_valid_visa_batch_name(numero_lote):
                LOGGER.error(
                    "VISA batch folder name must be DD-MM-YYYY or DD-MM-YYYY_N, "
                    "skipping it: %s",
                    batch_dir,
                )
                continue

            if visa_output_dir is None:
                LOGGER.error(
                    "VISA_OUTPUT_DIR must be configured to process VISA batches, "
                    "skipping batch: %s",
                    batch_dir,
                )
                continue

            batch_files = [item for item in batch_dir.iterdir() if item.is_file()]
            last_modification = max(
                datetime.fromtimestamp(item.stat().st_mtime) for item in batch_files
            )
            if current_time - last_modification < minimum_age:
                LOGGER.info(
                    "VISA batch is too recent and will not be imported yet: %s",
                    batch_dir,
                )
                continue

            available_files.append(
                {
                    "file": file_path,
                    "loader": VisaLoader,
                    "numero_lote": numero_lote,
                    "history_dir": visa_history_dir / numero_lote,
                    "output_dir": visa_output_dir,
                }
            )

        return available_files

    @staticmethod
    def _is_valid_visa_batch_name(name: str) -> bool:
        match = VISA_BATCH_NAME_PATTERN.fullmatch(name)
        if match is None:
            return False

        try:
            datetime.strptime(match.group("fecha"), "%d-%m-%Y")
        except ValueError:
            return False

        return True

    def _move_to_history(self, file_path: Path, history_folder: Path) -> None:
        """
        Moves a successfully processed file to the history folder
        and adds the processing timestamp to its filename.
        """

        history_folder.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        history_file = (
            history_folder / f"{file_path.stem}_{timestamp}{file_path.suffix}"
        )

        shutil.move(file_path, history_file)

        LOGGER.info("File moved to history: %s", history_file)

    def _get_visa_batch_moves(
        self, excel_path: Path, numero_lote: str, visa_output_dir: Path
    ) -> list[tuple[Path, Path]]:
        """
        Returns the source and target paths of the VISA invoice PDFs to move
        to the local InfoInput folder, adding the batch name as a suffix to
        each filename (e.g. "1.pdf" -> "1_13-11-2026.pdf").
        Fails before any processing if the batch has no PDFs or a target
        file already exists.
        """

        batch_dir = excel_path.parent
        target_dir = visa_output_dir / numero_lote

        moves = [
            (
                file_path,
                target_dir / f"{file_path.stem}_{numero_lote}{file_path.suffix}",
            )
            for file_path in sorted(batch_dir.iterdir())
            if file_path.is_file() and file_path.suffix.lower() == ".pdf"
        ]

        if not moves:
            raise ValueError(f"VISA batch does not contain any PDF: {batch_dir}")

        existing = [target.name for _, target in moves if target.exists()]
        if existing:
            raise FileExistsError(
                f"VISA files already exist in {target_dir}: {', '.join(existing)}"
            )

        return moves

    def _move_visa_batch(
        self,
        batch_dir: Path,
        numero_lote: str,
        visa_output_dir: Path,
        moves: list[tuple[Path, Path]],
    ) -> None:
        """
        Moves the invoice PDFs of a processed VISA batch from the shared
        folder to the local InfoInput folder and removes the batch folder
        once it is empty.
        """

        target_dir = visa_output_dir / numero_lote
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
