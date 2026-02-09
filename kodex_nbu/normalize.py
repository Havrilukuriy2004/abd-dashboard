from __future__ import annotations
import pandas as pd

def normalize_records(records: list[dict]) -> pd.DataFrame:
    """Converts raw API JSON records to a tidy DataFrame.

    Expected common fields:
    - dt (date as 'dd.mm.yyyy')
    - id_api
    - value
    plus any number of dimension columns (e.g., s181, k013, ...)
    """
    if not records:
        return pd.DataFrame(columns=["dt", "id_api", "value"])
    df = pd.DataFrame(records).copy()

    # normalize date
    if "dt" in df.columns:
        df["dt"] = pd.to_datetime(df["dt"], format="%d.%m.%Y", errors="coerce")
    else:
        df["dt"] = pd.NaT

    # normalize value
    if "value" in df.columns:
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
    else:
        df["value"] = pd.NA

    # keep id_api if exists
    if "id_api" not in df.columns:
        df["id_api"] = None

    return df

def filter_by_bank(df: pd.DataFrame, bank_dimension_kod: str, bank_value: str) -> pd.DataFrame:
    if not bank_dimension_kod:
        return df.copy()
    if bank_dimension_kod not in df.columns:
        # dataset doesn't contain this dimension; return empty to avoid silent errors
        return df.iloc[0:0].copy()
    return df.loc[df[bank_dimension_kod].astype(str) == str(bank_value)].copy()

def filter_by_id_api(df: pd.DataFrame, id_api_list: list[str]) -> pd.DataFrame:
    if not id_api_list:
        return df.copy()
    return df.loc[df["id_api"].isin(id_api_list)].copy()
