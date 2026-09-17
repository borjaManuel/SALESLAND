import pandas as pd
from sqlalchemy import text

from database.connection import Database
from loaders.base_loader import BaseLoader
from logger.logger import Logger

LOGGER = Logger.get_logger(__name__)


class IndicadorImpuestoLoader(BaseLoader):
    """
    Loader responsible for importing tax indicator data
    into the indicador_impuesto PostgreSQL table.

    The loader transforms the Excel column names into the database
    column names and performs an upsert based on the PEP value.
    """

    def __init__(self, database: Database):
        self.database = database

    def load(self, dataframe: pd.DataFrame):
        """
        Loads tax indicator data into PostgreSQL.

        The input Excel data is expected to contain the following columns:

            - PEP
            - LITERAL
            - FINANCIERO

        These columns are mapped to:

            - pep
            - literal
            - financiero

        Args:
            dataframe: DataFrame containing the Excel data.

        Raises:
            ValueError: If the required columns are missing or invalid data
                is found.
            Exception: If the database insertion fails.
        """

        LOGGER.info(
            "Preparing INDICADOR_IMPUESTO insertion. Records: %s",
            len(dataframe),
        )

        dataframe = self.transform(dataframe)

        self.validate(dataframe)

        # Convert NaN / NaT to None real para PostgreSQL
        dataframe = dataframe.astype(object).where(
            pd.notnull(dataframe),
            None,
        )

        records = dataframe.to_dict(orient="records")

        sql = """
            INSERT INTO indicador_impuesto (
                pep,
                literal,
                financiero
            )
            VALUES (
                :pep,
                :literal,
                :financiero
            )
            ON CONFLICT (pep) DO UPDATE SET
                literal = EXCLUDED.literal,
                financiero = EXCLUDED.financiero
        """

        with self.database.engine.begin() as connection:

            try:
                connection.execute(text(sql), records)

            except Exception as e:

                LOGGER.error("Error inserting INDICADOR_IMPUESTO data in batch")

                if records:
                    self.debug_record(records[0])

                raise e

        LOGGER.info("INDICADOR_IMPUESTO insertion completed successfully")

    def transform(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms Excel column names into database column names.

        Args:
            dataframe: Input Excel DataFrame.

        Returns:
            Transformed DataFrame.
        """

        dataframe = dataframe.copy()

        # Normalize Excel column names.
        # This handles leading/trailing spaces and non-breaking spaces.
        dataframe.columns = (
            dataframe.columns.astype(str)
            .str.replace("\u00a0", " ", regex=False)
            .str.strip()
        )

        required_columns = [
            "PEP",
            "LITERAL",
            "FINANCIERO",
        ]

        missing_columns = [
            column for column in required_columns if column not in dataframe.columns
        ]

        if missing_columns:
            LOGGER.error(
                "Columns received from Excel: %s",
                list(dataframe.columns),
            )

            raise ValueError(
                "Missing required columns in INDICADOR_IMPUESTO.xlsx: "
                + ", ".join(missing_columns)
            )

        dataframe = dataframe[
            [
                "PEP",
                "LITERAL",
                "FINANCIERO",
            ]
        ].copy()

        dataframe = dataframe.rename(
            columns={
                "PEP": "pep",
                "LITERAL": "literal",
                "FINANCIERO": "financiero",
            }
        )

        # PEP must remain a string because it can contain leading zeros.
        dataframe["pep"] = dataframe["pep"].astype(str).str.strip()

        dataframe["literal"] = dataframe["literal"].astype(str).str.strip()

        dataframe["financiero"] = dataframe["financiero"].astype(str).str.strip()

        return dataframe

    def validate(self, dataframe: pd.DataFrame):
        """
        Validates the transformed INDICADOR_IMPUESTO data.

        Args:
            dataframe: Transformed DataFrame.

        Raises:
            ValueError: If invalid data is detected.
        """

        if dataframe.empty:
            raise ValueError("INDICADOR_IMPUESTO.xlsx does not contain any records")

        # Validate PEP
        invalid_pep = dataframe[
            dataframe["pep"].isna() | (dataframe["pep"].astype(str).str.strip() == "")
        ]

        if not invalid_pep.empty:
            LOGGER.error(
                "Empty pep values found: %s",
                invalid_pep.to_dict(),
            )

            raise ValueError("pep cannot be empty")

        # Validate LITERAL
        invalid_literals = dataframe[
            dataframe["literal"].isna()
            | (dataframe["literal"].astype(str).str.strip() == "")
        ]

        if not invalid_literals.empty:
            LOGGER.error(
                "Empty literal values found: %s",
                invalid_literals.to_dict(),
            )

            raise ValueError("literal cannot be empty")

        # Validate FINANCIERO
        invalid_financiero = dataframe[
            dataframe["financiero"].isna()
            | (dataframe["financiero"].astype(str).str.strip() == "")
        ]

        if not invalid_financiero.empty:
            LOGGER.error(
                "Empty financiero values found: %s",
                invalid_financiero.to_dict(),
            )

            raise ValueError("financiero cannot be empty")

        # Validate maximum lengths
        limits = {
            "pep": 10,
            "literal": 100,
            "financiero": 2,
        }

        for field, size in limits.items():

            invalid = dataframe[
                dataframe[field].notna()
                & (dataframe[field].astype(str).str.len() > size)
            ]

            if not invalid.empty:
                LOGGER.error(
                    "Field %s exceeds limit %s",
                    field,
                    size,
                )

                LOGGER.error(invalid[[field]].to_dict())

                raise ValueError(f"{field} exceeds maximum length {size}")

        # Validate duplicate PEP values in the Excel file.
        duplicates = dataframe[dataframe["pep"].duplicated(keep=False)]

        if not duplicates.empty:
            LOGGER.error(
                "Duplicate pep values found: %s",
                duplicates[["pep"]].to_dict(),
            )

            raise ValueError("pep contains duplicate values")

        # Validate allowed FINANCIERO values.
        allowed_values = {"SI", "NO"}

        invalid_values = dataframe[~dataframe["financiero"].isin(allowed_values)]

        if not invalid_values.empty:
            LOGGER.error(
                "Invalid financiero values found: %s",
                invalid_values[["financiero"]].to_dict(),
            )

            raise ValueError("financiero must contain SI or NO")

    def debug_record(self, record):
        """
        Logs the contents and lengths of a record that caused
        a database insertion error.

        Args:
            record: Database-ready record.
        """

        limits = {
            "pep": 10,
            "literal": 100,
            "financiero": 2,
        }

        for field, value in record.items():

            if value is not None:

                length = len(str(value))
                limit = limits.get(field)

                LOGGER.error(
                    "%s -> value=%r length=%s limit=%s",
                    field,
                    value,
                    length,
                    limit,
                )

                if limit and length > limit:
                    LOGGER.error(
                        "!!! FIELD EXCEEDS LIMIT: %s",
                        field,
                    )
