import pandas as pd
from sqlalchemy import text

from database.connection import Database
from loaders.base_loader import BaseLoader
from logger.logger import Logger
from mappings.t007a_mapping import T007A_MAPPING

LOGGER = Logger.get_logger(__name__)


class T007aLoader(BaseLoader):

    def __init__(self, database: Database):
        self.database = database

    def load(self, dataframe):

        dataframe = self.transform(dataframe, T007A_MAPPING)

        dataframe = dataframe.astype(object).where(pd.notnull(dataframe), None)

        self.validate_lengths(dataframe)

        records = dataframe.to_dict(orient="records")

        LOGGER.info("Preparing T007A insertion. Records: %s", len(records))

        sql = """
            INSERT INTO t007a (
                kalsm,
                mwskz,
                mwskt,
                egbld,
                text1
            )
            VALUES (
                :kalsm,
                :mwskz,
                :mwskt,
                :egbld,
                :text1
            )
            ON CONFLICT (kalsm, mwskz) DO UPDATE SET
                mwskt = EXCLUDED.mwskt,
                egbld = EXCLUDED.egbld,
                text1 = EXCLUDED.text1
        """

        with self.database.engine.begin() as connection:
            connection.execute(text(sql), records)

        LOGGER.info("T007A insertion completed successfully")

    def validate_lengths(self, dataframe):

        limits = {
            "kalsm": 6,
            "mwskz": 2,
            "mwskt": 1,
            "egbld": 1,
            "text1": 50,
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
