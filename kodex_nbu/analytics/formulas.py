from __future__ import annotations

import pandas as pd

FORMULA_LIBRARY = [
    {
        "name": "Equity Ratio",
        "numerator": "BS1_CapitalTotal",
        "denominator": "BS1_AssetsTotal",
        "unit": "%",
        "description": "Capital / Assets",
    },
    {
        "name": "Liabilities Ratio",
        "numerator": "BS1_LiabTotal",
        "denominator": "BS1_AssetsTotal",
        "unit": "%",
        "description": "Liabilities / Assets",
    },
    {
        "name": "ROA",
        "numerator": "BS2_NetProfitLoss",
        "denominator": "BS1_AssetsTotal",
        "unit": "%",
        "description": "Net Profit / Assets",
    },
    {
        "name": "ROE",
        "numerator": "BS2_NetProfitLoss",
        "denominator": "BS1_CapitalTotal",
        "unit": "%",
        "description": "Net Profit / Capital",
    },
    {
        "name": "Net Interest Margin",
        "numerator": "BS1_NetInterIncomeCosts",
        "denominator": "BS1_AssetsTotal",
        "unit": "%",
        "description": "Net Interest Income / Assets",
    },
    {
        "name": "Leverage",
        "numerator": "BS1_AssetsTotal",
        "denominator": "BS1_CapitalTotal",
        "unit": "x",
        "description": "Assets / Capital",
    },
]


def formula_kpis(ts: pd.DataFrame) -> pd.DataFrame:
    """Derives formula KPIs from the latest available snapshot."""
    if ts.empty:
        return pd.DataFrame(columns=["asof", "metric", "value", "unit", "description"])
    asof = ts["dt"].max()
    snap = ts.loc[ts["dt"] == asof, ["id_api", "value"]].copy()
    snap["value"] = pd.to_numeric(snap["value"], errors="coerce")
    pivot = snap.set_index("id_api")["value"].to_dict()

    rows: list[dict] = []
    for formula in FORMULA_LIBRARY:
        num = pivot.get(formula["numerator"])
        den = pivot.get(formula["denominator"])
        if num is None or den is None or den == 0 or pd.isna(den) or pd.isna(num):
            continue
        value = (num / den) * (100.0 if formula["unit"] == "%" else 1.0)
        rows.append(
            {
                "asof": asof,
                "metric": formula["name"],
                "value": float(value),
                "unit": formula["unit"],
                "description": formula["description"],
            }
        )
    return pd.DataFrame(rows)
