from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from logger.logger import InvoiceExcelLogger
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

logger = InvoiceExcelLogger.get_logger()


@dataclass
class InvoiceData:
    """Represent invoice data and the Excel cells used to extract it."""

    client: str | None = None
    tax_id: str | None = None
    address: list[str] | None = None
    is_self_billing: bool = False
    invoice_number: str | None = None
    peps: list[str] = field(default_factory=list)
    pep_amounts: list[str] = field(default_factory=list)
    email: str | None = None

    descriptions: list[str] = field(default_factory=list)
    quantities: list[str] = field(default_factory=list)
    unit_prices: list[str] = field(default_factory=list)
    amounts: list[str] = field(default_factory=list)

    subtotal: str | None = None
    tax_rate: str | None = None
    taxes: str | None = None
    total: str | None = None

    locations: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Ensure that invoice line values and their locations are aligned."""
        lengths = {
            len(self.descriptions),
            len(self.quantities),
            len(self.unit_prices),
            len(self.amounts),
        }

        if len(lengths) != 1:
            raise ValueError("Invoice line arrays must have equal lengths.")

        for field_name in (
            "descriptions",
            "quantities",
            "unit_prices",
            "amounts",
        ):
            field_locations = self.locations.get(field_name, [])
            if len(field_locations) != len(self.descriptions):
                raise ValueError(
                    f"Locations for '{field_name}' must match the number of lines."
                )

        if len(self.peps) != len(self.pep_amounts):
            raise ValueError("PEP and PEP amount arrays must have equal lengths.")

        for field_name in ("peps", "pep_amounts"):
            field_locations = self.locations.get(field_name, [])
            if len(field_locations) != len(self.peps):
                raise ValueError(
                    f"Locations for '{field_name}' must match the number of PEPs."
                )

    def to_dict(self) -> dict[str, Any]:
        """Return extracted invoice data, including source cell references."""
        self.validate()

        return {
            "client": self.client,
            "tax_id": self.tax_id,
            "address": self.address,
            "is_self_billing": self.is_self_billing,
            "invoice_number": self.invoice_number,
            "peps": self.peps,
            "pep_amounts": self.pep_amounts,
            "email": self.email,
            "descriptions": self.descriptions,
            "quantities": self.quantities,
            "unit_prices": self.unit_prices,
            "amounts": self.amounts,
            "subtotal": self.subtotal,
            "tax_rate": self.tax_rate,
            "taxes": self.taxes,
            "total": self.total,
            "locations": self.locations,
        }


class InvoiceExcelLoader:
    """Extract invoice data and source cell locations from an Excel workbook."""

    TAX_ID_PATTERN = re.compile(
        r"\b(?:C\.?\s*I\.?\s*F\.?|N\.?\s*I\.?\s*F\.?)"
        r"\s*:?\s*([A-Z]\d{7}[A-Z0-9]|\d{8}[A-Z])\b",
        re.IGNORECASE,
    )

    INVOICE_NUMBER_PATTERN = re.compile(
        r"\b(?:N[ÚU]MERO\s+DE\s+FACTURA|N[ÚU]MERO\s+FACTURA|"
        r"FACTURA\s*(?:N[ÚU]M(?:ERO)?\.?|#)|"
        r"N[ÚU]M(?:ERO)?\.?\s*(?:DE\s+)?FACTURA)\b",
        re.IGNORECASE,
    )

    NUMBER_PATTERN = re.compile(
        r"^[+-]?(?:\d{1,3}(?:\.\d{3})+|\d+)(?:[,.]\d+)?%?\s*€?$"
    )

    DETAIL_STOP_PATTERN = re.compile(
        r"\b(?:SUBTOTAL|TIPO\s+IMPOSITIVO|IMPUESTOS?|REPARTO)\b",
        re.IGNORECASE,
    )

    IGNORED_DETAIL_PATTERN = re.compile(
        r"\b(?:FACTORING|EXENTO\s+IVA|REGLA\s+DE\s+NEGOCIO|" r"VENCIMIENTO|IBAN)\b",
        re.IGNORECASE,
    )

    EMAIL_PATTERN = re.compile(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        re.IGNORECASE,
    )

    def __init__(
        self,
        file_path: str | Path,
        sheet_name: str | None = None,
    ) -> None:
        """Initialize the loader with a workbook path and optional sheet name."""
        self.file_path = Path(file_path)
        self.sheet_name = sheet_name

    def load(self) -> InvoiceData:
        """Load the workbook and extract invoice values and their locations."""
        if not self.file_path.is_file():
            raise FileNotFoundError(f"Excel file not found: {self.file_path}")

        workbook = load_workbook(
            filename=self.file_path,
            read_only=True,
            data_only=True,
        )

        try:
            if (
                self.sheet_name is not None
                and self.sheet_name not in workbook.sheetnames
            ):
                raise ValueError(f"Worksheet not found: {self.sheet_name}")

            worksheet = (
                workbook[self.sheet_name] if self.sheet_name else workbook.active
            )

            rows = self._read_rows(worksheet)
            invoice = InvoiceData()

            invoice.is_self_billing = self._find_self_billing(
                rows,
                invoice,
            )

            self._extract_invoice_number(rows, invoice)
            self._extract_client(rows, invoice)
            self._extract_totals(rows, invoice)
            self._extract_lines(rows, invoice)
            self._extract_distribution(rows, invoice)
            self._extract_email(rows, invoice)

            invoice.validate()
            return invoice

        finally:
            workbook.close()

    @staticmethod
    def _normalize(value: Any) -> str:
        """Normalize whitespace without changing meaningful text."""
        if value is None:
            return ""

        return re.sub(
            r"\s+",
            " ",
            str(value).replace("\xa0", " "),
        ).strip()

    def _read_rows(
        self,
        worksheet: Worksheet,
    ) -> list[list[str]]:
        """Read cell values while preserving their original column positions."""
        return [
            [self._normalize(value) for value in row]
            for row in worksheet.iter_rows(values_only=True)
        ]

    @staticmethod
    def _get_cell_reference(
        row_index: int,
        column_index: int,
    ) -> str:
        """Convert zero-based indexes to an Excel cell reference."""
        return f"{get_column_letter(column_index + 1)}{row_index + 1}"

    def _find_self_billing(
        self,
        rows: list[list[str]],
        invoice: InvoiceData,
    ) -> bool:
        """Detect self-billing from the checkbox next to its label."""
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                if not re.search(r"\bAUTOFACTURA\b", value, re.IGNORECASE):
                    continue

                checkbox_column = column_index + 2

                if checkbox_column >= len(row):
                    continue

                checkbox_value = str(row[checkbox_column]).strip()

                if checkbox_value.upper() == "X":
                    invoice.locations["is_self_billing"] = [
                        self._get_cell_reference(row_index, checkbox_column)
                    ]
                    return True

                invoice.locations["is_self_billing"] = [
                    self._get_cell_reference(row_index, checkbox_column)
                ]
                return False

        invoice.locations["is_self_billing"] = []
        return False

    def _extract_invoice_number(
        self,
        rows: list[list[str]],
        invoice: InvoiceData,
    ) -> None:
        """Extract the invoice number when a recognized label is present."""
        for row_index, row in enumerate(rows):
            for column_index, cell in enumerate(row):
                match = self.INVOICE_NUMBER_PATTERN.search(cell)

                if not match:
                    continue

                # Support labels such as "Factura Nº: 12345" in one cell.
                inline_value = cell[match.end() :].strip(" :#.-")

                if inline_value:
                    invoice.invoice_number = inline_value
                    invoice.locations["invoice_number"] = self._get_cell_reference(
                        row_index, column_index
                    )
                    return

                value_column = next(
                    (
                        index
                        for index in range(column_index + 1, len(row))
                        if row[index]
                    ),
                    None,
                )

                if value_column is not None:
                    invoice.invoice_number = row[value_column]
                    invoice.locations["invoice_number"] = self._get_cell_reference(
                        row_index, value_column
                    )
                    return

        invoice.locations["invoice_number"] = ""

    def _extract_client(
        self,
        rows: list[list[str]],
        invoice: InvoiceData,
    ) -> None:
        """Extract client identity and address from the client block."""
        start_index = next(
            (
                index
                for index, row in enumerate(rows)
                if any(
                    re.search(r"\bDATOS\s+CLIENTE\b", value, re.IGNORECASE)
                    for value in row
                )
            ),
            None,
        )

        invoice.locations.setdefault("client", "")
        invoice.locations.setdefault("tax_id", "")
        invoice.locations.setdefault("address", [])

        if start_index is None:
            return

        # Find the column containing the client section heading.
        header_row = rows[start_index]
        header_column = next(
            (
                column_index
                for column_index, value in enumerate(header_row)
                if re.search(r"\bDATOS\s+CLIENTE\b", value, re.IGNORECASE)
            ),
            None,
        )

        if header_column is None:
            return

        client_lines: list[tuple[str, list[str]]] = []

        for row_index in range(start_index + 1, len(rows)):
            row = rows[row_index]

            # Only read cells in the client block, to the right of its heading.
            cells = [
                (column_index, value.strip())
                for column_index, value in enumerate(row)
                if column_index >= header_column and value and value.strip()
            ]

            if not cells:
                continue

            text = " ".join(value for _, value in cells).strip()

            # Stop when the invoice details section begins.
            if re.search(
                r"\b(DESCRIPCIÓN|CANT\.?|PRECIO\s+UNITARIO|IMPORTE|SUBTOTAL|"
                r"TIPO\s+IMPOSITIVO|IMPUESTOS|TOTAL|N[.º°]?\s*DE\s*FACTURA|FECHA)\b",
                text,
                re.IGNORECASE,
            ):
                break

            # Do not include invoice number/date or payment-attention text.
            if re.search(
                r"\b(N[.º°]?\s*DE\s*FACTURA|FECHA|ATT\.?)\b",
                text,
                re.IGNORECASE,
            ):
                continue

            if re.search(r"\bAUTOFACTURA\b", text, re.IGNORECASE):
                cells = [
                    (column_index, value)
                    for column_index, value in cells
                    if not re.search(r"\bAUTOFACTURA\b", value, re.IGNORECASE)
                    and not re.fullmatch(r"x", value, re.IGNORECASE)
                ]
                if not cells:
                    continue
                text = " ".join(value for _, value in cells).strip()

            tax_id_match = self.TAX_ID_PATTERN.search(text)

            if tax_id_match:
                invoice.tax_id = tax_id_match.group(1).upper()
                tax_cell = next(
                    (
                        (column_index, value)
                        for column_index, value in cells
                        if self.TAX_ID_PATTERN.search(value)
                    ),
                    None,
                )
                if tax_cell is not None:
                    invoice.locations["tax_id"] = self._get_cell_reference(
                        row_index, tax_cell[0]
                    )
                continue

            references = [
                self._get_cell_reference(row_index, column_index)
                for column_index, _ in cells
            ]
            client_lines.append((text, references))

        if client_lines:
            invoice.client = client_lines[0][0] or None
            invoice.locations["client"] = client_lines[0][1][0]

        if len(client_lines) > 1:
            address_lines = client_lines[1:]
            invoice.address = [text for text, _ in address_lines]
            invoice.locations["address"] = [
                references[0] for _, references in address_lines if references
            ]

    def _extract_totals(
        self,
        rows: list[list[str]],
        invoice: InvoiceData,
    ) -> None:
        """Extract financial totals and record the cells containing their values."""
        patterns = {
            "subtotal": re.compile(r"^\s*SUBTOTAL\s*$", re.IGNORECASE),
            "tax_rate": re.compile(
                r"^\s*TIPO\s+IMPOSITIVO\s*$",
                re.IGNORECASE,
            ),
            "taxes": re.compile(r"^\s*IMPUESTOS?\s*$", re.IGNORECASE),
            "total": re.compile(r"^\s*TOTAL\s*$", re.IGNORECASE),
        }

        for row_index, row in enumerate(rows):
            for column_index, cell in enumerate(row):
                for field_name, pattern in patterns.items():
                    if not pattern.fullmatch(cell):
                        continue

                    value_column = next(
                        (
                            index
                            for index in range(column_index + 1, len(row))
                            if row[index]
                        ),
                        None,
                    )

                    if value_column is None:
                        continue

                    setattr(invoice, field_name, row[value_column])
                    invoice.locations[field_name] = self._get_cell_reference(
                        row_index,
                        value_column,
                    )

    def _extract_lines(
        self,
        rows: list[list[str]],
        invoice: InvoiceData,
    ) -> None:
        """Extract detail lines and record source cells for every value."""
        header_index = self._find_detail_header(rows)

        if header_index is None:
            raise ValueError("Invoice detail header was not found.")

        locations = invoice.locations

        for field_name in (
            "descriptions",
            "quantities",
            "unit_prices",
            "amounts",
        ):
            locations[field_name] = []

        for row_index, row in enumerate(
            rows[header_index + 1 :],
            start=header_index + 1,
        ):
            cells = [
                (column_index, value) for column_index, value in enumerate(row) if value
            ]

            if not cells:
                continue

            row_text = " ".join(value for _, value in cells)

            if self.DETAIL_STOP_PATTERN.search(row_text):
                break

            if self.IGNORED_DETAIL_PATTERN.search(row_text):
                continue

            numeric_cells = [
                (column_index, value)
                for column_index, value in cells
                if self._is_numeric_cell(value)
            ]

            description_cells = [
                (column_index, value.strip())
                for column_index, value in cells
                if not self._is_numeric_cell(value) and value.strip()
            ]

            if not description_cells:
                continue

            quantity = ""
            unit_price = ""
            amount = ""
            quantity_location = ""
            unit_price_location = ""
            amount_location = ""

            if len(numeric_cells) >= 3:
                quantity_cell, unit_price_cell, amount_cell = numeric_cells[-3:]

                quantity = quantity_cell[1]
                unit_price = unit_price_cell[1]
                amount = amount_cell[1]

                quantity_location = self._get_cell_reference(
                    row_index,
                    quantity_cell[0],
                )
                unit_price_location = self._get_cell_reference(
                    row_index,
                    unit_price_cell[0],
                )
                amount_location = self._get_cell_reference(
                    row_index,
                    amount_cell[0],
                )

            for column_index, description in description_cells:
                invoice.descriptions.append(description)
                invoice.quantities.append(quantity)
                invoice.unit_prices.append(unit_price)
                invoice.amounts.append(amount)

                locations["descriptions"].append(
                    self._get_cell_reference(row_index, column_index)
                )
                locations["quantities"].append(quantity_location)
                locations["unit_prices"].append(unit_price_location)
                locations["amounts"].append(amount_location)

        logger.info(
            "Descripciones: %s | Cantidades: %s | Precios: %s | Importes: %s | Referencias: %s",
            len(invoice.descriptions),
            len(invoice.quantities),
            len(invoice.unit_prices),
            len(invoice.amounts),
            len(locations["descriptions"]),
        )

    def _find_detail_header(
        self,
        rows: list[list[str]],
    ) -> int | None:
        """Find the row containing the invoice detail column headings."""
        for index, row in enumerate(rows):
            text = " ".join(row).upper()

            if (
                "DESCRIPCIÓN" in text
                and re.search(r"\bCANT\.?\b", text)
                and "PRECIO UNITARIO" in text
                and "IMPORTE" in text
            ):
                return index

        return None

    def _is_numeric_cell(self, value: str) -> bool:
        """Check whether a complete cell contains a numeric value."""
        return bool(self.NUMBER_PATTERN.fullmatch(value))

    def _extract_distribution(
        self,
        rows: list[list[str]],
        invoice: InvoiceData,
    ) -> None:
        """Extract PEP codes and amounts from the REPARTO section."""
        invoice.peps = []
        invoice.pep_amounts = []
        invoice.locations["peps"] = []
        invoice.locations["pep_amounts"] = []

        reparto_position = None

        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                if re.fullmatch(r"REPARTO", value.strip(), re.IGNORECASE):
                    reparto_position = (row_index, column_index)
                    break
            if reparto_position is not None:
                break

        if reparto_position is None:
            return

        start_row, start_column = reparto_position

        stop_pattern = re.compile(
            r"\b(?:MAIL\s+DE\s+ENV[IÍ]O|SUBTOTAL|TIPO\s+IMPOSITIVO|"
            r"IMPUESTOS?|TOTAL)\b",
            re.IGNORECASE,
        )

        pep_pattern = re.compile(r"(?=.*\d)[A-Z0-9._/-]+", re.IGNORECASE)

        empty_rows = 0
        max_empty_rows = 2

        for row_index in range(start_row + 1, len(rows)):
            row = rows[row_index]
            row_text = " ".join(value for value in row if value)

            if stop_pattern.search(row_text):
                break

            pep_value = row[start_column] if start_column < len(row) else ""
            amount_column = start_column + 1
            amount_value = row[amount_column] if amount_column < len(row) else ""

            if not pep_value and not amount_value:
                empty_rows += 1
                if empty_rows >= max_empty_rows:
                    break
                continue

            empty_rows = 0

            if not pep_value or not amount_value:
                continue

            if not pep_pattern.fullmatch(pep_value):
                continue

            normalized_amount = amount_value.replace("\xa0", "").replace(" ", "")

            if not self._is_numeric_cell(normalized_amount):
                continue

            invoice.peps.append(pep_value)
            invoice.pep_amounts.append(amount_value)

            invoice.locations["peps"].append(
                self._get_cell_reference(row_index, start_column)
            )
            invoice.locations["pep_amounts"].append(
                self._get_cell_reference(row_index, amount_column)
            )

        logger.info(
            "Reparto: %s PEP | Referencias PEP: %s | Referencias importes: %s",
            len(invoice.peps),
            len(invoice.locations["peps"]),
            len(invoice.locations["pep_amounts"]),
        )

    def _extract_email(
        self,
        rows: list[list[str]],
        invoice: InvoiceData,
    ) -> None:
        """Extract the email address next to the MAIL DE ENVIO label."""
        invoice.email = None
        invoice.locations["email"] = ""

        label_pattern = re.compile(
            r"\bMAIL\s+DE\s+ENV[IÍ]O\b",
            re.IGNORECASE,
        )

        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                match = label_pattern.search(value)

                if not match:
                    continue

                inline_text = value[match.end() :]
                email_match = self.EMAIL_PATTERN.search(inline_text)

                if email_match:
                    invoice.email = email_match.group(0)
                    invoice.locations["email"] = self._get_cell_reference(
                        row_index,
                        column_index,
                    )
                    return

                for next_column in range(column_index + 1, len(row)):
                    if not row[next_column]:
                        continue

                    email_match = self.EMAIL_PATTERN.search(row[next_column])

                    if email_match:
                        invoice.email = email_match.group(0)
                        invoice.locations["email"] = self._get_cell_reference(
                            row_index,
                            next_column,
                        )
                    return

                return


def extract_invoice(
    file_path: str | Path,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Extract invoice data and return it as a dictionary."""
    loader = InvoiceExcelLoader(file_path, sheet_name)
    return loader.load().to_dict()
