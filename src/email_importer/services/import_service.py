from logger.logger import Logger
from services.imap_service import ImapService

logger = Logger.get_logger(__name__)


class ImportService:
    """
    Orchestrates the email import process.
    """

    def run(self) -> None:
        """
        Processes all unread emails.
        """
        imap_service = ImapService()
        logger.info("############## Starting email import process ##############")

        try:
            imap_service.connect()

            message_ids = imap_service.get_unread_messages()

            for message_id in message_ids:
                try:
                    imap_service.process_message(message_id)

                except Exception:
                    logger.exception(
                        "Error processing email %s. " "The email will remain unread.",
                        message_id.decode(),
                    )

        finally:
            imap_service.disconnect()
