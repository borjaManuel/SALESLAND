import pandas as pd
from database.connection import Database
from loaders.base_loader import BaseLoader
from logger.logger import Logger
from sqlalchemy import text

LOGGER = Logger.get_logger(__name__)


class EmitidasIbanVTOFactoringLoader(BaseLoader):
    """
    Loader responsible for importing issued invoice IBAN and factoring data
    into the emitidas_iban_vto_factoring PostgreSQL table.

    The loader transforms the Excel column names into the database column
    names and performs an upsert based on the customer code.
    """

    def __init__(self, database: Database):
        self.database = database

    def load(self, dataframe: pd.DataFrame):
        """
        Loads issued invoice IBAN and factoring data into PostgreSQL.

        The input Excel data is expected to contain the following columns:

            - CODIGO
            - CLIENTE
            - VENCIMIENTO
            - IBAN
            - FACTORING

        These columns are mapped to:

            - codigo
            - cliente
            - vencimiento
            - iban
            - factoring

        Args:
            dataframe: DataFrame containing the Excel data.

        Raises:
            ValueError: If the required columns are missing or invalid data
                is found.
            Exception: If the database insertion fails.
        """

        LOGGER.info(
            "Preparing EMITIDAS_IBAN_VTO_FACTORING insertion. Records: %s",
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
            INSERT INTO emitidas_iban_vto_factoring (
                codigo,
                cliente,
                vencimiento,
                iban,
                factoring
            )
            VALUES (
                :codigo,
                :cliente,
                :vencimiento,
                :iban,
                :factoring
            )
            ON CONFLICT (codigo) DO UPDATE SET
                cliente = EXCLUDED.cliente,
                vencimiento = EXCLUDED.vencimiento,
                iban = EXCLUDED.iban,
                factoring = EXCLUDED.factoring
        """

        with self.database.engine.begin() as connection:

            try:
                connection.execute(text(sql), records)

            except Exception as e:

                LOGGER.error(
                    "Error inserting EMITIDAS_IBAN_VTO_FACTORING data in batch"
                )

                if records:
                    self.debug_record(records[0])

                raise e

        LOGGER.info("EMITIDAS_IBAN_VTO_FACTORING insertion completed successfully")

    def transform(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms Excel column names into database column names.

        Args:
            dataframe: Input Excel DataFrame.

        Returns:
            Transformed DataFrame.
        """

        dataframe.columns = dataframe.columns.str.replace(
            "\u00a0", " ", regex=False
        ).str.strip()

        required_columns = [
            "CODIGO",
            "CLIENTE",
            "VENCIMIENTO",
            "IBAN",
            "FACTORING",
        ]

        missing_columns = [
            column for column in required_columns if column not in dataframe.columns
        ]

        if missing_columns:
            raise ValueError(
                "Missing required columns in EMITIDAS_IBAN_VTO_FACTORING.xlsx: "
                + ", ".join(missing_columns)
            )

        dataframe = dataframe[required_columns].copy()

        dataframe = dataframe.rename(
            columns={
                "CODIGO": "codigo",
                "CLIENTE": "cliente",
                "VENCIMIENTO": "vencimiento",
                "IBAN": "iban",
                "FACTORING": "factoring",
            }
        )

        # Normalizamos espacios y valores vacíos
        for column in ["cliente", "vencimiento", "iban", "factoring"]:
            dataframe[column] = (
                dataframe[column].astype("string").str.strip().replace("", pd.NA)
            )

        return dataframe

    def validate(self, dataframe: pd.DataFrame):
        """
        Validates the transformed EMITIDAS_IBAN_VTO_FACTORING data.

        Args:
            dataframe: Transformed DataFrame.

        Raises:
            ValueError: If invalid data is detected.
        """

        if dataframe.empty:
            raise ValueError(
                "EMITIDAS_IBAN_VTO_FACTORING.xlsx does not contain any records"
            )

        # Validar códigos
        invalid_codes = dataframe[dataframe["codigo"].isna()]

        if not invalid_codes.empty:
            LOGGER.error(
                "Empty codigo values found: %s",
                invalid_codes.to_dict(),
            )

            raise ValueError("codigo cannot be empty")

        # Validar clientes
        invalid_clients = dataframe[dataframe["cliente"].isna()]

        if not invalid_clients.empty:
            LOGGER.error(
                "Empty cliente values found: %s",
                invalid_clients.to_dict(),
            )

            raise ValueError("cliente cannot be empty")

        # Validar códigos duplicados
        duplicated_codes = dataframe[dataframe["codigo"].duplicated(keep=False)]

        if not duplicated_codes.empty:
            LOGGER.error(
                "Duplicated codigo values found: %s",
                duplicated_codes.to_dict(),
            )

            raise ValueError("codigo cannot contain duplicate values")

        # Validar longitudes máximas
        limits = {
            "cliente": 150,
            "vencimiento": 50,
            "iban": 34,
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
            "cliente": 150,
            "vencimiento": 50,
            "iban": 34,
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
