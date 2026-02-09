from __future__ import annotations
import pandas as pd
from kodex_nbu.heuristics import guess_frequency

def _get_series(ts: pd.DataFrame, id_api: str) -> pd.Series:
    s = ts.loc[ts["id_api"] == id_api].set_index("dt")["value"].sort_index()
    return pd.to_numeric(s, errors="coerce")

def formula_kpis(ts: pd.DataFrame) -> pd.DataFrame:
    if ts.empty:
        return pd.DataFrame(columns=["kpi","value","asof","note"])
    freq = guess_frequency(ts["dt"])
    yoy_lag = {"monthly":12, "quarterly":4, "annual":1}.get(freq, 1)
    assets = _get_series(ts, "BS1_AssetsTotal")
    equity = _get_series(ts, "BS1_CapitalTotal")
    profit = _get_series(ts, "BS2_NetProfitLoss")
    asof = ts["dt"].max()
    out = []

    def last(s):
        s2 = s.dropna()
        return float(s2.iloc[-1]) if len(s2) else None

    def avg_last2(s):
        s2 = s.dropna().tail(2)
        if len(s2) == 0:
            return None
        if len(s2) == 1:
            return float(s2.iloc[0])
        return float(s2.mean())

    A = last(assets)
    E = last(equity)
    P = last(profit)
    Aavg = avg_last2(assets)
    Eavg = avg_last2(equity)

    out.append({"kpi":"Equity ratio", "value": (E/A) if (A not in (None,0) and E is not None) else None, "asof":asof, "note":"E/A"})
    out.append({"kpi":"ROA", "value": (P/Aavg) if (Aavg not in (None,0) and P is not None) else None, "asof":asof, "note":"P/avg(A)"})
    out.append({"kpi":"ROE", "value": (P/Eavg) if (Eavg not in (None,0) and P is not None) else None, "asof":asof, "note":"P/avg(E)"})

    def yoy_growth(s):
        s2 = s.dropna()
        if len(s2) <= yoy_lag:
            return None
        v_now = s2.iloc[-1]
        v_prev = s2.iloc[-1-yoy_lag]
        return None if v_prev == 0 else float(v_now/v_prev - 1)

    out.append({"kpi":"Assets YoY growth", "value": yoy_growth(assets), "asof":asof, "note": f"lag={yoy_lag} ({freq})"})
    out.append({"kpi":"Profit YoY growth", "value": yoy_growth(profit), "asof":asof, "note": f"lag={yoy_lag} ({freq})"})

    assets_clean = assets.dropna()
    if len(assets_clean) >= 2 and assets_clean.iloc[0] != 0:
        years = (assets_clean.index.max() - assets_clean.index.min()).days / 365.25
        cagr = float((assets_clean.iloc[-1]/assets_clean.iloc[0]) ** (1/years) - 1) if years > 0 else None
    else:
        cagr = None
    out.append({"kpi":"Assets CAGR", "value": cagr, "asof":asof, "note":"full window"})
    return pd.DataFrame(out)
