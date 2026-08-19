import pandas as pd
from sqlalchemy import text

from database.connection import Database
from loaders.base_loader import BaseLoader
from logger.logger import Logger

LOGGER = Logger.get_logger(__name__)


class ContrapartidaClientesLoader(BaseLoader):
    """
    Loader responsible for importing customer invoice counterpart data
    into the contrapartida_clientes PostgreSQL table.

    The loader transforms the Excel column names into the database column
    names and performs an upsert based on the invoice class.
    """

    def __init__(self, database: Database):
        self.database = database

    def load(self, dataframe: pd.DataFrame):
        """
        Loads customer invoice counterpart data into PostgreSQL.

        The input Excel data is expected to contain the following columns:

            - CLASE DE FACTURA
            - CUENTA CONTABLE

        These columns are mapped to:

            - clase_factura
            - cuenta_contable

        Args:
            dataframe: DataFrame containing the Excel data.

        Raises:
            ValueError: If the required columns are missing or invalid data
                is found.
            Exception: If the database insertion fails.
        """

        LOGGER.info(
            "Preparing CONTRAPARTIDA_CLIENTES insertion. Records: %s",
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
            INSERT INTO contrapartida_clientes (
                clase_factura,
                cuenta_contable
            )
            VALUES (
                :clase_factura,
                :cuenta_contable
            )
            ON CONFLICT (clase_factura) DO UPDATE SET
                cuenta_contable = EXCLUDED.cuenta_contable
        """

        with self.database.engine.begin() as connection:

            try:
                connection.execute(text(sql), records)

            except Exception as e:

                LOGGER.error("Error inserting CONTRAPARTIDA_CLIENTES data in batch")

                if records:
                    self.debug_record(records[0])

                raise e

        LOGGER.info("CONTRAPARTIDA_CLIENTES insertion completed successfully")

    def transform(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms Excel column names into database column names.

        Args:
            dataframe: Input Excel DataFrame.

        Returns:
            Transformed DataFrame.
        """

        required_columns = [
            "CLASE DE FACTURA",
            "CUENTA CONTABLE",
        ]

        missing_columns = [
            column for column in required_columns if column not in dataframe.columns
        ]

        if missing_columns:
            raise ValueError(
                "Missing required columns in CONTRAPARTIDA_CLIENTES.xlsx: "
                + ", ".join(missing_columns)
            )

        dataframe = dataframe[
            [
                "CLASE DE FACTURA",
                "CUENTA CONTABLE",
            ]
        ].copy()

        dataframe = dataframe.rename(
            columns={
                "CLASE DE FACTURA": "clase_factura",
                "CUENTA CONTABLE": "cuenta_contable",
            }
        )

        # Normalizamos espacios y valores vacíos
        dataframe["clase_factura"] = dataframe["clase_factura"].astype(str).str.strip()

        dataframe["cuenta_contable"] = (
            dataframe["cuenta_contable"].astype(str).str.strip()
        )

        return dataframe

    def validate(self, dataframe: pd.DataFrame):
        """
        Validates the transformed CONTRAPARTIDA_CLIENTES data.

        Args:
            dataframe: Transformed DataFrame.

        Raises:
            ValueError: If invalid data is detected.
        """

        if dataframe.empty:
            raise ValueError("CONTRAPARTIDA_CLIENTES.xlsx does not contain any records")

        # Validar valores vacíos
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

        invalid_accounts = dataframe[
            dataframe["cuenta_contable"].isna()
            | (dataframe["cuenta_contable"].astype(str).str.strip() == "")
        ]

        if not invalid_accounts.empty:
            LOGGER.error(
                "Empty cuenta_contable values found: %s",
                invalid_accounts.to_dict(),
            )

            raise ValueError("cuenta_contable cannot be empty")

        # Validar longitudes máximas
        limits = {
            "clase_factura": 50,
            "cuenta_contable": 20,
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
            "clase_factura": 50,
            "cuenta_contable": 20,
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
