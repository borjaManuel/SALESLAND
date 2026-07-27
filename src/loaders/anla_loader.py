import pandas as pd
from mappings.anla_mapping import ANLA_MAPPING
from sqlalchemy import text

from database.connection import Database
from loaders.base_loader import BaseLoader
from logger.logger import Logger

LOGGER = Logger.get_logger(__name__)


class AnlaLoader(BaseLoader):
    """
    Loader responsible for importing ANLA fixed assets data.
    """

    def __init__(self, database: Database):
        self.database = database

    def load(self, dataframe):

        dataframe = self.transform(dataframe, ANLA_MAPPING)

        dataframe = self.transform_dates(dataframe)

        dataframe = dataframe.astype(object).where(pd.notnull(dataframe), None)

        records = dataframe.to_dict(orient="records")

        self.validate_lengths(dataframe)

        LOGGER.info("Preparing ANLA insertion. Records: %s", len(records))

        sql = """

        INSERT INTO anla (

            bukrs,
            anln1,
            anln2,
            anlkl,
            txt50,
            erdat

        )

        VALUES (

            :bukrs,
            :anln1,
            :anln2,
            :anlkl,
            :txt50,
            :erdat

        )

        """

        with self.database.engine.begin() as connection:

            connection.execute(text(sql), records)

        LOGGER.info("ANLA insertion completed successfully")

    def transform_dates(self, dataframe):

        dataframe["erdat"] = pd.to_datetime(dataframe["erdat"], errors="coerce")

        dataframe["erdat"] = dataframe["erdat"].where(dataframe["erdat"].notna(), None)

        return dataframe

    def validate_lengths(self, dataframe):

        limits = {"bukrs": 4, "anln1": 12, "anln2": 4, "anlkl": 8, "txt50": 50}

        for field, size in limits.items():

            invalid = dataframe[
                dataframe[field].notna()
                & (dataframe[field].astype(str).str.len() > size)
            ]

            if not invalid.empty:

                raise ValueError(f"{field} exceeds maximum length {size}")
