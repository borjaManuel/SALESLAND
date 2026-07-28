from datetime import date, datetime

import pandas as pd
from sqlalchemy import text

from database.connection import Database
from loaders.base_loader import BaseLoader
from logger.logger import Logger
from mappings.proj_mapping import PROJ_MAPPING

LOGGER = Logger.get_logger(__name__)


class ProjLoader(BaseLoader):

    def __init__(self, database: Database):
        self.database = database

    def load(self, dataframe):

        dataframe = self.transform(dataframe, PROJ_MAPPING)

        dataframe = self.transform_dates(dataframe)

        dataframe = dataframe.astype(object).where(pd.notnull(dataframe), None)

        self.validate_lengths(dataframe)

        records = dataframe.to_dict(orient="records")

        LOGGER.info("Preparing PROJ insertion. Records: %s", len(records))

        sql = """
            INSERT INTO proj (
                pspid,
                post1,
                vbukr,
                waers,
                plfaz,
                plsez,
                profl
            )
            VALUES (
                :pspid,
                :post1,
                :vbukr,
                :waers,
                :plfaz,
                :plsez,
                :profl
            )
            ON CONFLICT (pspid) DO UPDATE SET
                post1 = EXCLUDED.post1,
                vbukr = EXCLUDED.vbukr,
                waers = EXCLUDED.waers,
                plfaz = EXCLUDED.plfaz,
                plsez = EXCLUDED.plsez,
                profl = EXCLUDED.profl
        """

        with self.database.engine.begin() as connection:
            connection.execute(text(sql), records)

        LOGGER.info("PROJ insertion completed successfully")

    def validate_lengths(self, dataframe):

        limits = {
            "pspid": 24,
            "post1": 40,
            "vbukr": 4,
            "waers": 5,
            "profl": 7,
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

        dataframe["plfaz"] = pd.to_datetime(
            dataframe["plfaz"],
            errors="coerce",
        ).dt.date

        dataframe["plsez"] = pd.to_datetime(
            dataframe["plsez"],
            errors="coerce",
        ).dt.date

        dataframe = dataframe.astype(object).where(pd.notnull(dataframe), None)

        return dataframe
