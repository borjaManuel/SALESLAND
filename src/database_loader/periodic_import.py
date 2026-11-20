from services.periodic_import_service import PeriodicImportService

if __name__ == "__main__":
    # VISA batches are imported by visa_import.py with their own schedule.
    PeriodicImportService().run(include_visa=False)
