import shutil
import time
from pathlib import Path

from config.settings import Settings
from logger.logger import InvoiceExcelLogger
from services.invoice_csv_exporter import InvoiceCSVExporter
from services.invoice_excel_loader import extract_invoice
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = InvoiceExcelLogger.get_logger()


class InvoiceFolderHandler(FileSystemEventHandler):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.processed_folder = settings.excel_input_folder / "processed"
        self.error_folder = settings.excel_input_folder / "error"
        self.exporter = InvoiceCSVExporter(settings.csv_output_folder)
        self.processing: set[Path] = set()

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._process_if_excel(Path(event.src_path))

    def on_moved(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._process_if_excel(Path(event.dest_path))

    def _process_if_excel(self, excel_path: Path) -> None:
        if excel_path.suffix.lower() != ".xlsx":
            return

        if excel_path.parent.resolve() != self.settings.excel_input_folder.resolve():
            return

        if excel_path.name.startswith("~$"):
            return

        if excel_path in self.processing:
            return

        self.processing.add(excel_path)

        try:
            if not self._wait_until_ready(excel_path):
                raise TimeoutError(
                    f"El archivo no está disponible o no termina de copiarse: {excel_path}"
                )

            logger.info("Procesando Excel: %s", excel_path)

            invoice = extract_invoice(str(excel_path))

            csv_path = self.exporter.export(
                invoice,
                filename=f"{excel_path.stem}.csv",
            )

            self.processed_folder.mkdir(parents=True, exist_ok=True)
            destination = self.processed_folder / excel_path.name

            if destination.exists():
                raise FileExistsError(
                    f"Ya existe un archivo procesado con ese nombre: {destination}"
                )

            shutil.move(str(excel_path), str(destination))

            logger.info("CSV generado: %s", csv_path)
            logger.info("Excel movido a: %s", destination)

        except Exception:
            logger.exception("Error procesando el Excel: %s", excel_path)

            try:
                if excel_path.exists():
                    self.error_folder.mkdir(parents=True, exist_ok=True)
                    destination = self.error_folder / excel_path.name

                    if destination.exists():
                        logger.error(
                            "No se mueve el Excel porque ya existe en error: %s",
                            destination,
                        )
                    else:
                        shutil.move(str(excel_path), str(destination))
                        logger.info("Excel movido a error: %s", destination)

            except Exception:
                logger.exception(
                    "No se pudo mover el Excel a la carpeta de error: %s",
                    excel_path,
                )

        finally:
            self.processing.discard(excel_path)

    @staticmethod
    def _wait_until_ready(
        path: Path,
        attempts: int = 30,
        interval: float = 1.0,
    ) -> bool:
        previous_size = -1
        stable_checks = 0

        for _ in range(attempts):
            try:
                current_size = path.stat().st_size

                if current_size > 0 and current_size == previous_size:
                    stable_checks += 1
                    if stable_checks >= 2:
                        return True
                else:
                    stable_checks = 0

                previous_size = current_size

            except (FileNotFoundError, PermissionError):
                stable_checks = 0

            time.sleep(interval)

        return False


def start_folder_monitor(settings: Settings) -> None:
    input_folder = settings.excel_input_folder
    input_folder.mkdir(parents=True, exist_ok=True)
    settings.csv_output_folder.mkdir(parents=True, exist_ok=True)

    handler = InvoiceFolderHandler(settings)

    # Process Excel files already present when the service starts.
    for excel_path in input_folder.glob("*.xlsx"):
        handler._process_if_excel(excel_path)

    observer = Observer()
    observer.schedule(handler, str(input_folder), recursive=False)
    observer.start()

    logger.info("Monitorizando carpeta: %s", input_folder)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Deteniendo monitorización de facturas.")
        observer.stop()
    finally:
        observer.join()
