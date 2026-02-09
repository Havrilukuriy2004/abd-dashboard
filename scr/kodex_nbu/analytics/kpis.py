from __future__ import annotations
import pandas as pd

def kpi_snapshot(df: pd.DataFrame, asof: pd.Timestamp | None = None) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["dt","id_api","value"])
    if asof is None:
        asof = df["dt"].max()
    snap = df.loc[df["dt"] == asof, ["dt","id_api","value"]].copy()
    return snap.groupby(["dt","id_api"], as_index=False)["value"].sum().sort_values("id_api")

def kpi_timeseries(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["dt","id_api","value"])
    ts = df.loc[:, ["dt","id_api","value"]].copy()
    return ts.groupby(["dt","id_api"], as_index=False)["value"].sum().sort_values(["id_api","dt"])
