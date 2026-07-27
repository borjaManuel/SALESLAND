import argparse

from checks.check_config import run as run_check
from services.import_service import ImportService


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--check", action="store_true", help="Comprueba la configuración"
    )

    args = parser.parse_args()

    if args.check:
        run_check()
        return

    import_service = ImportService()
    import_service.run()


if __name__ == "__main__":
    main()
