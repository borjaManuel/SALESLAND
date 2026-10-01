from pathlib import Path


class AttachmentProcessor:
    """
    Processes email attachments and stores PDF files.
    """

    def __init__(self, output_folder: Path):
        self.output_folder = output_folder

    def process(self, filename: str, content: bytes) -> Path:
        """
        Saves an attachment to the configured output folder.

        Args:
            filename: Attachment filename.
            content: Attachment binary content.

        Returns:
            Path: Path of the saved file.

        Raises:
            OSError: If the file cannot be saved.
        """
        self.output_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path = self.output_folder / filename

        output_path.write_bytes(content)

        return output_path
