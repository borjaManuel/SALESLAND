import argparse

from checks.check_config import run as run_check


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--check", action="store_true", help="Comprueba la configuración"
    )

    args = parser.parse_args()

    if args.check:
        run_check()
        return


if __name__ == "__main__":
    main()
