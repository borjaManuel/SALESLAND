import pandas as pd
from mappings.lfb1_mapping import LFB1_MAPPING
from sqlalchemy import text

from database.connection import Database
from loaders.base_loader import BaseLoader
from logger.logger import Logger

LOGGER = Logger.get_logger(__name__)


class Lfb1Loader(BaseLoader):
    """
    Loader responsible for importing LFB1 master data into PostgreSQL.
    """

    def __init__(self, database: Database):
        self.database = database

    def load(self, dataframe: pd.DataFrame):

        dataframe = self.transform(dataframe, LFB1_MAPPING)
        dataframe = self.transform_dates(dataframe)

        dataframe = dataframe.astype(object).where(pd.notnull(dataframe), None)

        self.validate_lengths(dataframe)

        records = dataframe.to_dict(orient="records")

        LOGGER.info("Preparing LFB1 insertion. Records: %s", len(records))

        sql = """
            INSERT INTO lfb1 (
                lifnr,
                bukrs,
                pernr,
                erdat,
                ernam,
                sperr,
                loevm,
                zuawa,
                akont,
                zwels,
                zahls,
                zterm,
                qland,
                qsskz
            )
            VALUES (
                :lifnr,
                :bukrs,
                :pernr,
                :erdat,
                :ernam,
                :sperr,
                :loevm,
                :zuawa,
                :akont,
                :zwels,
                :zahls,
                :zterm,
                :qland,
                :qsskz
            )
        """

        with self.database.engine.begin() as connection:
            connection.execute(text(sql), records)

        LOGGER.info("LFB1 insertion completed successfully")

    def validate_lengths(self, dataframe: pd.DataFrame):

        limits = {
            "lifnr": 10,
            "bukrs": 4,
            "pernr": 8,
            "ernam": 12,
            "sperr": 1,
            "loevm": 1,
            "zuawa": 3,
            "akont": 10,
            "zwels": 10,
            "zahls": 1,
            "zterm": 4,
            "qland": 3,
            "qsskz": 3,
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
