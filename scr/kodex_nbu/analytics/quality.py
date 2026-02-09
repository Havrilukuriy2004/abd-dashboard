from __future__ import annotations
import pandas as pd

def data_quality_report(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame([{"rows":0,"date_min":None,"date_max":None,"missing_dt_pct":None,"missing_value_pct":None,"duplicate_rows":None}])
    return pd.DataFrame([{
        "rows": len(df),
        "date_min": str(df["dt"].min().date()) if pd.notna(df["dt"].min()) else None,
        "date_max": str(df["dt"].max().date()) if pd.notna(df["dt"].max()) else None,
        "missing_dt_pct": round(df["dt"].isna().mean()*100, 2),
        "missing_value_pct": round(df["value"].isna().mean()*100, 2),
        "duplicate_rows": int(df.duplicated().sum()),
    }])
