from __future__ import annotations
import pandas as pd

def peer_table(snapshot_all_banks: pd.DataFrame, bank_value: str, metric_id_api: str) -> pd.DataFrame:
    """Builds peer comparison for one metric at a given date.

    Input snapshot_all_banks columns:
    - bank (dimension column) + id_api + value
    - dt (optional, kept if present)

    Output:
    - bank, value, rank, percentile
    """
    if snapshot_all_banks.empty:
        return pd.DataFrame(columns=["bank", "value", "rank", "percentile"])

    df = snapshot_all_banks.loc[snapshot_all_banks["id_api"] == metric_id_api].copy()
    if df.empty:
        return pd.DataFrame(columns=["bank", "value", "rank", "percentile"])

    # Require a 'bank' column already normalized by caller
    df = df.dropna(subset=["bank", "value"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"])

    df = df.sort_values("value", ascending=False).reset_index(drop=True)
    df["rank"] = df["value"].rank(method="min", ascending=False).astype(int)
    n = len(df)
    df["percentile"] = (1.0 - (df["rank"] - 1) / max(n - 1, 1)) * 100.0

    # highlight selected bank
    df["is_selected"] = df["bank"].astype(str) == str(bank_value)
    return df
