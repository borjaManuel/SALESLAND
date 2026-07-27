import pandas as pd


class BaseLoader:
    """
    Base class providing common functionality for data loaders.

    This class contains reusable transformation methods that can be
    extended by specific loaders to process and prepare data before
    loading it into the target database.
    """

    def transform(self, dataframe: pd.DataFrame, mapping: dict) -> pd.DataFrame:
        """
        Transforms a DataFrame according to the provided field mapping.

        The transformation renames the DataFrame columns using the specified
        mapping and returns only the columns required by the target structure.

        Args:
            dataframe (pd.DataFrame): Source DataFrame containing the original
                data structure.
            mapping (dict): Dictionary mapping source column names to target
                column names.

        Returns:
            pd.DataFrame: Transformed DataFrame ready for database insertion.
        """
        dataframe = dataframe.rename(columns=mapping)
        dataframe = dataframe[list(mapping.values())]

        return dataframe[list(mapping.values())]
