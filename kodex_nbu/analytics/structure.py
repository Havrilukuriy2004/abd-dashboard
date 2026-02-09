from __future__ import annotations

import pandas as pd


def structure_snapshot(df: pd.DataFrame, id_api_list: list[str], asof: pd.Timestamp | None = None) -> pd.DataFrame:
    """Builds a structure table for a list of IDs at a specific date."""
    if df.empty or not id_api_list:
        return pd.DataFrame(columns=["dt", "id_api", "value", "share_pct"])
    if asof is None:
        asof = df["dt"].max()
    snap = df.loc[(df["dt"] == asof) & (df["id_api"].isin(id_api_list)), ["dt", "id_api", "value"]].copy()
    if snap.empty:
        return pd.DataFrame(columns=["dt", "id_api", "value", "share_pct"])
    snap["value"] = pd.to_numeric(snap["value"], errors="coerce")
    snap = snap.groupby(["dt", "id_api"], as_index=False)["value"].sum()
    total = snap["value"].sum()
    if total != 0:
        snap["share_pct"] = (snap["value"] / total) * 100.0
    else:
        snap["share_pct"] = 0.0
    return snap.sort_values("value", ascending=False)
