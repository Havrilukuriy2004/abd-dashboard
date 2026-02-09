from __future__ import annotations

import os
from pathlib import Path
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

# ---------- Streamlit setup ----------
st.set_page_config(page_title="Kodex — NBU Bank Dashboard", layout="wide")
ROOT = Path(__file__).resolve().parents[1]
CFG = load_config(ROOT / "config" / "config.yaml")

client = NBUOpenDataClient(base_url=CFG.nbu_api_base, use_cache=True)

st.title("Kodex — Dashboard по вибору банку (NBU OpenData)")

with st.expander("API reminder (what the code assumes)", expanded=False):
    st.markdown(
        """
- We call NBU OpenData via GET requests to a dataset mnemonic (`apikod`).
- Dates are either `date=yyyyMMdd` or ranges `start=yyyyMMdd&end=yyyyMMdd`.
- Large responses may need pagination via `offset` + `limit`.
"""
    )

tab_catalog, tab_select, tab_profile = st.tabs(["Catalog", "Bank selection", "Bank profile"])

# ---------- Helpers ----------
@st.cache_data(show_spinner=False, ttl=3600)
def cached_list_datasets():
    return client.list_datasets()

@st.cache_data(show_spinner=False, ttl=3600)
def cached_list_dimensions():
    return client.list_dimensions()

@st.cache_data(show_spinner=False, ttl=3600)
def cached_dimension_values(dimensionkod: str, date: str | None):
    return client.dimension_values(dimensionkod, date=date)

def yyyymmdd(d: dt.date) -> str:
    return d.strftime("%Y%m%d")

def default_start_end(lookback_days: int):
    today = dt.date.today()
    start = today - dt.timedelta(days=lookback_days)
    return start, today

# ---------- Tab 1: Catalog ----------
with tab_catalog:
    st.subheader("1) Catalog: find dataset (apikod) and its dimensions")

    datasets = cached_list_datasets()
    df_ds = datasets_to_df(datasets)

    q = st.text_input("Search by keyword (e.g., 'баланс', 'bank', 'BS', 'фінансов')", value="")
    df_view = search_datasets(df_ds, q)
    st.dataframe(df_view, use_container_width=True, height=350)

    st.caption("Pick a row and copy its 'apikod' into config/config.yaml → apikod_bs.")

    st.markdown("---")
    st.subheader("Dimensions directory (dimensionkod)")
    df_dim = pd.DataFrame(cached_list_dimensions())
    st.dataframe(df_dim, use_container_width=True, height=250)

# ---------- Tab 2: Bank selection ----------
with tab_select:
    st.subheader("2) Bank selection: rank & filter banks")

    apikod = st.text_input("apikod (dataset mnemonic)", value=CFG.apikod_bs)
    bank_dim = st.text_input("bank dimensionkod", value=CFG.bank_dimension_kod)

    start_d, end_d = default_start_end(CFG.default_lookback_days)
    c1, c2 = st.columns(2)
    with c1:
        start = st.date_input("Start date", value=start_d)
    with c2:
        end = st.date_input("End date", value=end_d)

    st.info("If the dataset requires a 'period' parameter, set it below (optional).")
    period = st.text_input("period (optional)", value="")

    if not apikod:
        st.warning("Set apikod first (Catalog tab → copy apikod).")
    else:
        # Step A: pull dimension values for banks to show selection list
        banks = []
        if bank_dim:
            dim_vals = cached_dimension_values(bank_dim, date=yyyymmdd(end))
            # normalize possible fields: many dimensions return {'txt':..., <dimensionkod>:...}
            if dim_vals:
                key = bank_dim
                for r in dim_vals:
                    if key in r:
                        banks.append({"bank": r.get(key), "txt": r.get("txt")})
        df_banks = pd.DataFrame(banks)

        if bank_dim and df_banks.empty:
            st.error(
                "bank_dimension_kod is set, but no values were returned. "
                "Most likely this dimension is not 'banks' for this dataset. "
                "Go back to Catalog → inspect dataset dimensions and try another dimensionkod."
            )

        bank_value = st.selectbox(
            "Select bank (dimension value)",
            options=df_banks["bank"].astype(str).tolist() if not df_banks.empty else [],
        )

        # Step B: fetch minimal KPIs for ranking
        kpi_list = (CFG.kpi_sets.get("core_bs1", []) + CFG.kpi_sets.get("core_bs2", []))
        params = {"start": yyyymmdd(start), "end": yyyymmdd(end)}
        if period:
            params["period"] = period

        st.write("Loading data from API...")
        raw = client.fetch_dataset_all(apikod, params=params, page_size=5000)
        df = normalize_records(raw)

        # filter to KPIs
        df_kpi = filter_by_id_api(df, kpi_list)

        # build latest snapshot across banks for ranking
        asof = df_kpi["dt"].max() if not df_kpi.empty else None
        if asof is None:
            st.error("No data returned. Check apikod, date range, or required dimensions.")
        else:
            # Ranking metric: assets if available, else first KPI
            ranking_metric = "BS1_AssetsTotal" if "BS1_AssetsTotal" in kpi_list else kpi_list[0]

            if bank_dim and bank_dim in df_kpi.columns:
                snap = df_kpi.loc[df_kpi["dt"] == asof].copy()
                # normalize bank column name for peer functions
                snap = snap.rename(columns={bank_dim: "bank"})
                peers = peer_table(snap, bank_value=bank_value, metric_id_api=ranking_metric)

                st.markdown(f"**As of:** {asof.date()} — Ranking metric: `{ranking_metric}`")
                st.dataframe(
                    peers.loc[:, ["bank", "value", "rank", "percentile", "is_selected"]],
                    use_container_width=True,
                    height=350
                )
            else:
                st.warning(
                    "No bank dimension column found in returned dataset. "
                    "This can happen if the dataset does not contain banks or uses another dimensionkod."
                )

