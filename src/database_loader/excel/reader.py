import pandas as pd


class ExcelReader:

    def read(self, file_path: str) -> pd.DataFrame:
        return pd.read_excel(file_path, dtype=str)
