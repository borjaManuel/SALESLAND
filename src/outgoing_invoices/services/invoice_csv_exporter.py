import csv
import json
from pathlib import Path
from typing import Any


class InvoiceCSVExporter:
    """Export extracted outgoing invoice data to a horizontal CSV file."""

    def __init__(self, output_folder: str | Path) -> None:
        self.output_folder = Path(output_folder)

    def export(
        self,
        invoice: dict[str, Any],
        filename: str = "outgoing_invoices.csv",
    ) -> Path:
        """Export one invoice as a horizontal CSV row."""
        self.output_folder.mkdir(parents=True, exist_ok=True)
        output_path = self.output_folder / filename

        locations = invoice.get("locations", {})
        row: dict[str, str] = {}

        for field, value in invoice.items():
            if field == "locations":
                continue

            row[field] = self._serialize(value)

            field_locations = locations.get(field, [])
            row[f"{field}_locations"] = self._serialize(field_locations)

        with output_path.open(
            mode="w",
            newline="",
            encoding="utf-8-sig",
        ) as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=list(row.keys()),
                delimiter=";",
                quoting=csv.QUOTE_MINIMAL,
            )
            writer.writeheader()
            writer.writerow(row)

        return output_path

    @staticmethod
    def _serialize(value: Any) -> str:
        """Serialize lists as JSON arrays and scalar values as strings."""
        if value is None:
            return ""

        if isinstance(value, (list, tuple)):
            return json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
                default=str,
            )

        if isinstance(value, bool):
            return str(value).lower()

        return str(value)
