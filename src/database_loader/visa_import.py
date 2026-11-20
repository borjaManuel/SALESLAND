from services.periodic_import_service import PeriodicImportService

if __name__ == "__main__":
    # Imports only the VISA batches of VISA_DATA_DIR, so that it can be
    # scheduled more frequently than the periodic Excel files.
    PeriodicImportService().run(include_periodic=False)
