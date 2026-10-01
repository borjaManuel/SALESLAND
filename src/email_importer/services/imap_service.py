import email
import imaplib
from email.message import Message

from config.settings import load_settings
from logger.logger import Logger
from processor.attachment_processor import AttachmentProcessor

logger = Logger.get_logger(__name__)


class ImapService:
    """
    Handles IMAP communication and email processing.
    """

    def __init__(self):
        self.settings = load_settings()

        self.mail = None

        self.attachment_processor = AttachmentProcessor(self.settings.pdf_output_folder)

    def connect(self) -> None:
        """
        Connects and authenticates against the IMAP server.
        """
        logger.info(
            "Connecting to IMAP server %s:%s",
            self.settings.imap_server,
            self.settings.imap_port,
        )

        self.mail = imaplib.IMAP4_SSL(
            self.settings.imap_server,
            self.settings.imap_port,
        )

        self.mail.login(
            self.settings.imap_user,
            self.settings.imap_password,
        )

        status, _ = self.mail.select(self.settings.imap_folder)

        if status != "OK":
            logger.error(
                f"Unable to access IMAP folder " f"'{self.settings.imap_folder}'."
            )

        logger.info(
            "Connected to IMAP folder '%s'",
            self.settings.imap_folder,
        )

    def disconnect(self) -> None:
        """
        Closes the IMAP connection.
        """
        if self.mail is None:
            return

        try:
            self.mail.logout()
        except Exception:
            logger.exception("Error while closing IMAP connection")

        self.mail = None

    def get_unread_messages(self) -> list[bytes]:
        """
        Retrieves the identifiers of unread emails.

        Returns:
            list[bytes]: IMAP message identifiers.
        """
        status, data = self.mail.search(
            None,
            "UNSEEN",
        )

        if status != "OK":
            logger.error("Unable to search unread emails.")

        message_ids = data[0].split()

        if not message_ids:
            logger.info("No unread emails found.")
            return []

        logger.info(
            "Found %d unread email(s)",
            len(message_ids),
        )

        return message_ids

    def process_message(self, message_id: bytes) -> None:
        """
        Downloads and processes PDF attachments from an email.

        The email is marked as read only after successful processing.

        Args:
            message_id: IMAP message identifier.
        """
        status, data = self.mail.fetch(
            message_id,
            "(RFC822)",
        )

        if status != "OK":
            raise RuntimeError(f"Unable to retrieve email {message_id!r}.")

        raw_email = data[0][1]

        message = email.message_from_bytes(raw_email)

        sender = message.get("From", "Unknown sender")
        subject = message.get("Subject", "No subject")

        logger.info(
            "Processing email %s | From: %s | Subject: %s",
            message_id.decode(),
            sender,
            subject,
        )

        pdf_count = 0

        for part in message.walk():

            if part.get_content_disposition() != "attachment":
                continue

            filename = part.get_filename()

            if not filename:
                continue

            if not filename.lower().endswith(".pdf"):
                continue

            content = part.get_payload(decode=True)

            if content is None:
                raise RuntimeError(f"Unable to read attachment '{filename}'.")

            self.attachment_processor.process(
                filename,
                content,
            )

            pdf_count += 1

            logger.info(
                "PDF attachment processed: %s | " "From: %s | Subject: %s",
                filename,
                sender,
                subject,
            )

        logger.info(
            "Email %s processed successfully | "
            "From: %s | Subject: %s | PDF attachments: %d",
            message_id.decode(),
            sender,
            subject,
            pdf_count,
        )

        self.mail.store(
            message_id,
            "+FLAGS",
            "\\Seen",
        )

        logger.info(
            "Email %s marked as read | " "From: %s | Subject: %s",
            message_id.decode(),
            sender,
            subject,
        )
