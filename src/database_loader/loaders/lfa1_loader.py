import pandas as pd
from sqlalchemy import text

from database.connection import Database
from loaders.base_loader import BaseLoader
from logger.logger import Logger
from mappings.lfa1_mapping import LFA1_MAPPING

LOGGER = Logger.get_logger(__name__)


class Lfa1Loader(BaseLoader):
    """
    Loader responsible for importing LFA1 master data into PostgreSQL.
    """

    def __init__(self, database: Database):
        self.database = database

    def load(self, dataframe: pd.DataFrame):

        dataframe = self.transform(dataframe, LFA1_MAPPING)
        dataframe = self.transform_dates(dataframe)

        dataframe = dataframe.astype(object).where(pd.notnull(dataframe), None)

        self.validate_lengths(dataframe)

        records = dataframe.to_dict(orient="records")

        LOGGER.info("Preparing LFA1 insertion. Records: %s", len(records))

        sql = """
            INSERT INTO lfa1 (
                lifnr,
                land1,
                name1,
                ort01,
                pstlz,
                regio,
                stras,
                erdat,
                ernam,
                ktokk,
                spras,
                stcd1,
                stceg
            )
            VALUES (
                :lifnr,
                :land1,
                :name1,
                :ort01,
                :pstlz,
                :regio,
                :stras,
                :erdat,
                :ernam,
                :ktokk,
                :spras,
                :stcd1,
                :stceg
            )
            ON CONFLICT (lifnr) DO UPDATE SET
                land1 = EXCLUDED.land1,
                name1 = EXCLUDED.name1,
                ort01 = EXCLUDED.ort01,
                pstlz = EXCLUDED.pstlz,
                regio = EXCLUDED.regio,
                stras = EXCLUDED.stras,
                erdat = EXCLUDED.erdat,
                ernam = EXCLUDED.ernam,
                ktokk = EXCLUDED.ktokk,
                spras = EXCLUDED.spras,
                stcd1 = EXCLUDED.stcd1,
                stceg = EXCLUDED.stceg
        """

        with self.database.engine.begin() as connection:
            connection.execute(text(sql), records)

        LOGGER.info("LFA1 insertion completed successfully")

    def validate_lengths(self, dataframe: pd.DataFrame):

        limits = {
            "lifnr": 10,
            "land1": 3,
            "name1": 35,
            "ort01": 35,
            "pstlz": 10,
            "regio": 3,
            "stras": 35,
            "ernam": 12,
            "ktokk": 4,
            "spras": 3,
            "stcd1": 16,
            "stceg": 20,
        }

        for field, size in limits.items():

            invalid = dataframe[
                dataframe[field].notna()
                & (dataframe[field].astype(str).str.len() > size)
            ]

            if not invalid.empty:

                LOGGER.error(
                    "Field '%s' exceeds maximum length %s",
                    field,
                    size,
                )

                LOGGER.error(invalid[[field]].to_dict())

                raise ValueError(f"{field} exceeds maximum length {size}")

    def transform_dates(self, dataframe: pd.DataFrame) -> pd.DataFrame:

        dataframe["erdat"] = pd.to_datetime(
            dataframe["erdat"],
            errors="coerce",
        )

        dataframe["erdat"] = dataframe["erdat"].where(
            dataframe["erdat"].notna(),
            None,
        )

        return dataframe
