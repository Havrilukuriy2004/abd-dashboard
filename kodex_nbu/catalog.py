from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
import pandas as pd

@dataclass(frozen=True)
class DatasetInfo:
    txt: str
    apikod: str
    periods: str | None
    dimensions: str | None
    entrydate: str | None

def datasets_to_df(datasets: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(datasets)
    # normalize common columns
    for c in ["txt", "apikod", "periods", "dimensions", "entrydate"]:
        if c not in df.columns:
            df[c] = None
    return df[["txt", "apikod", "periods", "dimensions", "entrydate"]].copy()

def search_datasets(df: pd.DataFrame, query: str) -> pd.DataFrame:
    q = (query or "").strip().lower()
    if not q:
        return df
    mask = df["txt"].fillna("").str.lower().str.contains(q) | df["apikod"].fillna("").str.lower().str.contains(q)
    return df.loc[mask].copy()

def parse_dimensions(dimensions_field: str | None) -> list[str]:
    if not dimensions_field:
        return []
    return [x.strip() for x in str(dimensions_field).split(",") if x.strip()]
