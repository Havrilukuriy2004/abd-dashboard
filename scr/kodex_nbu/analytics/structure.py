from __future__ import annotations
import pandas as pd

def structure_snapshot(df: pd.DataFrame, id_apis: list[str], asof: pd.Timestamp | None = None) -> pd.DataFrame:
    if df.empty or not id_apis:
        return pd.DataFrame(columns=["dt","id_api","value","share"])
    if asof is None:
        asof = df["dt"].max()
    snap = df[(df["dt"] == asof) & (df["id_api"].isin(id_apis))].copy()
    if snap.empty:
        return pd.DataFrame(columns=["dt","id_api","value","share"])
    snap = snap.groupby(["dt","id_api"], as_index=False)["value"].sum()
    total = float(snap["value"].sum()) if snap["value"].notna().any() else 0.0
    snap["share"] = snap["value"]/total if total != 0 else 0.0
    return snap.sort_values("value", ascending=False)
