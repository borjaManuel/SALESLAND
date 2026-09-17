import pandas as pd
from sqlalchemy import text

from database.connection import Database
from loaders.base_loader import BaseLoader
from logger.logger import Logger
from mappings.kna1_mapping import KNA1_MAPPING

LOGGER = Logger.get_logger(__name__)


class Kna1Loader(BaseLoader):
    """
    Loader responsible for importing KNA1 master data into PostgreSQL.

    This loader transforms Excel data according to the KNA1 field mapping
    and inserts the resulting records into the target database table.
    """

    def __init__(self, database: Database):
        self.database = database

    def load(self, dataframe):
        """
        Loads KNA1 records into the PostgreSQL database.

        The process includes:
            - Transforming the input DataFrame using the KNA1 field mapping.
            - Converting the transformed data into database-ready records.
            - Inserting the records into the KNA1 table within a transaction.

        Args:
            dataframe (pandas.DataFrame): DataFrame containing the KNA1 Excel data.

        Raises:
            SQLAlchemyError: If the database insertion fails.
        """

        dataframe = self.transform(dataframe, KNA1_MAPPING)
        dataframe = self.transform_dates(dataframe)

        # Convertir NaN / NaT a None real para PostgreSQL
        dataframe = dataframe.astype(object).where(pd.notnull(dataframe), None)
        records = dataframe.to_dict(orient="records")

        self.validate_lengths(dataframe)

        LOGGER.info("Preparing KNA1 insertion. Records: %s", len(records))

        sql = """
                INSERT INTO kna1 (
                    kunnr,
                    land1,
                    name1,
                    ort01,
                    pstlz,
                    regio,
                    aufsd,
                    sortl,
                    stras,
                    telf1,
                    name2,
                    anred,
                    erdat,
                    ernam,
                    ktokd,
                    faksd,
                    spras,
                    stcd1,
                    kokrs,
                    stceg,
                    stcd5
                )
                VALUES (
                    :kunnr,
                    :land1,
                    :name1,
                    :ort01,
                    :pstlz,
                    :regio,
                    :aufsd,
                    :sortl,
                    :stras,
                    :telf1,
                    :name2,
                    :anred,
                    :erdat,
                    :ernam,
                    :ktokd,
                    :faksd,
                    :spras,
                    :stcd1,
                    :kokrs,
                    :stceg,
                    :stcd5
                )
                ON CONFLICT (kunnr) DO UPDATE SET
                    land1 = EXCLUDED.land1,
                    name1 = EXCLUDED.name1,
                    ort01 = EXCLUDED.ort01,
                    pstlz = EXCLUDED.pstlz,
                    regio = EXCLUDED.regio,
                    aufsd = EXCLUDED.aufsd,
                    sortl = EXCLUDED.sortl,
                    stras = EXCLUDED.stras,
                    telf1 = EXCLUDED.telf1,
                    name2 = EXCLUDED.name2,
                    anred = EXCLUDED.anred,
                    erdat = EXCLUDED.erdat,
                    ernam = EXCLUDED.ernam,
                    ktokd = EXCLUDED.ktokd,
                    faksd = EXCLUDED.faksd,
                    spras = EXCLUDED.spras,
                    stcd1 = EXCLUDED.stcd1,
                    kokrs = EXCLUDED.kokrs,
                    stceg = EXCLUDED.stceg,
                    stcd5 = EXCLUDED.stcd5
            """

        with self.database.engine.begin() as connection:

            try:
                connection.execute(text(sql), records)

            except Exception as e:

                LOGGER.error("Error inserting KNA1 data in batch")

                self.debug_record_lengths(records[0])

                raise e

        LOGGER.info("KNA1 insertion completed successfully")

    def validate_lengths(self, dataframe):

        limits = {
            "kunnr": 10,
            "land1": 3,
            "name1": 35,
            "ort01": 35,
            "pstlz": 10,
            "regio": 3,
            "aufsd": 2,
            "sortl": 10,
            "stras": 35,
            "telf1": 16,
            "name2": 35,
            "anred": 15,
            "ernam": 12,
            "ktokd": 4,
            "faksd": 2,
            "spras": 2,
            "stcd1": 16,
            "kokrs": 4,
            "stceg": 20,
            "stcd5": 16,
        }

        for field, size in limits.items():

            invalid = dataframe[
                dataframe[field].notna()
                & (dataframe[field].astype(str).str.len() > size)
            ]

            if not invalid.empty:
                LOGGER.error("Field %s exceeds limit %s", field, size)

                LOGGER.error(invalid[[field]].to_dict())

                raise ValueError(f"{field} exceeds maximum length {size}")

    def transform_dates(self, dataframe: pd.DataFrame) -> pd.DataFrame:

        dataframe["erdat"] = pd.to_datetime(dataframe["erdat"], errors="coerce")

        dataframe["erdat"] = dataframe["erdat"].where(dataframe["erdat"].notna(), None)

        return dataframe

    def debug_record_lengths(self, record):
        limits = {
            "kunnr": 10,
            "land1": 3,
            "name1": 35,
            "ort01": 35,
            "pstlz": 10,
            "regio": 3,
            "aufsd": 2,
            "sortl": 10,
            "stras": 35,
            "telf1": 16,
            "name2": 35,
            "anred": 15,
            "ernam": 12,
            "ktokd": 4,
            "faksd": 2,
            "spras": 2,
            "stcd1": 16,
            "kokrs": 4,
            "stceg": 20,
            "stcd5": 16,
        }

        for field, value in record.items():
            if value is not None:
                length = len(str(value))
                limit = limits.get(field)

                LOGGER.error(
                    "%s -> value=%r length=%s limit=%s", field, value, length, limit
                )

                if limit and length > limit:
                    LOGGER.error("!!! FIELD EXCEEDS LIMIT: %s", field)
