import pandas as pd
from database.connection import Database
from loaders.base_loader import BaseLoader
from logger.logger import Logger
from sqlalchemy import text

LOGGER = Logger.get_logger(__name__)


class ClaseFacturasEmitidasLoader(BaseLoader):
    """
    Loader responsible for importing issued invoice class data
    into the clase_facturas_emitidas PostgreSQL table.

    The loader transforms the Excel column names into the database column
    names and performs an upsert based on the PEP.
    """

    def __init__(self, database: Database):
        self.database = database

    def load(self, dataframe: pd.DataFrame):
        """
        Loads issued invoice class data into PostgreSQL.

        The input Excel data is expected to contain the following columns:

            - PEP
            - CLASE DE FACTURA

        These columns are mapped to:

            - pep
            - clase_factura

        Args:
            dataframe: DataFrame containing the Excel data.

        Raises:
            ValueError: If the required columns are missing or invalid data
                is found.
            Exception: If the database insertion fails.
        """

        LOGGER.info(
            "Preparing CLASE_FACTURAS_EMITIDAS insertion. Records: %s",
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
            INSERT INTO clase_facturas_emitidas (
                pep,
                clase_factura
            )
            VALUES (
                :pep,
                :clase_factura
            )
            ON CONFLICT (pep) DO UPDATE SET
                clase_factura = EXCLUDED.clase_factura
        """

        with self.database.engine.begin() as connection:

            try:
                connection.execute(text(sql), records)

            except Exception as e:

                LOGGER.error("Error inserting CLASE_FACTURAS_EMITIDAS data in batch")

                if records:
                    self.debug_record(records[0])

                raise e

        LOGGER.info("CLASE_FACTURAS_EMITIDAS insertion completed successfully")

    def transform(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms Excel column names into database column names.

        Args:
            dataframe: Input Excel DataFrame.

        Returns:
            Transformed DataFrame.
        """

        required_columns = [
            "PEP",
            "CLASE DE FACTURA",
        ]

        missing_columns = [
            column for column in required_columns if column not in dataframe.columns
        ]

        if missing_columns:
            raise ValueError(
                "Missing required columns in CLASE_FACTURAS_EMITIDAS.xlsx: "
                + ", ".join(missing_columns)
            )

        dataframe = dataframe[
            [
                "PEP",
                "CLASE DE FACTURA",
            ]
        ].copy()

        dataframe = dataframe.rename(
            columns={
                "PEP": "pep",
                "CLASE DE FACTURA": "clase_factura",
            }
        )

        # Normalizamos espacios y valores vacíos
        dataframe["pep"] = dataframe["pep"].astype(str).str.strip()

        dataframe["clase_factura"] = dataframe["clase_factura"].astype(str).str.strip()

        return dataframe

    def validate(self, dataframe: pd.DataFrame):
        """
        Validates the transformed CLASE_FACTURAS_EMITIDAS data.

        Args:
            dataframe: Transformed DataFrame.

        Raises:
            ValueError: If invalid data is detected.
        """

        if dataframe.empty:
            raise ValueError(
                "CLASE_FACTURAS_EMITIDAS.xlsx does not contain any records"
            )

        # Validar valores vacíos
        invalid_peps = dataframe[
            dataframe["pep"].isna() | (dataframe["pep"].astype(str).str.strip() == "")
        ]

        if not invalid_peps.empty:
            LOGGER.error(
                "Empty pep values found: %s",
                invalid_peps.to_dict(),
            )

            raise ValueError("pep cannot be empty")

        invalid_classes = dataframe[
            dataframe["clase_factura"].isna()
            | (dataframe["clase_factura"].astype(str).str.strip() == "")
        ]

        if not invalid_classes.empty:
            LOGGER.error(
                "Empty clase_factura values found: %s",
                invalid_classes.to_dict(),
            )

            raise ValueError("clase_factura cannot be empty")

        # Validar longitudes máximas
        limits = {
            "pep": 50,
            "clase_factura": 50,
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

    def debug_record(self, record):
        """
        Logs the contents and lengths of a record that caused
        a database insertion error.

        Args:
            record: Database-ready record.
        """

        limits = {
            "pep": 50,
            "clase_factura": 50,
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
