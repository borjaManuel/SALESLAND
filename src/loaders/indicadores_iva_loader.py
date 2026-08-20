import pandas as pd
from sqlalchemy import text

from database.connection import Database
from loaders.base_loader import BaseLoader
from logger.logger import Logger

LOGGER = Logger.get_logger(__name__)


class IndicadorIvaLoader(BaseLoader):
    """
    Loader responsible for importing VAT indicator data
    into the indicador_iva PostgreSQL table.

    The loader transforms the Excel column names into the database
    column names and performs an upsert based on the VAT indicator.
    """

    def __init__(self, database: Database):
        self.database = database

    def load(self, dataframe: pd.DataFrame):
        """
        Loads VAT indicator data into PostgreSQL.

        The input Excel data is expected to contain the following columns:

            - INDICADORES IVA
            - TASA
            - TIPO
            - PRORRATA

        These columns are mapped to:

            - indicadores_iva
            - tasa
            - tipo
            - prorrata

        Args:
            dataframe: DataFrame containing the Excel data.

        Raises:
            ValueError: If the required columns are missing or invalid data
                is found.
            Exception: If the database insertion fails.
        """

        LOGGER.info(
            "Preparing INDICADOR_IVA insertion. Records: %s",
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
            INSERT INTO indicador_iva (
                indicadores_iva,
                tasa,
                tipo,
                prorrata
            )
            VALUES (
                :indicadores_iva,
                :tasa,
                :tipo,
                :prorrata
            )
            ON CONFLICT (indicadores_iva) DO UPDATE SET
                tasa = EXCLUDED.tasa,
                tipo = EXCLUDED.tipo,
                prorrata = EXCLUDED.prorrata
        """

        with self.database.engine.begin() as connection:

            try:
                connection.execute(text(sql), records)

            except Exception as e:

                LOGGER.error("Error inserting INDICADOR_IVA data in batch")

                if records:
                    self.debug_record(records[0])

                raise e

        LOGGER.info("INDICADOR_IVA insertion completed successfully")

    def transform(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms Excel column names into database column names.

        Args:
            dataframe: Input DataFrame.

        Returns:
            Transformed DataFrame.
        """

        dataframe = dataframe.copy()

        # Normalize Excel column names.
        # Handles leading/trailing spaces and non-breaking spaces.
        dataframe.columns = (
            dataframe.columns.astype(str)
            .str.replace("\u00a0", " ", regex=False)
            .str.strip()
        )

        required_columns = [
            "INDICADORES IVA",
            "TASA",
            "TIPO",
            "PRORRATA",
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
                "Missing required columns in INDICADOR_IVA.xlsx: "
                + ", ".join(missing_columns)
            )

        dataframe = dataframe[
            [
                "INDICADORES IVA",
                "TASA",
                "TIPO",
                "PRORRATA",
            ]
        ].copy()

        dataframe = dataframe.rename(
            columns={
                "INDICADORES IVA": "indicadores_iva",
                "TASA": "tasa",
                "TIPO": "tipo",
                "PRORRATA": "prorrata",
            }
        )

        dataframe["indicadores_iva"] = (
            dataframe["indicadores_iva"].astype(str).str.strip()
        )

        dataframe["tasa"] = dataframe["tasa"].apply(self.format_percentage)

        dataframe["tipo"] = dataframe["tipo"].astype(str).str.strip()

        dataframe["prorrata"] = dataframe["prorrata"].apply(self.format_percentage)

        return dataframe

    def format_percentage(self, value):
        """
        Converts a decimal percentage value into a percentage string.

        Examples:
            0     -> "0%"
            0.04  -> "4%"
            0.10  -> "10%"
            0.21  -> "21%"
            0.05  -> "5%"
        """

        if pd.isna(value):
            return None

        value = str(value).strip()

        if value == "":
            return None

        try:
            numeric_value = float(value)

            percentage = numeric_value * 100

            if percentage.is_integer():
                return f"{int(percentage)}%"

            return f"{percentage:g}%"

        except ValueError:

            if value.endswith("%"):
                return value

            raise ValueError(f"Invalid percentage value: {value}")

    def validate(self, dataframe: pd.DataFrame):
        """
        Validates the transformed INDICADOR_IVA data.

        Args:
            dataframe: Transformed DataFrame.

        Raises:
            ValueError: If invalid data is detected.
        """

        if dataframe.empty:
            raise ValueError("INDICADOR_IVA.xlsx does not contain any records")

        # Validate INDICADORES IVA
        invalid_indicators = dataframe[
            dataframe["indicadores_iva"].isna()
            | (dataframe["indicadores_iva"].astype(str).str.strip() == "")
        ]

        if not invalid_indicators.empty:
            LOGGER.error(
                "Empty indicadores_iva values found: %s",
                invalid_indicators.to_dict(),
            )

            raise ValueError("indicadores_iva cannot be empty")

        # Validate TASA
        invalid_rates = dataframe[
            dataframe["tasa"].isna() | (dataframe["tasa"].astype(str).str.strip() == "")
        ]

        if not invalid_rates.empty:
            LOGGER.error(
                "Empty tasa values found: %s",
                invalid_rates.to_dict(),
            )

            raise ValueError("tasa cannot be empty")

        # Validate TIPO
        invalid_types = dataframe[
            dataframe["tipo"].isna() | (dataframe["tipo"].astype(str).str.strip() == "")
        ]

        if not invalid_types.empty:
            LOGGER.error(
                "Empty tipo values found: %s",
                invalid_types.to_dict(),
            )

            raise ValueError("tipo cannot be empty")

        # PRORRATA can be empty.

        # Validate maximum lengths
        limits = {
            "indicadores_iva": 10,
            "tasa": 10,
            "tipo": 100,
            "prorrata": 10,
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

        # Validate duplicate VAT indicators
        duplicates = dataframe[dataframe["indicadores_iva"].duplicated(keep=False)]

        if not duplicates.empty:
            LOGGER.error(
                "Duplicate indicadores_iva values found: %s",
                duplicates[["indicadores_iva"]].to_dict(),
            )

            raise ValueError("indicadores_iva contains duplicate values")

    def debug_record(self, record):
        """
        Logs the contents and lengths of a record that caused
        a database insertion error.

        Args:
            record: Database-ready record.
        """

        limits = {
            "indicadores_iva": 10,
            "tasa": 10,
            "tipo": 100,
            "prorrata": 10,
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
