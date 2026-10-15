import csv
import json
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
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

            if field == "pep_amounts":
                row[field] = self._serialize(
                    [self._format_money(amount) for amount in value]
                )
            elif field in {"subtotal", "taxes", "total"}:
                row[field] = self._format_money(value)
            else:
                row[field] = self._serialize(value)

            field_locations = self._normalize_locations(
                field,
                locations.get(field, []),
            )
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

    @staticmethod
    def _flatten_locations(value: Any) -> list[str]:
        """Flatten nested location lists into a single list."""
        if value is None or value == "":
            return []

        if isinstance(value, (list, tuple)):
            result = []
            for item in value:
                result.extend(InvoiceCSVExporter._flatten_locations(item))
            return result

        return [str(value)]

    @classmethod
    def _normalize_locations(cls, field: str, value: Any) -> Any:
        """Normalize locations while preserving empty positions."""
        list_fields = {
            "address",
            "descriptions",
            "quantities",
            "unit_prices",
            "amounts",
            "peps",
            "pep_amounts",
        }

        if field in list_fields:
            if value is None:
                return []
            if isinstance(value, (list, tuple)):
                return [str(item) if item is not None else "" for item in value]
            return [str(value)]

        locations = cls._flatten_locations(value)

        if len(locations) == 1:
            return locations[0]

        if not locations:
            return ""

        return locations

    @staticmethod
    def _format_money(value: Any) -> str:
        """Format monetary values to two decimal places."""
        if value is None or value == "":
            return ""

        try:
            amount = Decimal(str(value))
            return str(
                amount.quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP,
                )
            )
        except (InvalidOperation, ValueError):
            return str(value)
