from __future__ import annotations

# Fix for Streamlit Cloud: make `src/` importable
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import datetime as dt
import pandas as pd
import plotly.express as px
import streamlit as st

from kodex_nbu.config import load_config
from kodex_nbu.client import NBUOpenDataClient
from kodex_nbu.catalog import datasets_to_df, search_datasets, parse_dimensions
from kodex_nbu.normalize import normalize_records, filter_by_bank, filter_by_id_api
from kodex_nbu.analytics.kpis import kpi_snapshot, kpi_timeseries
from kodex_nbu.analytics.quality import data_quality_report
from kodex_nbu.analytics.peer import peer_table
from kodex_nbu.analytics.formulas import formula_kpis
from kodex_nbu.analytics.structure import structure_snapshot
from kodex_nbu.heuristics import detect_bank_dimension, auto_structure_ids

st.set_page_config(page_title="Kodex — NBU Bank Dashboard", layout="wide")
CFG = load_config(ROOT / "config" / "config.yaml")
client = NBUOpenDataClient(base_url=CFG.nbu_api_base, use_cache=True)

def yyyymmdd(d: dt.date) -> str:
    return d.strftime("%Y%m%d")

def default_start_end(lookback_days: int):
    today = dt.date.today()
    start = today - dt.timedelta(days=lookback_days)
    return start, today

@st.cache_data(show_spinner=False, ttl=3600)
def cached_list_datasets():
    return client.list_datasets()

@st.cache_data(show_spinner=False, ttl=3600)
def cached_list_dimensions():
    return client.list_dimensions()

@st.cache_data(show_spinner=False, ttl=3600)
def cached_dimension_values(dimensionkod: str, date: str | None):
    return client.dimension_values(dimensionkod, date=date)

st.title("Kodex — Dashboard по вибору банку (NBU OpenData)")

tab_catalog, tab_select, tab_profile = st.tabs(["Catalog", "Bank selection", "Bank profile"])

with tab_catalog:
    st.subheader("1) Catalog: знайди `apikod` та `dimensions`")
    df_ds = datasets_to_df(cached_list_datasets())
    q = st.text_input("Пошук (баланс / доходи / витрати / banks / BS)", value="")
    df_view = search_datasets(df_ds, q)
    st.dataframe(df_view, use_container_width=True, height=340)

    st.markdown("---")
    st.subheader("Directory of dimensions (dimensionkod)")
    st.dataframe(pd.DataFrame(cached_list_dimensions()), use_container_width=True, height=240)

with tab_select:
    st.subheader("2) Bank selection: вибір банку + ранжування")
    apikod = st.text_input("apikod", value=CFG.apikod_bs)
    bank_dim = st.text_input("bank dimensionkod (manual або auto)", value=CFG.bank_dimension_kod)

    start_d, end_d = default_start_end(CFG.default_lookback_days)
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        start = st.date_input("Start", value=start_d)
    with c2:
        end = st.date_input("End", value=end_d)
    with c3:
        period = st.text_input("period (optional)", value="")

    if apikod and st.button("Auto-detect bank dimension"):
        df = datasets_to_df(cached_list_datasets())
        row = df.loc[df["apikod"].astype(str) == str(apikod)]
        if row.empty:
            st.error("Unknown apikod. Use Catalog tab.")
        else:
            dims = parse_dimensions(row.iloc[0]["dimensions"])
            cand = detect_bank_dimension(client, dims, date_yyyymmdd=yyyymmdd(end))
            st.dataframe(pd.DataFrame(cand), use_container_width=True)

    banks = []
    if apikod and bank_dim:
        dim_vals = cached_dimension_values(bank_dim, date=yyyymmdd(end))
        for r in dim_vals or []:
            if bank_dim in r:
                banks.append({"bank": str(r.get(bank_dim)), "txt": r.get("txt")})
    df_banks = pd.DataFrame(banks)
    bank_value = st.selectbox("Bank", options=df_banks["bank"].tolist() if not df_banks.empty else [])

    if apikod and bank_dim and bank_value:
        kpi_list = (CFG.kpi_sets.get("core_bs1", []) + CFG.kpi_sets.get("core_bs2", []))
        params = {"start": yyyymmdd(start), "end": yyyymmdd(end)}
        if period:
            params["period"] = period
        with st.spinner("Loading data..."):
            raw = client.fetch_dataset_all(apikod, params=params, page_size=5000)
        df_raw = normalize_records(raw)
        df_kpi = filter_by_id_api(df_raw, kpi_list)
        asof = df_kpi["dt"].max() if not df_kpi.empty else None
        if asof is None:
            st.error("No data returned. Check parameters.")
        else:
            metric = "BS1_AssetsTotal" if "BS1_AssetsTotal" in kpi_list else kpi_list[0]
            snap = df_kpi[df_kpi["dt"] == asof].copy()
            if bank_dim in snap.columns:
                snap = snap.rename(columns={bank_dim: "bank"})
                peers = peer_table(snap, bank_value, metric)
                st.caption(f"As of {asof.date()} (metric: {metric})")
                st.dataframe(peers[["bank","value","rank","percentile","is_selected"]], use_container_width=True, height=360)

