import imaplib

from config.settings import load_settings
from logger.logger import Logger

logger = Logger.get_logger(__name__)


def run() -> None:
    """
    Runs the IMAP connectivity and mailbox access checks.

    Raises:
        RuntimeError: If the IMAP server or mailbox cannot be accessed.
    """
    settings = load_settings()

    _check_imap_server(settings)
    _check_imap_mailbox(settings)


def _check_imap_server(settings) -> None:
    """
    Checks connectivity to the configured IMAP server.

    Args:
        settings: Application configuration.

    Raises:
        RuntimeError: If the IMAP server cannot be reached.
    """
    try:
        logger.info(
            "Connecting to IMAP server %s:%s",
            settings.imap_server,
            settings.imap_port,
        )

        mail = imaplib.IMAP4_SSL(
            settings.imap_server,
            settings.imap_port,
        )

        mail.logout()

        logger.info("IMAP server connection successful")

    except Exception as error:
        logger.error(
            "Unable to connect to IMAP server: %s",
            error,
        )

        raise RuntimeError("Unable to connect to the IMAP server.") from error


def _check_imap_mailbox(settings) -> None:
    """
    Checks authentication and access to the configured mailbox.

    Args:
        settings: Application configuration.

    Raises:
        RuntimeError: If the mailbox cannot be accessed.
    """
    mail = None

    try:
        logger.info(
            "Authenticating mailbox %s",
            settings.imap_user,
        )

        mail = imaplib.IMAP4_SSL(
            settings.imap_server,
            settings.imap_port,
        )

        mail.login(
            settings.imap_user,
            settings.imap_password,
        )

        status, _ = mail.select(settings.imap_folder)

        if status != "OK":
            raise RuntimeError(
                f"Unable to access IMAP folder " f"'{settings.imap_folder}'."
            )

        logger.info(
            "Mailbox folder '%s' is accessible",
            settings.imap_folder,
        )

    except imaplib.IMAP4.error as error:
        logger.error(
            "Unable to authenticate or access IMAP mailbox: %s",
            error,
        )

        raise RuntimeError(
            "Unable to authenticate or access the IMAP mailbox."
        ) from error

    finally:
        if mail is not None:
            try:
                mail.logout()
            except Exception:
                pass
