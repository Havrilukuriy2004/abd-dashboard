from __future__ import annotations
import pandas as pd

def data_quality_report(df: pd.DataFrame) -> pd.DataFrame:
    """Simple quality report: missing rates, date range, duplicates."""
    if df.empty:
        return pd.DataFrame([{
            "rows": 0,
            "date_min": None,
            "date_max": None,
            "missing_dt_pct": None,
            "missing_value_pct": None,
            "duplicate_rows": None,
        }])
    rows = len(df)
    miss_dt = df["dt"].isna().mean() * 100
    miss_val = df["value"].isna().mean() * 100
    dup = df.duplicated().sum()
    return pd.DataFrame([{
        "rows": rows,
        "date_min": str(df["dt"].min().date()) if pd.notna(df["dt"].min()) else None,
        "date_max": str(df["dt"].max().date()) if pd.notna(df["dt"].max()) else None,
        "missing_dt_pct": round(miss_dt, 2),
        "missing_value_pct": round(miss_val, 2),
        "duplicate_rows": int(dup),
    }])
