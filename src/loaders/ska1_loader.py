import pandas as pd
from mappings.ska1_mapping import SKA1_MAPPING
from sqlalchemy import text

from database.connection import Database
from loaders.base_loader import BaseLoader
from logger.logger import Logger

LOGGER = Logger.get_logger(__name__)


class Ska1Loader(BaseLoader):

    def __init__(self, database: Database):
        self.database = database

    def load(self, dataframe):

        dataframe = self.transform(dataframe, SKA1_MAPPING)
        dataframe = self.transform_dates(dataframe)

        dataframe = dataframe.astype(object).where(pd.notnull(dataframe), None)

        self.validate_lengths(dataframe)

        records = dataframe.to_dict(orient="records")

        LOGGER.info("Preparing SKA1 insertion. Records: %s", len(records))

        sql = """
            INSERT INTO ska1 (
                ktopl,
                saknr,
                xbilk,
                erdat,
                ernam,
                gvtyp,
                ktoks,
                xloev,
                xspea,
                xspeb,
                xspec,
                txt50
            )
            VALUES (
                :ktopl,
                :saknr,
                :xbilk,
                :erdat,
                :ernam,
                :gvtyp,
                :ktoks,
                :xloev,
                :xspea,
                :xspeb,
                :xspec,
                :txt50
            )
        """

        with self.database.engine.begin() as connection:
            connection.execute(text(sql), records)

        LOGGER.info("SKA1 insertion completed successfully")

    def validate_lengths(self, dataframe):

        limits = {
            "ktopl": 4,
            "saknr": 10,
            "xbilk": 1,
            "ernam": 12,
            "gvtyp": 2,
            "ktoks": 4,
            "xloev": 1,
            "xspea": 1,
            "xspeb": 1,
            "xspec": 1,
            "txt50": 50,
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

    def transform_dates(self, dataframe):

        dataframe["erdat"] = pd.to_datetime(
            dataframe["erdat"],
            errors="coerce",
        ).dt.date

        dataframe = dataframe.astype(object).where(pd.notnull(dataframe), None)

        return dataframe
