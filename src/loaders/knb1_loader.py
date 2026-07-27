import pandas as pd
from mappings.knb1_mapping import KNB1_MAPPING
from sqlalchemy import text

from database.connection import Database
from loaders.base_loader import BaseLoader
from logger.logger import Logger

LOGGER = Logger.get_logger(__name__)


class Knb1Loader(BaseLoader):
    """
    Loader responsible for importing KNB1 master data into PostgreSQL.

    This loader transforms Excel data according to the KNB1 field mapping
    and inserts the resulting records into the target database table.
    """

    def __init__(self, database: Database):
        self.database = database

    def load(self, dataframe: pd.DataFrame):
        """
        Loads KNB1 records into the PostgreSQL database.
        """

        dataframe = self.transform(dataframe, KNB1_MAPPING)
        dataframe = self.transform_dates(dataframe)

        # Convert NaN / NaT to None for PostgreSQL
        dataframe = dataframe.astype(object).where(pd.notnull(dataframe), None)

        self.validate_lengths(dataframe)

        records = dataframe.to_dict(orient="records")

        LOGGER.info("Preparing KNB1 insertion. Records: %s", len(records))

        sql = """
            INSERT INTO knb1 (
                kunnr,
                bukrs,
                akont,
                zwels,
                zterm,
                ernam,
                sperr,
                loevm,
                erdat
            )
            VALUES (
                :kunnr,
                :bukrs,
                :akont,
                :zwels,
                :zterm,
                :ernam,
                :sperr,
                :loevm,
                :erdat
            )
        """

        with self.database.engine.begin() as connection:
            connection.execute(text(sql), records)

        LOGGER.info("KNB1 insertion completed successfully")

    def validate_lengths(self, dataframe: pd.DataFrame):

        limits = {
            "kunnr": 10,
            "bukrs": 4,
            "akont": 10,
            "zwels": 10,
            "zterm": 4,
            "ernam": 12,
            "sperr": 1,
            "loevm": 1,
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
        """
        Converts KNB1 date fields to datetime.
        """

        dataframe["erdat"] = pd.to_datetime(
            dataframe["erdat"],
            errors="coerce",
            dayfirst=True,
        )

        dataframe["erdat"] = dataframe["erdat"].where(
            dataframe["erdat"].notna(),
            None,
        )

        return dataframe
