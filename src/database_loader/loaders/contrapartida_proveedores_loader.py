import pandas as pd
from sqlalchemy import text

from database.connection import Database
from loaders.base_loader import BaseLoader
from logger.logger import Logger

LOGGER = Logger.get_logger(__name__)


class ContrapartidaProveedoresLoader(BaseLoader):
    """
    Loader responsible for importing supplier invoice counterpart data
    into the contrapartida_proveedores PostgreSQL table.

    The loader transforms the Excel column names into the database column
    names and performs an upsert based on the supplier number.
    """

    def __init__(self, database: Database):
        self.database = database

    def load(self, dataframe: pd.DataFrame):
        """
        Loads supplier invoice counterpart data into PostgreSQL.

        The input Excel data is expected to contain the following columns:

            - NUMERO
            - PROVEEDOR
            - CUENTA DE GASTO
            - CLASE DE DOCUMENTO

        These columns are mapped to:

            - numero
            - proveedor
            - cuenta_gasto
            - clase_documento

        Args:
            dataframe: DataFrame containing the Excel data.

        Raises:
            ValueError: If the required columns are missing or invalid data
                is found.
            Exception: If the database insertion fails.
        """

        LOGGER.info(
            "Preparing CONTRAPARTIDA_PROVEEDORES insertion. Records: %s",
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
            INSERT INTO contrapartida_proveedores (
                numero,
                proveedor,
                cuenta_gasto,
                clase_documento
            )
            VALUES (
                :numero,
                :proveedor,
                :cuenta_gasto,
                :clase_documento
            )
            ON CONFLICT (numero) DO UPDATE SET
                proveedor = EXCLUDED.proveedor,
                cuenta_gasto = EXCLUDED.cuenta_gasto,
                clase_documento = EXCLUDED.clase_documento
        """

        with self.database.engine.begin() as connection:

            try:
                connection.execute(text(sql), records)

            except Exception as e:

                LOGGER.error("Error inserting CONTRAPARTIDA_PROVEEDORES data in batch")

                if records:
                    self.debug_record(records[0])

                raise e

        LOGGER.info("CONTRAPARTIDA_PROVEEDORES insertion completed successfully")

    def transform(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms Excel column names into database column names.

        Args:
            dataframe: Input Excel DataFrame.

        Returns:
            Transformed DataFrame.
        """

        # Normalize Excel column names
        dataframe = dataframe.copy()

        dataframe.columns = (
            dataframe.columns.astype(str)
            .str.replace("\u00a0", " ", regex=False)
            .str.strip()
        )

        required_columns = [
            "NUMERO",
            "PROVEEDOR",
            "CUENTA DE GASTO",
            "CLASE DE DOCUMENTO",
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
                "Missing required columns in "
                "CONTRAPARTIDA_PROVEEDORES.xlsx: " + ", ".join(missing_columns)
            )

        dataframe = dataframe[
            [
                "NUMERO",
                "PROVEEDOR",
                "CUENTA DE GASTO",
                "CLASE DE DOCUMENTO",
            ]
        ].copy()

        dataframe = dataframe.rename(
            columns={
                "NUMERO": "numero",
                "PROVEEDOR": "proveedor",
                "CUENTA DE GASTO": "cuenta_gasto",
                "CLASE DE DOCUMENTO": "clase_documento",
            }
        )

        # Normalize values
        dataframe["numero"] = dataframe["numero"].astype(str).str.strip()

        dataframe["proveedor"] = dataframe["proveedor"].astype(str).str.strip()

        dataframe["cuenta_gasto"] = dataframe["cuenta_gasto"].astype(str).str.strip()

        dataframe["clase_documento"] = (
            dataframe["clase_documento"].astype(str).str.strip()
        )

        return dataframe

    def validate(self, dataframe: pd.DataFrame):
        """
        Validates the transformed CONTRAPARTIDA_PROVEEDORES data.

        Args:
            dataframe: Transformed DataFrame.

        Raises:
            ValueError: If invalid data is detected.
        """

        if dataframe.empty:
            raise ValueError(
                "CONTRAPARTIDA_PROVEEDORES.xlsx does not contain any records"
            )

        # Validar NUMERO
        invalid_numbers = dataframe[
            dataframe["numero"].isna()
            | (dataframe["numero"].astype(str).str.strip() == "")
        ]

        if not invalid_numbers.empty:
            LOGGER.error(
                "Empty numero values found: %s",
                invalid_numbers.to_dict(),
            )

            raise ValueError("numero cannot be empty")

        # Validar PROVEEDOR
        invalid_suppliers = dataframe[
            dataframe["proveedor"].isna()
            | (dataframe["proveedor"].astype(str).str.strip() == "")
        ]

        if not invalid_suppliers.empty:
            LOGGER.error(
                "Empty proveedor values found: %s",
                invalid_suppliers.to_dict(),
            )

            raise ValueError("proveedor cannot be empty")

        # Validar CUENTA DE GASTO
        invalid_accounts = dataframe[
            dataframe["cuenta_gasto"].isna()
            | (dataframe["cuenta_gasto"].astype(str).str.strip() == "")
        ]

        if not invalid_accounts.empty:
            LOGGER.error(
                "Empty cuenta_gasto values found: %s",
                invalid_accounts.to_dict(),
            )

            raise ValueError("cuenta_gasto cannot be empty")

        # CLASE DE DOCUMENTO puede estar vacía.
        # No se valida como obligatorio.

        # Validar longitudes máximas
        limits = {
            "numero": 10,
            "proveedor": 100,
            "cuenta_gasto": 20,
            "clase_documento": 10,
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

        # Validar que no existan números de proveedor duplicados
        duplicates = dataframe[dataframe["numero"].duplicated(keep=False)]

        if not duplicates.empty:
            LOGGER.error(
                "Duplicate numero values found: %s",
                duplicates[["numero"]].to_dict(),
            )

            raise ValueError("numero contains duplicate values")

    def debug_record(self, record):
        """
        Logs the contents and lengths of a record that caused
        a database insertion error.

        Args:
            record: Database-ready record.
        """

        limits = {
            "numero": 10,
            "proveedor": 100,
            "cuenta_gasto": 20,
            "clase_documento": 10,
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
