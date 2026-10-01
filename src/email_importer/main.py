import argparse

from checks.imap_check import run as run_check
from services.import_service import ImportService


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--check",
        action="store_true",
        help="Checks the IMAP server and mailbox configuration",
    )

    args = parser.parse_args()

    if args.check:
        run_check()
        return

    import_service = ImportService()
    import_service.run()


if __name__ == "__main__":
    main()