# ---------- Tab 3: Bank profile ----------
with tab_profile:
    st.subheader("3) Bank profile: KPI cards, dynamics, structure")

    apikod = st.text_input("apikod (dataset mnemonic) ", value=CFG.apikod_bs, key="apikod_profile")
    bank_dim = st.text_input("bank dimensionkod ", value=CFG.bank_dimension_kod, key="bankdim_profile")

    start_d, end_d = default_start_end(CFG.default_lookback_days)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        start = st.date_input("Start", value=start_d, key="start_profile")
    with c2:
        end = st.date_input("End", value=end_d, key="end_profile")
    with c3:
        period = st.text_input("period (optional)", value="", key="period_profile")

    # bank list
    bank_value = ""
    if bank_dim:
        dim_vals = cached_dimension_values(bank_dim, date=yyyymmdd(end))
        banks = []
        for r in dim_vals or []:
            if bank_dim in r:
                banks.append({"bank": str(r.get(bank_dim)), "txt": r.get("txt")})
        df_banks = pd.DataFrame(banks)
        if not df_banks.empty:
            bank_value = st.selectbox("Bank", options=df_banks["bank"].tolist(), index=0)
        else:
            st.warning("No dimension values for chosen bank dimension. Check bank_dimension_kod.")
    else:
        st.warning("Set bank_dimension_kod to build a bank profile.")
        st.stop()

    kpi_list = (CFG.kpi_sets.get("core_bs1", []) + CFG.kpi_sets.get("core_bs2", []))
    params = {"start": yyyymmdd(start), "end": yyyymmdd(end)}
    if period:
        params["period"] = period

    raw = client.fetch_dataset_all(apikod, params=params, page_size=5000)
    df = normalize_records(raw)

    # --- Quality ---
    st.markdown("#### Data quality")
    st.dataframe(data_quality_report(df), use_container_width=True)

    # --- Bank filter + KPI filter ---
    df_bank = filter_by_bank(df, bank_dimension_kod=bank_dim, bank_value=bank_value)
    df_bank_kpi = filter_by_id_api(df_bank, kpi_list)

    if df_bank_kpi.empty:
        st.error("No KPI data for this bank in the chosen range. Check date range or indicators.")
        st.stop()

    # --- Snapshot KPI cards ---
    snap = kpi_snapshot(df_bank_kpi)
    asof = snap["dt"].iloc[0] if not snap.empty else None
    st.markdown(f"#### KPI snapshot (as of {asof.date() if asof is not None else 'n/a'})")

    # Build cards
    card_map = {r["id_api"]: r["value"] for _, r in snap.iterrows()}
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Assets", f"{card_map.get('BS1_AssetsTotal', float('nan')):,.0f}" if 'BS1_AssetsTotal' in card_map else "n/a")
    m2.metric("Liabilities", f"{card_map.get('BS1_LiabTotal', float('nan')):,.0f}" if 'BS1_LiabTotal' in card_map else "n/a")
    m3.metric("Equity", f"{card_map.get('BS1_CapitalTotal', float('nan')):,.0f}" if 'BS1_CapitalTotal' in card_map else "n/a")
    m4.metric("Net interest", f"{card_map.get('BS1_NetInterIncomeCosts', float('nan')):,.0f}" if 'BS1_NetInterIncomeCosts' in card_map else "n/a")
    m5.metric("Net profit", f"{card_map.get('BS2_NetProfitLoss', float('nan')):,.0f}" if 'BS2_NetProfitLoss' in card_map else "n/a")

    # --- Dynamics ---
    st.markdown("#### Dynamics")
    ts = kpi_timeseries(df_bank_kpi)
    fig = px.line(ts, x="dt", y="value", color="id_api", markers=False)
    st.plotly_chart(fig, use_container_width=True)

    # --- Peer comparison (assets) at last date ---
    st.markdown("#### Peer comparison (Assets)")
    df_all_kpi = filter_by_id_api(df, ["BS1_AssetsTotal"])
    if bank_dim in df_all_kpi.columns and not df_all_kpi.empty:
        asof_all = df_all_kpi["dt"].max()
        snap_all = df_all_kpi.loc[df_all_kpi["dt"] == asof_all].rename(columns={bank_dim: "bank"})
        peers = peer_table(snap_all, bank_value=bank_value, metric_id_api="BS1_AssetsTotal")
        st.dataframe(peers.head(50), use_container_width=True, height=300)
    else:
        st.info("Cannot compute peers: bank dimension not present in data returned.")

    # --- Export ---
    st.markdown("#### Export")
    export_dir = ROOT / "exports"
    export_dir.mkdir(exist_ok=True)
    if st.button("Export tables to Excel"):
        out_path = export_dir / f"bank_profile_{bank_value}_{yyyymmdd(end)}.xlsx"
        with pd.ExcelWriter(out_path, engine="openpyxl") as xw:
            snap.to_excel(xw, sheet_name="kpi_snapshot", index=False)
            ts.to_excel(xw, sheet_name="kpi_timeseries", index=False)
            if 'peers' in locals() and isinstance(peers, pd.DataFrame):
                peers.to_excel(xw, sheet_name="peers_assets", index=False)
        st.success(f"Saved: {out_path}")
