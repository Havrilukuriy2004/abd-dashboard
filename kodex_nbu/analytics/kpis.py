from __future__ import annotations
import pandas as pd

def kpi_snapshot(df: pd.DataFrame, asof: pd.Timestamp | None = None) -> pd.DataFrame:
    """Returns a single-date KPI table: id_api, value.

    If asof is None: uses max date in df.
    """
    if df.empty:
        return pd.DataFrame(columns=["dt", "id_api", "value"])
    if asof is None:
        asof = df["dt"].max()
    snap = df.loc[df["dt"] == asof, ["dt", "id_api", "value"]].copy()
    # If duplicates exist (multiple dims), aggregate by sum (safe default; can change to last/mean)
    snap = snap.groupby(["dt", "id_api"], as_index=False)["value"].sum()
    return snap.sort_values("id_api")

def kpi_timeseries(df: pd.DataFrame) -> pd.DataFrame:
    """Returns KPI time series: dt, id_api, value (aggregated by sum)."""
    if df.empty:
        return pd.DataFrame(columns=["dt", "id_api", "value"])
    ts = df.loc[:, ["dt", "id_api", "value"]].copy()
    ts = ts.groupby(["dt", "id_api"], as_index=False)["value"].sum()
    return ts.sort_values(["id_api", "dt"])


def kpi_changes(df: pd.DataFrame, periods: list[int] | None = None) -> pd.DataFrame:
    """Computes latest-period deltas and growth by id_api."""
    if df.empty:
        return pd.DataFrame(columns=["dt", "id_api", "value"])
    periods = periods or [1, 2, 4, 12]
    ts = df.loc[:, ["dt", "id_api", "value"]].copy()
    ts = ts.groupby(["dt", "id_api"], as_index=False)["value"].sum()
    ts = ts.sort_values(["id_api", "dt"])
    for p in periods:
        ts[f"value_prev_{p}"] = ts.groupby("id_api")["value"].shift(p)
        ts[f"delta_{p}"] = ts["value"] - ts[f"value_prev_{p}"]
        ts[f"pct_{p}"] = (ts[f"delta_{p}"] / ts[f"value_prev_{p}"]) * 100.0
    latest = ts.groupby("id_api", as_index=False).tail(1)
    return latest.sort_values("id_api")
