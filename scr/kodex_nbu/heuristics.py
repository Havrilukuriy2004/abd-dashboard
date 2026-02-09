from __future__ import annotations
import re
import pandas as pd

BANK_HINT_RE = re.compile(r"(банк|bank|jsc|\bat\b|акц|публ|pjsc)", re.IGNORECASE)

def guess_frequency(dts: pd.Series) -> str:
    dts = pd.to_datetime(dts, errors="coerce").dropna().sort_values()
    if len(dts) < 3:
        return "unknown"
    gaps = dts.diff().dropna().dt.days
    med = float(gaps.median())
    if 20 <= med <= 45:
        return "monthly"
    if 70 <= med <= 120:
        return "quarterly"
    if 300 <= med <= 430:
        return "annual"
    return "unknown"

def detect_bank_dimension(client, dimensionkods: list[str], date_yyyymmdd: str | None, sample_n: int = 50) -> list[dict]:
    candidates = []
    for dk in dimensionkods:
        try:
            vals = client.dimension_values(dk, date=date_yyyymmdd)
        except Exception:
            continue
        if not vals:
            continue
        texts = [str(r.get("txt","")) for r in vals[:sample_n] if r.get("txt") is not None]
        if not texts:
            continue
        hit = sum(bool(BANK_HINT_RE.search(t)) for t in texts)
        score = hit / max(len(texts), 1)
        candidates.append({"dimensionkod": dk, "sample_size": len(texts), "hit_rate": round(score,3), "example": texts[0][:80]})
    candidates.sort(key=lambda x: x["hit_rate"], reverse=True)
    return candidates

def auto_structure_ids(df: pd.DataFrame, prefix: str, top_n: int = 12) -> list[str]:
    if df.empty:
        return []
    sub = df[df["id_api"].astype(str).str.startswith(prefix)].copy()
    if sub.empty:
        return []
    asof = sub["dt"].max()
    snap = sub[sub["dt"] == asof].groupby("id_api", as_index=False)["value"].sum()
    snap["abs"] = snap["value"].abs()
    snap = snap.sort_values("abs", ascending=False).head(top_n)
    return snap["id_api"].tolist()