with tab_profile:
    st.subheader("3) Bank profile: окремі блоки аналізу")
    apikod = st.text_input("apikod ", value=CFG.apikod_bs, key="apikod_p")
    bank_dim = st.text_input("bank dimensionkod ", value=CFG.bank_dimension_kod, key="bankdim_p")

    start_d, end_d = default_start_end(CFG.default_lookback_days)
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        start = st.date_input("Start ", value=start_d, key="start_p")
    with c2:
        end = st.date_input("End ", value=end_d, key="end_p")
    with c3:
        period = st.text_input("period ", value="", key="period_p")

    if not (apikod and bank_dim):
        st.info("Спочатку задай apikod і bank dimension.")
        st.stop()

    dim_vals = cached_dimension_values(bank_dim, date=yyyymmdd(end))
    banks = [{"bank": str(r.get(bank_dim)), "txt": r.get("txt")} for r in (dim_vals or []) if bank_dim in r]
    df_banks = pd.DataFrame(banks)
    if df_banks.empty:
        st.error("Немає значень для цього dimensionkod.")
        st.stop()
    bank_value = st.selectbox("Bank ", options=df_banks["bank"].tolist(), key="bank_p")

    params = {"start": yyyymmdd(start), "end": yyyymmdd(end)}
    if period:
        params["period"] = period
    with st.spinner("Loading dataset..."):
        raw = client.fetch_dataset_all(apikod, params=params, page_size=5000)
    df = normalize_records(raw)
    st.markdown("### A) Data quality")
    st.dataframe(data_quality_report(df), use_container_width=True)

    df_bank = filter_by_bank(df, bank_dim, bank_value)

    st.markdown("### B) Core KPI")
    kpi_list = (CFG.kpi_sets.get("core_bs1", []) + CFG.kpi_sets.get("core_bs2", []))
    df_bank_kpi = filter_by_id_api(df_bank, kpi_list)
    if df_bank_kpi.empty:
        st.error("Нема KPI для цього банку.")
        st.stop()

    snap = kpi_snapshot(df_bank_kpi)
    asof = snap["dt"].iloc[0]
    st.caption(f"As of {asof.date()}")
    st.dataframe(snap, use_container_width=True, height=220)

    st.markdown("### C) Dynamics")
    ts = kpi_timeseries(df_bank_kpi)
    st.plotly_chart(px.line(ts, x="dt", y="value", color="id_api"), use_container_width=True)

    st.markdown("### D) Formula KPIs")
    fk = formula_kpis(ts)
    st.dataframe(fk, use_container_width=True, height=240)

    st.markdown("### E) Structure (auto top-N)")
    top_n = int(CFG.structure.get("top_n", 12))
    assets_ids = auto_structure_ids(df_bank, str(CFG.structure.get("assets_prefix","BS1_Assets")), top_n=top_n)
    liab_ids = auto_structure_ids(df_bank, str(CFG.structure.get("liab_prefix","BS1_Liab")), top_n=top_n)

    cA, cB = st.columns(2)
    with cA:
        st.write("Assets IDs:", assets_ids)
        assets_tbl = structure_snapshot(df_bank, assets_ids)
        st.dataframe(assets_tbl, use_container_width=True, height=220)
        if not assets_tbl.empty:
            st.plotly_chart(px.pie(assets_tbl, names="id_api", values="value"), use_container_width=True)
            st.plotly_chart(px.treemap(assets_tbl, path=["id_api"], values="value"), use_container_width=True)
    with cB:
        st.write("Liabilities IDs:", liab_ids)
        liab_tbl = structure_snapshot(df_bank, liab_ids)
        st.dataframe(liab_tbl, use_container_width=True, height=220)
        if not liab_tbl.empty:
            st.plotly_chart(px.pie(liab_tbl, names="id_api", values="value"), use_container_width=True)
            st.plotly_chart(px.treemap(liab_tbl, path=["id_api"], values="value"), use_container_width=True)

    st.markdown("### F) Peer comparison (Assets)")
    df_all_assets = df[df["id_api"] == "BS1_AssetsTotal"].copy()
    if bank_dim in df_all_assets.columns and not df_all_assets.empty:
        asof_all = df_all_assets["dt"].max()
        snap_all = df_all_assets[df_all_assets["dt"] == asof_all].rename(columns={bank_dim: "bank"})
        peers = peer_table(snap_all, bank_value, "BS1_AssetsTotal")
        st.dataframe(peers.head(80), use_container_width=True, height=280)
    else:
        st.info("Peers unavailable (no bank dimension in response).")

    st.markdown("### G) Export")
    export_dir = ROOT / "exports"
    export_dir.mkdir(exist_ok=True)
    if st.button("Export to Excel"):
        out_path = export_dir / f"bank_profile_{bank_value}_{yyyymmdd(end)}.xlsx"
        with pd.ExcelWriter(out_path, engine="openpyxl") as xw:
            snap.to_excel(xw, sheet_name="kpi_snapshot", index=False)
            ts.to_excel(xw, sheet_name="kpi_timeseries", index=False)
            fk.to_excel(xw, sheet_name="formula_kpis", index=False)
            assets_tbl.to_excel(xw, sheet_name="assets_structure", index=False)
            liab_tbl.to_excel(xw, sheet_name="liab_structure", index=False)
            if 'peers' in locals():
                peers.to_excel(xw, sheet_name="peers_assets", index=False)
        st.success(f"Saved: {out_path}")
