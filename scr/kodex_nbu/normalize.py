from __future__ import annotations
import pandas as pd

def normalize_records(records: list[dict]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=["dt","id_api","value"])
    df = pd.DataFrame(records).copy()
    df["dt"] = pd.to_datetime(df.get("dt"), format="%d.%m.%Y", errors="coerce")
    df["value"] = pd.to_numeric(df.get("value"), errors="coerce")
    if "id_api" not in df.columns:
        df["id_api"] = None
    return df

def filter_by_bank(df: pd.DataFrame, bank_dimension_kod: str, bank_value: str) -> pd.DataFrame:
    if not bank_dimension_kod:
        return df.copy()
    if bank_dimension_kod not in df.columns:
        return df.iloc[0:0].copy()
    return df.loc[df[bank_dimension_kod].astype(str) == str(bank_value)].copy()

def filter_by_id_api(df: pd.DataFrame, id_api_list: list[str]) -> pd.DataFrame:
    if not id_api_list:
        return df.copy()
    return df.loc[df["id_api"].isin(id_api_list)].copy()
