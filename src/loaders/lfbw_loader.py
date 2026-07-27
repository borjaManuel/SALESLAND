import pandas as pd
from mappings.lfbw_mapping import LFBW_MAPPING
from sqlalchemy import text

from database.connection import Database
from loaders.base_loader import BaseLoader
from logger.logger import Logger

LOGGER = Logger.get_logger(__name__)


class LfbwLoader(BaseLoader):
    """
    Loader responsible for importing LFBW master data into PostgreSQL.
    """

    def __init__(self, database: Database):
        self.database = database

    def load(self, dataframe: pd.DataFrame):

        dataframe = self.transform(dataframe, LFBW_MAPPING)

        dataframe = dataframe.astype(object).where(pd.notnull(dataframe), None)

        self.validate_lengths(dataframe)

        records = dataframe.to_dict(orient="records")

        LOGGER.info("Preparing LFBW insertion. Records: %s", len(records))

        sql = """
            INSERT INTO lfbw (
                lifnr,
                bukrs,
                witht,
                wt_withcd,
                wt_subjct,
                wt_exrt,
                wt_exdf,
                wt_exdt,
                wt_wtexm,
                wt_exrs,
                wt_wtstcd,
                wt_withtr
            )
            VALUES (
                :lifnr,
                :bukrs,
                :witht,
                :wt_withcd,
                :wt_subjct,
                :wt_exrt,
                :wt_exdf,
                :wt_exdt,
                :wt_wtexm,
                :wt_exrs,
                :wt_wtstcd,
                :wt_withtr
            )
        """

        with self.database.engine.begin() as connection:
            connection.execute(text(sql), records)

        LOGGER.info("LFBW insertion completed successfully")

    def validate_lengths(self, dataframe: pd.DataFrame):

        limits = {
            "lifnr": 10,
            "bukrs": 4,
            "witht": 2,
            "wt_withcd": 2,
            "wt_subjct": 2,
            "wt_exdf": 8,
            "wt_exdt": 8,
            "wt_wtexm": 15,
            "wt_exrs": 2,
            "wt_wtstcd": 16,
            "wt_withtr": 2,
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
