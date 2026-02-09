from __future__ import annotations

from typing import Iterable

import pandas as pd

from kodex_nbu.client import NBUOpenDataClient, NBUApiError


def detect_bank_dimension(
    client: NBUOpenDataClient,
    dimensions: Iterable[str],
    date_yyyymmdd: str | None = None,
) -> list[dict]:
    """Scores dimensions to guess which one represents banks."""
    results: list[dict] = []
    for dim in dimensions:
        dim = str(dim).strip()
        if not dim:
            continue
        try:
            values = client.dimension_values(dim, date=date_yyyymmdd)
        except NBUApiError:
            values = []
        df_vals = pd.DataFrame(values or [])
        if df_vals.empty:
            results.append({"dimensionkod": dim, "values_count": 0, "score": 0, "sample": None})
            continue
        sample_txt = df_vals.get("txt", pd.Series(dtype=str)).dropna().head(3).tolist()
        count = len(df_vals)
        score = 0
        if any("банк" in str(t).lower() or "bank" in str(t).lower() for t in sample_txt):
            score += 3
        if 5 <= count <= 500:
            score += 2
        if count > 500:
            score -= 1
        if dim.lower().startswith("bank"):
            score += 1
        results.append(
            {
                "dimensionkod": dim,
                "values_count": count,
                "score": score,
                "sample": ", ".join(str(s) for s in sample_txt),
            }
        )
    return sorted(results, key=lambda x: x["score"], reverse=True)


def auto_structure_ids(df: pd.DataFrame, prefix: str, top_n: int = 12) -> list[str]:
    """Auto-selects top-N id_api items by latest-date value for a given prefix."""
    if df.empty:
        return []
    prefix = str(prefix)
    asof = df["dt"].max()
    snap = df.loc[(df["dt"] == asof) & (df["id_api"].str.startswith(prefix, na=False)), ["id_api", "value"]].copy()
    if snap.empty:
        return []
    snap["value"] = pd.to_numeric(snap["value"], errors="coerce")
    snap = snap.dropna(subset=["value"])
    snap = snap.groupby("id_api", as_index=False)["value"].sum()
    snap = snap.sort_values("value", ascending=False)
    return snap.head(top_n)["id_api"].tolist()
