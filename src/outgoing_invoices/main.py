from config.settings import load_settings
from services.invoice_folder_wacher import start_folder_monitor


def main() -> None:
    settings = load_settings()
    start_folder_monitor(settings)


if __name__ == "__main__":
    main()
