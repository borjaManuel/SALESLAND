import pandas as pd
from sqlalchemy import text

from database.connection import Database
from loaders.base_loader import BaseLoader
from logger.logger import Logger
from mappings.t059z_mapping import T059Z_MAPPING

LOGGER = Logger.get_logger(__name__)


class T059zLoader(BaseLoader):

    def __init__(self, database: Database):
        self.database = database

    def load(self, dataframe):

        dataframe = self.transform(dataframe, T059Z_MAPPING)

        dataframe = dataframe.astype(object).where(pd.notnull(dataframe), None)
        dataframe["wt_wtreci"] = dataframe["wt_wtreci"].apply(self.normalize_decimal)

        self.validate_lengths(dataframe)

        records = dataframe.to_dict(orient="records")

        LOGGER.info("Preparing T059Z insertion. Records: %s", len(records))

        sql = """
            INSERT INTO t059z (
                land1,
                witht,
                wt_withcd,
                text40,
                wt_qsbase,
                wt_wtreci
            )
            VALUES (
                :land1,
                :witht,
                :wt_withcd,
                :text40,
                :wt_qsbase,
                :wt_wtreci
            )
            ON CONFLICT (land1, witht, wt_withcd) DO UPDATE SET
                text40 = EXCLUDED.text40,
                wt_qsbase = EXCLUDED.wt_qsbase,
                wt_wtreci = EXCLUDED.wt_wtreci
        """

        with self.database.engine.begin() as connection:
            connection.execute(text(sql), records)

        LOGGER.info("T059Z insertion completed successfully")

    def validate_lengths(self, dataframe):

        limits = {
            "land1": 3,
            "witht": 2,
            "wt_withcd": 2,
            "text40": 40,
            "wt_qsbase": 3,
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

    def normalize_decimal(self, value):

        if pd.isna(value):
            return None

        value = str(value).replace(",", ".")

        return round(float(value), 2)
