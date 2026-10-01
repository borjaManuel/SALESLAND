import pandas as pd
from sqlalchemy import text

from database.connection import Database
from loaders.base_loader import BaseLoader
from logger.logger import Logger
from mappings.visa_mapping import VISA_MAPPING

LOGGER = Logger.get_logger(__name__)


class VisaLoader(BaseLoader):
    """
    Loader responsible for importing Visa data.
    """

    def __init__(self, database: Database):
        self.database = database

    def load(self, dataframe, numero_lote):

        dataframe = self.transform(dataframe, VISA_MAPPING)

        if dataframe.empty:
            raise ValueError("VISA Excel does not contain any records")

        try:
            numero_lote = int(numero_lote)
        except (TypeError, ValueError) as error:
            raise ValueError("numero_lote must be an integer") from error

        if numero_lote < 1:
            raise ValueError("numero_lote must be a positive integer")

        for column in ("factura", "cuenta_contable", "pep"):
            dataframe[column] = dataframe[column].astype("string").str.strip()
            if dataframe[column].isna().any() or dataframe[column].eq("").any():
                raise ValueError(f"{column} cannot be empty")

        self.validate_lengths(dataframe)

        sql = """

        INSERT INTO excell_visa (
            factura,
            cuenta_contable,
            pep,
            numero_lote
        )
        VALUES (
            :factura,
            :cuenta_contable,
            :pep,
            :numero_lote
        )
        ON CONFLICT (factura, numero_lote) DO UPDATE SET
            cuenta_contable = EXCLUDED.cuenta_contable,
            pep = EXCLUDED.pep
        """

        with self.database.engine.begin() as connection:
            dataframe["numero_lote"] = numero_lote
            dataframe = dataframe.astype(object).where(pd.notnull(dataframe), None)
            records = dataframe.to_dict(orient="records")

            LOGGER.info(
                "Preparing VISA insertion. Records: %s, batch: %s",
                len(records),
                numero_lote,
            )
            connection.execute(text(sql), records)

        LOGGER.info("VISA insertion completed successfully for batch %s", numero_lote)

    def validate_lengths(self, dataframe):
        limits = {
            "factura": 50,
            "cuenta_contable": 20,
            "pep": 20,
        }

        for field, size in limits.items():
            invalid = dataframe[field].str.len() > size
            if invalid.any():
                raise ValueError(f"{field} exceeds maximum length {size}")