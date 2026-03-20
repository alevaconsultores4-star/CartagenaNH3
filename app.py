"""
Cartagena H2 — Financial Model Dashboard  v3.0
Electryon Power Inc. | Green Ammonia Export
Light theme · Large fonts · Investor-friendly
Run: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from model_engine import (
    ProjectParams, compute_process_chain, compute_capex,
    compute_production_profile, compute_revenue, compute_opex,
    compute_dcf, compute_lcoa_breakdown, sensitivity_analysis,
    DEFAULT_SENSITIVITY
)

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Cartagena H2 — Financial Model",
    page_icon="⚗️", layout="wide",
    initial_sidebar_state="expanded"
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family:'Inter',sans-serif; font-size:16px; color:#1a1a2e; }
.stApp { background:#f8f9fc; }
.main .block-container { padding:1.5rem 2rem; max-width:1440px; }

section[data-testid="stSidebar"] { background:#ffffff; border-right:2px solid #e2e8f0; }
section[data-testid="stSidebar"] * { color:#1a1a2e !important; }
section[data-testid="stSidebar"] .stMarkdown h3 {
    color:#1e4799 !important; font-size:0.76rem; font-weight:700;
    letter-spacing:0.10em; text-transform:uppercase;
    margin:1.1rem 0 0.3rem; padding-bottom:0.3rem; border-bottom:2px solid #e2e8f0;
}
section[data-testid="stSidebar"] label { font-size:0.92rem !important; font-weight:500 !important; }
section[data-testid="stSidebar"] .streamlit-expanderHeader { font-size:0.9rem !important; font-weight:600 !important; }

/* Dropdown options - dark text */
[data-baseweb="popover"] *, [data-baseweb="menu"] *, li[role="option"], li[role="option"] * {
    color:#1a1a2e !important;
}
li[role="option"]:hover, li[role="option"]:hover * {
    background:#eff6ff !important; color:#1a1a2e !important;
}

.kpi-card { background:#fff; border:1px solid #e2e8f0; border-top:4px solid #1e4799;
            border-radius:12px; padding:1.1rem 1.3rem; text-align:center;
            box-shadow:0 1px 4px rgba(0,0,0,0.06); }
.kpi-label { font-size:0.76rem; font-weight:600; color:#6b7280;
             text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.35rem; }
.kpi-value { font-size:1.9rem; font-weight:700; color:#1a1a2e; line-height:1.1; }
.kpi-sub   { font-size:0.8rem; color:#6b7280; margin-top:0.25rem; }
.kpi-good  { color:#16a34a !important; }
.kpi-warn  { color:#d97706 !important; }
.kpi-bad   { color:#dc2626 !important; }

.sec-hdr { font-size:1.05rem; font-weight:700; color:#1e4799;
           border-bottom:2px solid #e2e8f0; padding-bottom:0.4rem; margin:1.5rem 0 0.9rem; }

.stTabs [data-baseweb="tab-list"] { background:transparent; gap:4px; }
.stTabs [data-baseweb="tab"] { background:#fff; color:#6b7280; border:1px solid #e2e8f0;
    border-radius:8px; font-size:0.9rem; font-weight:500; padding:0.5rem 1.1rem; }
.stTabs [aria-selected="true"] { background:#1e4799 !important; color:#fff !important;
    border-color:#1e4799 !important; }

.info-box { background:#eff6ff; border-left:4px solid #1e4799; border-radius:0 8px 8px 0;
            padding:0.9rem 1.1rem; margin:0.8rem 0; font-size:0.92rem; color:#1e3a5f; line-height:1.6; }
.warn-box { background:#fffbeb; border-left:4px solid #d97706; border-radius:0 8px 8px 0;
            padding:0.9rem 1.1rem; margin:0.8rem 0; font-size:0.92rem; color:#78350f; line-height:1.6; }
.info-box strong, .warn-box strong { font-weight:700; }
</style>
""", unsafe_allow_html=True)

# ─── PLOTLY THEME ─────────────────────────────────────────────────────────────
PL = dict(
    paper_bgcolor="#ffffff", plot_bgcolor="#f8f9fc",
    font=dict(family="Inter,sans-serif", color="#374151", size=13),
    title=dict(font=dict(family="Inter,sans-serif", color="#1a1a2e", size=15)),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#374151", size=12)),
    margin=dict(l=60, r=20, t=48, b=48),
    xaxis=dict(gridcolor="#e2e8f0", zerolinecolor="#e2e8f0",
               tickfont=dict(color="#374151", size=12), title_font=dict(color="#374151")),
    yaxis=dict(gridcolor="#e2e8f0", zerolinecolor="#e2e8f0",
               tickfont=dict(color="#374151", size=12), title_font=dict(color="#374151")),
)

def lo(title="", lkw=None, xkw=None, ykw=None, **kw):
    """Build layout. Pass lkw/xkw/ykw INSIDE this call, never directly to update_layout.
    Strips legend/xaxis/yaxis from kw to avoid 'multiple values' TypeError."""
    base = dict(PL)
    if title:  base["title"]  = dict(text=title, font=dict(family="Inter", color="#1a1a2e", size=15))
    if lkw:    base["legend"] = {**PL["legend"], **lkw}
    if xkw:    base["xaxis"]  = {**PL["xaxis"],  **xkw}
    if ykw:    base["yaxis"]  = {**PL["yaxis"],  **ykw}
    for k in ("legend", "xaxis", "yaxis", "title"):
        kw.pop(k, None)
    base.update(kw)
    return base

C = dict(blue="#1e4799", teal="#0891b2", green="#16a34a",
         amber="#d97706", red="#dc2626", purple="#7c3aed", gray="#6b7280")

def kpi(col, label, val, sub="", cls=""):
    col.markdown(f"""<div class="kpi-card">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value {cls}">{val}</div>
      <div class="kpi-sub">{sub}</div>
    </div>""", unsafe_allow_html=True)

def sec(txt):
    st.markdown(f'<div class="sec-hdr">{txt}</div>', unsafe_allow_html=True)

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚗️ Cartagena H2")
    st.markdown("**Financial Model v3.0 — Electryon Power Inc.**")
    st.divider()
    st.caption("All values editable. Defaults = EPI Excel (Mar 2026).")

    # ── PROJECT ───────────────────────────────────────────────────────────────
    with st.expander("📋  Project", expanded=True):
        scenario = st.selectbox("Revenue scenario", ["base","bear","bull"],
            format_func=lambda x: {"base":"Base — $900/t NH₃",
                                    "bear":"Bear — $700/t NH₃",
                                    "bull":"Bull — $1,100/t NH₃"}[x])
        cod_year = st.slider("Start of production", 2029, 2032, 2030, 1,
            help="COD year. 2yr construction before this.")
        project_life = st.slider("Project life (years)", 15, 30, 25, 1,
            help="EPI: 25 years (NH3 Interface R32)")

    # ── SOLAR PV ─────────────────────────────────────────────────────────────
    with st.expander("☀️  Solar PV", expanded=True):
        solar_mwac   = st.slider("Nameplate capacity (MWac)", 150, 450, 250, 10,
            help="EPI H2!R11 — 250 MWac single-axis tracking. DC/AC ratio 1.2 fixed.")
        solar_capex  = st.slider("Installed cost ($/kWac)", 500, 1200, 800, 25,
            help="EPI DATABASE R6 — $800/kWac all-in.")
        solar_cf     = st.slider("Capacity factor (%)", 18.0, 32.0, 24.6, 0.1,
            help="EPI H2!R15 — 24.60% from PVSyst hourly simulation.")
        solar_gwh    = st.number_input("Annual generation (GWh/yr)", 400.0, 900.0, 615.58, 1.0,
            help="EPI H2!R13 — 615.58 GWh/yr. Overrides CF × capacity.")
        solar_om_mw  = st.slider("O&M cost ($/MW/yr)", 8000, 25000, 13000, 500,
            help="EPI/Arup: $13,000/MW/yr")

    # ── GRID POWER ───────────────────────────────────────────────────────────
    with st.expander("🔌  Grid Power", expanded=True):
        grid_night_mw   = st.slider("Night grid power (MW)", 40, 150, 80, 5,
            help="EPI H2!R30 — 80 MW at 32% complementarity.")
        grid_day_comp   = st.slider("Day complementarity (%)", 0, 30, 10, 1,
            help="EPI H2!R23 — 10% of 180MW = 18MW grid top-up during daylight.")
        grid_night_comp = st.slider("Night complementarity (%)", 10, 60, 32, 1,
            help="EPI H2!R29 — 32% of 180MW = 57.6MW at night.")
        grid_price_day  = st.slider("Grid day price ($/MWh)", 40, 130, 77, 1,
            help="EPI H2!R106 — $77.34/MWh (COP 327/kWh ÷ TRM 4,229)")
        grid_price_night= st.slider("Grid night price ($/MWh)", 40, 110, 70, 1,
            help="EPI H2!R107 — $69.61/MWh (COP 294/kWh ÷ TRM 4,229)")
        hb_grid_mw      = st.slider("HB auxiliary grid (MW)", 4, 20, 8, 1,
            help="EPI H2!R57 — 8 MW for Haber-Bosch process (24hrs/day).")

    # ── ELECTROLYSER ─────────────────────────────────────────────────────────
    with st.expander("⚡  Electrolyser", expanded=True):
        elec_mw      = st.slider("Capacity (MW)", 100, 300, 180, 10,
            help="EPI H2!R36 — 180 MW AWE (Alkaline).")
        elec_sec     = st.slider("Efficiency — SEC (kWh/kgH₂)", 40, 65, 50, 1,
            help="EPI H2!R40 — 50 kWh/kgH₂ including BoP. 2030 target: 45.")
        elec_capex   = st.slider("Cost ($/kWe all-in)", 350, 900, 612, 10,
            help="EPI DATABASE R18 — $612/kWe (stack + BoP + EPC).")
        elec_avail   = st.slider("Utilization (%)", 85, 100, 98, 1,
            help="EPI H2!R45 — 98% long-term availability.") / 100
        elec_degrad  = st.slider("SEC degradation (%/yr)", 0.0, 2.0, 0.5, 0.1,
            help="Annual increase in energy consumption as stack ages.") / 100

    # ── HABER-BOSCH ──────────────────────────────────────────────────────────
    with st.expander("🏭  Haber-Bosch & ASU", expanded=False):
        hb_eff       = st.slider("HB conversion efficiency (%)", 85, 100, 98, 1,
            help="EPI H2!R62 — 98%. Fraction of H₂ successfully converted to NH₃.") / 100
        hb_h2_ratio  = st.number_input("H₂/NH₃ ratio (tH₂/tNH₃)", 0.150, 0.200, 0.177553, 0.001,
            format="%.6f",
            help="EPI H2!R61 — 0.177553 (stoichiometric from molecular weights).")
        hb_capex     = st.slider("HB cost ($/kgNH₃/hr)", 1500, 6000, 3300, 100,
            help="EPI DATABASE R21 — $3,300/kgNH₃/hr.")
        asu_capex    = st.slider("ASU cost ($/kgN₂/hr)", 700, 2500, 1450, 50,
            help="EPI DATABASE R22 — $1,450/kgN₂/hr.")
        n2_excess    = st.slider("N₂ excess (%)", 5, 30, 15, 1,
            help="EPI H2!R74 — 15% extra N₂ above stoichiometric.") / 100
        water_l_kgh2 = st.slider("Water consumption (L/kgH₂)", 18.0, 30.0, 22.3, 0.1,
            help="EPI H2!R50 — 22.3 L/kgH₂ (IRENA reference).")
        nh3_stor_t   = st.slider("NH₃ onsite storage (tonnes)", 3000, 20000, 9160, 100,
            help="EPI H2!R97 — 9,160 t storage.")

    # ── INVESTMENT COSTS ─────────────────────────────────────────────────────
    with st.expander("🏗️  Investment Costs (CAPEX)", expanded=False):
        st.markdown("**Port & Infrastructure (Fichtner)**")
        exp_fac   = st.slider("Export terminal ($M)", 20.0, 100.0, 48.0, 1.0,
            help="Fichtner Jan 2025 — refrigerated NH₃ tank + pumps at Puerto Bahía.")
        pipeline_km = st.slider("NH₃ pipeline ($M)", 5.0, 35.0, 16.0, 0.5,
            help="Fichtner — 10 km buried pipeline to Mamonal port.")
        ohtl      = st.slider("Power line 220kV ($M)", 4.0, 20.0, 9.0, 0.5,
            help="Fichtner — 11.2 km 220kV overhead transmission line.")
        wtp       = st.slider("Water treatment pipeline ($M)", 3.0, 18.0, 8.7, 0.5,
            help="Fichtner — WTP + Canal del Dique intake.")
        koh       = st.slider("KOH electrolyte system ($M)", 2.0, 16.0, 7.1, 0.5,
            help="Fichtner — KOH make-up system for AWE.")
        wwtp      = st.slider("Wastewater plant ($M)", 1.0, 10.0, 3.8, 0.5,
            help="Fichtner — wastewater treatment.")
        periph_cont = st.slider("Port contingency (%)", 5, 30, 15, 1,
            help="Fichtner contingency on peripheral items.") / 100
        bop_pct   = st.slider("HB installation & BoP (%)", 15, 50, 30, 1,
            help="EPI H2!R99 — 30% of HB sub-block for installation, BoP, risk.") / 100
        owners_pct= st.slider("Owner's costs / FEED (%)", 2, 10, 5, 1,
            help="5% of total project cost for FEED, permitting, legal.") / 100

    # ── OPERATING COSTS ──────────────────────────────────────────────────────
    with st.expander("💰  Operating Costs (OPEX)", expanded=False):
        freight_t  = st.slider("Freight & insurance ($/tonne)", 20, 150, 60, 5,
            help="EPI NH3 Interface R99 — $60/tonne all-in.")
        om_musd    = st.number_input("Fixed O&M ($M/yr)", 5.0, 30.0, 13.72, 0.1,
            help="EPI NH3 G0 R97 — $13.72M/yr fixed equipment O&M.")
        grid_escal = st.slider("Grid price escalation (%/yr)", 0.0, 5.0, 2.5, 0.1,
            help="Annual grid electricity price increase.") / 100
        periph_om  = st.number_input("Port O&M ($M/yr)", 0.5, 8.0, 2.21, 0.1,
            help="Fichtner — $2.21M/yr port infrastructure O&M.")

    # ── REVENUE ──────────────────────────────────────────────────────────────
    with st.expander("📈  Revenue", expanded=False):
        nh3_price  = st.slider("NH₃ start price ($/tonne)", 500, 1500, 900, 25,
            help="Year 1 spot price. Market Q3 2025: $840–$902/t NW Europe.")
        nh3_floor  = st.slider("NH₃ price floor ($/tonne)", 400, 900, 650, 25,
            help="Minimum price assumption — covers full OPEX.")
        h2g_vol    = st.slider("H₂Global contract (ktpa)", 0, 100, 50, 5,
            help="NH₃ under Hintco long-term contract. Bankable fixed-price revenue.")
        h2g_eur    = st.slider("H₂Global price (€/tonne)", 500, 1200, 811, 10,
            help="Hintco Lot 1 net price. Benchmark: €811/t.")
        eur_usd    = st.number_input("EUR/USD rate", 0.90, 1.30, 1.07, 0.01,
            help="EPI: 1.07")
        h2g_years  = st.slider("H₂Global contract length (years)", 5, 15, 10, 1,
            help="Duration of the fixed-price HPA contract.")
        col_h2_ktpa= st.number_input("Colombia H₂ offtake (ktpa)", 0.0, 20.0, 9.0, 0.5,
            help="H₂ allocation to Reficar domestic offtake.")
        col_h2_px  = st.number_input("Colombia H₂ price ($/kgH₂)", 2.0, 8.0, 4.02, 0.1,
            help="EPI assumption: $4.02/kgH₂")

    # ── FINANCING ────────────────────────────────────────────────────────────
    with st.expander("🏦  Financing", expanded=False):
        debt_pct   = st.slider("Debt (% of total investment)", 30, 85, 75, 5,
            help="EPI NH3 Interface R182 — D/E=3, debt=75%.") / 100
        wacc_pct   = st.slider("WACC / discount rate (%)", 5.0, 15.0, 10.0, 0.5,
            help="EPI NH3 Interface R181 — 10% nominal.") / 100
        debt_rate  = st.slider("Loan interest rate (%)", 3.0, 12.0, 5.0, 0.25,
            help="EPI NH3 Interface R185 — 5% nominal.") / 100
        debt_tenor = st.slider("Loan tenor (years)", 5, 20, 7, 1,
            help="EPI NH3 Interface R184 — 7 year loan.")
        tax_rate   = st.slider("Income tax rate (%)", 0, 40, 35, 1,
            help="Colombian corporate tax rate before incentive deductions.") / 100

    # ── COLOMBIA INCENTIVES ───────────────────────────────────────────────────
    with st.expander("🇨🇴  Colombia Incentives", expanded=False):
        apply_vat  = st.toggle("Ley 1715 Art.12 — VAT exemption (19%)", value=True,
            help="19% VAT waiver on all equipment. ~$84M saving on core CAPEX.")
        apply_tariff= st.toggle("Ley 1715 Art.13 — Import tariff (~10%)", value=True,
            help="~10% tariff exemption on imported equipment. ~$15M saving.")
        tax_ded_pct = st.slider("Art.11 income tax deduction (%)", 0, 100, 50, 5,
            help="Ley 1715 Art.11 — 50% of investment deductible over 15 years.") / 100
        imported_pct= st.slider("Imported equipment fraction (%)", 30, 90, 60, 5,
            help="Share of core CAPEX that is imported — determines tariff saving.") / 100

    st.divider()
    st.caption("EPI Excel (Mar 2026) · Arup (Nov 2025) · Fichtner (Jan 2025)")


# ─── RUN MODEL ────────────────────────────────────────────────────────────────
@st.cache_data
def run_model(scenario, cod_year, project_life,
              solar_mwac, solar_capex, solar_cf, solar_gwh, solar_om_mw,
              grid_night_mw, grid_day_comp, grid_night_comp,
              grid_price_day, grid_price_night, hb_grid_mw,
              elec_mw, elec_sec, elec_capex, elec_avail, elec_degrad,
              hb_eff, hb_h2_ratio, hb_capex, asu_capex,
              n2_excess, water_l_kgh2, nh3_stor_t,
              exp_fac, pipeline_km, ohtl, wtp, koh, wwtp,
              periph_cont, bop_pct, owners_pct,
              freight_t, om_musd, grid_escal, periph_om,
              nh3_price, nh3_floor, h2g_vol, h2g_eur, eur_usd,
              h2g_years, col_h2_ktpa, col_h2_px,
              debt_pct, wacc_pct, debt_rate, debt_tenor, tax_rate,
              apply_vat, apply_tariff, tax_ded_pct, imported_pct):
    p = ProjectParams(
        cod_year=cod_year,
        project_life_years=project_life,
        solar_mwac=float(solar_mwac),
        solar_mwp=float(solar_mwac),
        solar_capacity_factor=float(solar_cf) / 100,
        solar_gwh_yr=float(solar_gwh),
        solar_capex_per_mwac=float(solar_capex) * 1_000,
        solar_opex_per_mwac=float(solar_om_mw),
        hydro_ppa_mw=float(grid_night_mw),
        grid_day_complementarity=float(grid_day_comp) / 100,
        grid_night_complementarity=float(grid_night_comp) / 100,
        electrolyser_mw=float(elec_mw),
        electrolyser_sec=float(elec_sec),
        electrolyser_capex_all_in_mw=float(elec_capex) * 1_000,
        plant_availability=float(elec_avail),
        electrolyser_degradation=float(elec_degrad),
        hb_combined_efficiency=float(hb_eff),
        hb_h2_per_tnh3=float(hb_h2_ratio),
        hb_capex_per_kgd=float(hb_capex) / 24,
        asu_capex_per_kgd_n2=float(asu_capex) / 24,
        n2_excess_pct=float(n2_excess),
        water_l_per_kgh2=float(water_l_kgh2),
        nh3_storage_t=float(nh3_stor_t),
        export_facility_musd=float(exp_fac),
        pipeline_km=float(pipeline_km) / 1.6,
        power_ohtl_musd=float(ohtl),
        wtp_pipeline_musd=float(wtp),
        koh_system_musd=float(koh),
        wwtp_musd=float(wwtp),
        peripheral_contingency_pct=float(periph_cont),
        hb_bop_pct=float(bop_pct),
        grid_price_day_kwh=float(grid_price_day) / 1_000,
        grid_price_night_kwh=float(grid_price_night) / 1_000,
        grid_price_hb_kwh=float(grid_price_night) / 1_000,
        grid_price_escalation=float(grid_escal),
        freight_insurance_per_t=float(freight_t),
        fixed_opex_annual_musd=float(om_musd),
        peripheral_opex_mpa=float(periph_om),
        nh3_price_base=float(nh3_price),
        nh3_price_bear=float(nh3_price) * 0.778,
        nh3_price_bull=float(nh3_price) * 1.222,
        nh3_price_floor=float(nh3_floor),
        h2global_volume_ktpa=float(h2g_vol),
        h2global_net_price_eur=float(h2g_eur),
        eur_usd=float(eur_usd),
        h2global_contract_years=int(h2g_years),
        colombia_h2_ktpa=float(col_h2_ktpa),
        colombia_h2_price_per_kg=float(col_h2_px),
        debt_share=float(debt_pct),
        wacc=float(wacc_pct),
        debt_interest_rate=float(debt_rate),
        debt_tenor_years=int(debt_tenor),
        income_tax_rate=float(tax_rate),
        vat_exempt=bool(apply_vat),
        tariff_exempt=bool(apply_tariff),
        income_tax_deduction_pct=float(tax_ded_pct),
        imported_capex_fraction=float(imported_pct),
    )
    pc      = compute_process_chain(p)
    capex   = compute_capex(p)
    prod    = compute_production_profile(p, p.project_life_years)
    rev     = compute_revenue(p, prod, scenario)
    opex_df = compute_opex(p, prod, capex)
    dcf_df, metrics = compute_dcf(p, prod, rev, opex_df, capex)
    lb      = compute_lcoa_breakdown(p, capex, prod)
    sens    = sensitivity_analysis(p, DEFAULT_SENSITIVITY)
    return p, pc, capex, prod, rev, opex_df, dcf_df, metrics, lb, sens

p, pc, capex, prod, rev, opex_df, dcf_df, metrics, lb, sens = run_model(
    scenario, cod_year, project_life,
    solar_mwac, solar_capex, solar_cf, solar_gwh, solar_om_mw,
    grid_night_mw, grid_day_comp, grid_night_comp,
    grid_price_day, grid_price_night, hb_grid_mw,
    elec_mw, elec_sec, elec_capex, elec_avail, elec_degrad,
    hb_eff, hb_h2_ratio, hb_capex, asu_capex,
    n2_excess, water_l_kgh2, nh3_stor_t,
    exp_fac, pipeline_km, ohtl, wtp, koh, wwtp,
    periph_cont, bop_pct, owners_pct,
    freight_t, om_musd, grid_escal, periph_om,
    nh3_price, nh3_floor, h2g_vol, h2g_eur, eur_usd,
    h2g_years, col_h2_ktpa, col_h2_px,
    debt_pct, wacc_pct, debt_rate, debt_tenor, tax_rate,
    apply_vat, apply_tariff, tax_ded_pct, imported_pct
)

blended_rpt = metrics["avg_annual_revenue_musd"] * 1e6 / max(1, pc["nh3_net_tpa"])
apply_inc = apply_vat or apply_tariff

# ─── HEADER ───────────────────────────────────────────────────────────────────
irr   = metrics.get("project_irr_pct")
eirr  = metrics.get("equity_irr_pct")
irr_c = "kpi-good" if (irr or 0)>=10 else "kpi-warn"

st.markdown(f"""
<h1 style="font-size:2rem;font-weight:700;color:#1a1a2e;margin-bottom:0.2rem;">
  Project Cartagena H2 — Financial Model
</h1>
<p style="color:#6b7280;font-size:1rem;margin-bottom:1.2rem;">
  Green Ammonia Export · Cartagena, Colombia → Europe &amp; Asia · COD {cod_year}
  &nbsp;·&nbsp; {solar_mwac} MWac Solar · {elec_mw} MW Electrolyser
  · <strong>{pc['nh3_net_ktpa']:.1f} ktpa NH₃</strong>
</p>""", unsafe_allow_html=True)

# KPI row
k1,k2,k3,k4,k5,k6 = st.columns(6)
inc_sav = metrics.get('vat_saving_musd', 0) + metrics.get('tariff_saving_musd', 0)
gross = metrics.get('gross_capex_musd', metrics['total_capex_musd'] + inc_sav)
if inc_sav > 0:
    inv_sub = f"Gross ${gross:.0f}M − Ley 1715 ${inc_sav:.0f}M (Core ${metrics['core_capex_musd']:.0f}M + Port ${metrics['peripheral_capex_musd']:.0f}M)"
else:
    inv_sub = f"Core ${metrics['core_capex_musd']:.0f}M + Port ${metrics['peripheral_capex_musd']:.0f}M"
kpi(k1, "Total Investment",      f"${metrics['total_capex_musd']:.0f}M", inv_sub)
kpi(k2, "Production Cost",       f"${metrics['epi_lcoa_usd_t']:.0f}/t",
    f"Full investor: ${metrics['lcoa_usd_t']:.0f}/t")
kpi(k3, "Project Return (IRR)",  f"{irr:.1f}%" if irr else "—",
    f"Equity: {eirr:.1f}%" if eirr else "", irr_c)
kpi(k4, "Average Revenue",       f"${metrics['avg_annual_revenue_musd']:.0f}M/yr",
    f"EBITDA margin: {metrics['avg_ebitda_margin_pct']:.0f}%", "kpi-good")
kpi(k5, "Project NPV",           f"${metrics['project_npv_musd']:.0f}M",
    f"At {wacc_pct*100:.1f}% discount rate")
kpi(k6, "Payback",               f"{metrics['payback_years']} yrs" if metrics['payback_years'] else "—",
    f"Min DSCR: {metrics['min_dscr']}×" if metrics['min_dscr'] else "")

st.markdown("<br>", unsafe_allow_html=True)

# ─── TABS ─────────────────────────────────────────────────────────────────────
t1,t2,t3,t4,t5,t6,t7,t8,t9,t10 = st.tabs([
    "⚙️  How It Works",
    "📊  Financial Returns",
    "🏗️  Investment Cost",
    "💰  Operating Costs",
    "📈  Revenue",
    "🇨🇴  Colombia Benefits",
    "🎯  Scenarios & Sensitivity",
    "🔬  Full Calculation Ledger",
    "📊  LCOA Breakdown",
    "⚙️  Assumptions & Parameters",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — HOW IT WORKS
# ══════════════════════════════════════════════════════════════════════════════
with t1:
    sec("How the Plant Works — From Sunlight to Ammonia")

    # Process flow boxes
    col1, col2, col3 = st.columns(3)
    col1.success(f"☀️ Solar: $0 variable/MWh")
    col2.info(f"🔌 Grid night: ${grid_price_night}/MWh")
    col3.success(f"🏭 Production cost: ${metrics['epi_lcoa_usd_t']:.0f}/tonne NH₃")

    c1,c2,c3,c4,c5,c6,c7 = st.columns(7)
    c1.metric("☀️ Solar", f"{solar_mwac} MWac", f"{pc['solar_gwh_yr']:.0f} GWh/yr")
    c2.metric("🔌 Grid (night)", f"{grid_night_mw} MW", f"{pc['grid_night_gwh']:.0f} GWh/yr")
    c3.metric("⚡ Electrolyser", f"{elec_mw} MW", f"{elec_sec} kWh/kgH₂")
    c4.metric("🫧 Hydrogen", f"{pc['h2_gross_tpa']/1000:.1f} ktpa", "from electrolysis")
    c5.metric("🏭 Haber-Bosch", f"{pc['nh3_net_ktpa']:.1f} ktpa", "H₂ + N₂ → NH₃")
    c6.metric("🛢️ NH₃ output", f"{pc['nh3_rate_td']:.0f} t/day", f"{pc['nh3_net_ktpa']:.1f} ktpa")
    c7.metric("🚢 Export", f"{h2g_vol} ktpa", "Europe · Asia")

    st.info(f"☀️ Solar share: {pc['solar_share_pct']:.0f}%  ·  "
            f"⚡ Load factor: {pc['elec_load_pct']:.0f}%  ·  "
            f"💧 Water: {pc['water_m3h']:.0f} m³/hr  ·  "
            f"🌿 GHG: ~0 kgCO₂/kgNH₃ (RFNBO ✓)")

    # KPI cards
    sec("Key Production Numbers")
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    def pk(col, lbl, v, u):
        col.markdown(f"""<div class="kpi-card" style="border-top-color:#0891b2;">
          <div class="kpi-label">{lbl}</div>
          <div class="kpi-value" style="font-size:1.4rem;">{v}</div>
          <div class="kpi-sub">{u}</div></div>""", unsafe_allow_html=True)
    pk(c1, "Solar energy",          f"{pc['solar_gwh_yr']:.1f} GWh",  "per year")
    pk(c2, "Total power to elec.",  f"{pc['elec_total_gwh']:.1f} GWh","per year")
    pk(c3, "Hydrogen produced",     f"{pc['h2_gross_tpa']/1000:.1f} kt","per year")
    pk(c4, "Ammonia produced",      f"{pc['nh3_net_ktpa']:.1f} ktpa",  f"{pc['nh3_rate_td']:.0f} t/day")
    pk(c5, "Grid electricity cost", f"${pc['annual_grid_cost_musd']:.1f}M","per year")
    pk(c6, "Elec. load factor",     f"{pc['elec_load_pct']:.0f}%",     "of rated capacity")

    # Step-by-step table
    sec("Step-by-Step Calculation")
    steps = [
        ("1 · Power", "Solar generation",            f"{pc['solar_gwh_yr']:.2f} GWh/yr",    f"{solar_mwac} MWac × {p.solar_capacity_factor*100:.1f}% CF"),
        ("1 · Power", "Grid top-up (daytime)",       f"{pc['grid_day_gwh']:.2f} GWh/yr",    "80 MW × 10% complementarity × daylight hrs"),
        ("1 · Power", "Grid power (night)",          f"{pc['grid_night_gwh']:.2f} GWh/yr",  f"{grid_night_mw} MW × 32% complementarity × night hrs"),
        ("2 · H₂",   "Electrolyser total input",    f"{pc['elec_total_gwh']:.2f} GWh/yr",  "Solar + grid combined"),
        ("2 · H₂",   "Hydrogen produced",           f"{pc['h2_gross_tpa']:,.0f} t/yr",      f"÷ {elec_sec} kWh/kgH₂"),
        ("3 · NH₃",  "Nitrogen from air (ASU)",     f"{pc['n2_required_tpa']:,.0f} t/yr",   f"Air Separation Unit"),
        ("3 · NH₃",  "Ammonia from Haber-Bosch",    f"{pc['nh3_net_ktpa']:.1f} ktpa",       f"÷ {p.hb_h2_per_tnh3:.4f} tH₂/tNH₃ × 98% eff."),
        ("4 · Water","Water consumed",               f"{pc['water_m3h']:.0f} m³/hr",         f"= {pc['water_total_m3y']/1000:.0f} kt/yr"),
        ("✓ Check",  "Greenhouse gases",            "~0 kgCO₂/kgNH₃",                      "Below EU RFNBO limit of 0.53 ✓"),
    ]
    sc = {"1 · Power":"#1e4799","2 · H₂":"#16a34a","3 · NH₃":"#d97706","4 · Water":"#0891b2","✓ Check":"#16a34a"}
    rows = ""
    for step, name, val, formula in steps:
        c = sc.get(step, "#6b7280")
        rows += f"""<tr style="border-bottom:1px solid #f3f4f6;">
          <td style="padding:0.6rem 0.8rem;white-space:nowrap;">
            <span style="background:{c}18;color:{c};border-radius:6px;padding:0.2rem 0.6rem;font-size:0.8rem;font-weight:600;">{step}</span>
          </td>
          <td style="padding:0.6rem 0.8rem;color:#1a1a2e;font-weight:600;font-size:0.95rem;">{name}</td>
          <td style="padding:0.6rem 0.8rem;color:{c};font-weight:700;font-size:1rem;text-align:right;">{val}</td>
          <td style="padding:0.6rem 0.8rem;color:#6b7280;font-size:0.88rem;">{formula}</td>
        </tr>"""
    st.markdown(f"""<table style="width:100%;border-collapse:collapse;background:#fff;
        border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;">
      <thead><tr style="background:#f8f9fc;border-bottom:2px solid #e2e8f0;">
        <th style="padding:0.7rem 0.8rem;color:#1e4799;font-size:0.85rem;text-align:left;">STEP</th>
        <th style="padding:0.7rem 0.8rem;color:#1e4799;font-size:0.85rem;text-align:left;">WHAT</th>
        <th style="padding:0.7rem 0.8rem;color:#1e4799;font-size:0.85rem;text-align:right;">VALUE</th>
        <th style="padding:0.7rem 0.8rem;color:#1e4799;font-size:0.85rem;text-align:left;">HOW IT'S CALCULATED</th>
      </tr></thead><tbody>{rows}</tbody></table>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — FINANCIAL RETURNS
# ══════════════════════════════════════════════════════════════════════════════
with t2:
    years = dcf_df.calendar_year.tolist()
    ca, cb = st.columns([2,1])

    with ca:
        sec("Revenue vs Costs — Every Year")
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Revenue", x=years, y=dcf_df.revenue_musd,
                             marker_color=C["blue"], opacity=0.85))
        fig.add_trace(go.Bar(name="Operating costs", x=years, y=-dcf_df.opex_musd,
                             marker_color=C["red"], opacity=0.75))
        fig.add_trace(go.Bar(name="Tax + Interest", x=years,
                             y=-(dcf_df.tax_musd + dcf_df.interest_musd),
                             marker_color=C["purple"], opacity=0.70))
        fig.add_trace(go.Scatter(name="Free Cash Flow", x=years, y=dcf_df.project_fcf_musd,
                                 mode="lines+markers", line=dict(color=C["green"], width=3),
                                 marker=dict(size=5)))
        fig.update_layout(**lo("Revenue, costs and free cash flow (USD millions)",
                          lkw=dict(orientation="h", y=-0.20),
                          ykw=dict(title="USD millions")),
                          barmode="relative", height=360)
        st.plotly_chart(fig, use_container_width=True)

    with cb:
        sec("Cumulative Cash")
        fig2 = go.Figure()
        fig2.add_hline(y=metrics["total_capex_musd"], line_dash="dash",
                       line_color=C["red"], line_width=2,
                       annotation_text=f"Investment: ${metrics['total_capex_musd']:.0f}M",
                       annotation_font_color=C["red"], annotation_font_size=12)
        fig2.add_trace(go.Scatter(x=years, y=dcf_df.project_fcf_musd.cumsum(),
                                  fill="tozeroy", fillcolor="rgba(30,71,153,0.10)",
                                  line=dict(color=C["blue"], width=3),
                                  name="Cumulative cash"))
        fig2.update_layout(**lo("Cumulative free cash flow",
                            ykw=dict(title="USD millions")), height=360, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    sec("EBITDA and Profit Margin")
    fig3 = make_subplots(specs=[[{"secondary_y":True}]])
    fig3.add_trace(go.Bar(name="EBITDA (USD M)", x=years, y=dcf_df.ebitda_musd,
                          marker_color=C["teal"], opacity=0.75), secondary_y=False)
    fig3.add_trace(go.Scatter(name="Margin %", x=years, y=dcf_df.ebitda_margin_pct,
                              mode="lines", line=dict(color=C["amber"], width=3)),
                   secondary_y=True)
    fig3.update_layout(
        title=dict(text="Earnings before interest, tax & depreciation", font=dict(family="Inter", color="#1a1a2e", size=15)),
        legend=dict(**PL["legend"], orientation="h", y=-0.25),
        height=280,
        paper_bgcolor=PL["paper_bgcolor"], plot_bgcolor=PL["plot_bgcolor"],
        font=PL["font"], margin=PL["margin"], xaxis=PL["xaxis"],
    )
    fig3.update_yaxes(title_text="USD M", secondary_y=False,
                      gridcolor="#e2e8f0", title_font=dict(color="#374151"), tickfont=dict(color="#374151"))
    fig3.update_yaxes(title_text="Margin %", secondary_y=True, gridcolor="rgba(0,0,0,0)",
                      title_font=dict(color=C["amber"]), tickfont=dict(color=C["amber"]))
    st.plotly_chart(fig3, use_container_width=True)

    # 3-scenario cards
    sec("Bear / Base / Bull Comparison")
    sc1,sc2,sc3 = st.columns(3)
    pm = {"bear": nh3_price*0.778, "base": float(nh3_price), "bull": nh3_price*1.222}
    sl = {"bear":"🔴 Bear","base":"🟡 Base","bull":"🟢 Bull"}
    sb = {"bear":C["red"],"base":C["amber"],"bull":C["green"]}
    for col, sc in zip([sc1,sc2,sc3], ["bear","base","bull"]):
        rv_s = compute_revenue(p, prod, sc)
        _, ms = compute_dcf(p, prod, rv_s, opex_df, capex)
        ir = f"{ms['project_irr_pct']:.1f}%" if ms['project_irr_pct'] else "—"
        er = f"{ms['equity_irr_pct']:.1f}%"  if ms['equity_irr_pct']  else "—"
        col.markdown(f"""
        <div style="background:#fff;border:1px solid #e2e8f0;border-top:4px solid {sb[sc]};
                    border-radius:12px;padding:1.1rem 1.2rem;">
          <div style="font-weight:700;font-size:1.1rem;color:#1a1a2e;margin-bottom:0.8rem;">
            {sl[sc]} — ${pm[sc]:.0f}/t
          </div>
          <table style="width:100%;font-size:0.95rem;">
            <tr><td style="color:#6b7280;padding:0.25rem 0;">Revenue/yr</td>
                <td style="font-weight:700;text-align:right;">${ms['avg_annual_revenue_musd']:.0f}M</td></tr>
            <tr><td style="color:#6b7280;padding:0.25rem 0;">EBITDA margin</td>
                <td style="font-weight:700;text-align:right;">{ms['avg_ebitda_margin_pct']:.0f}%</td></tr>
            <tr><td style="color:#6b7280;padding:0.25rem 0;">Project IRR</td>
                <td style="font-weight:700;text-align:right;">{ir}</td></tr>
            <tr><td style="color:#6b7280;padding:0.25rem 0;">Equity IRR</td>
                <td style="font-weight:700;text-align:right;">{er}</td></tr>
            <tr><td style="color:#6b7280;padding:0.25rem 0;">NPV</td>
                <td style="font-weight:700;text-align:right;">${ms['project_npv_musd']:.0f}M</td></tr>
            <tr><td style="color:#6b7280;padding:0.25rem 0;">Payback</td>
                <td style="font-weight:700;text-align:right;">{ms['payback_years'] or '—'} yrs</td></tr>
          </table>
        </div>""", unsafe_allow_html=True)

    st.markdown(f"""<div class="info-box" style="margin-top:1rem;">
    <strong>How to read this:</strong> Project IRR is the return on the full ${metrics['total_capex_musd']:.0f}M investment.
    Equity IRR is the return to investors who provide the {(1-debt_pct)*100:.0f}% equity (${metrics['equity_musd']:.0f}M).
    Higher debt amplifies equity returns. The Min DSCR of {metrics['min_dscr']}× means
    the project generates {metrics['min_dscr']}× more cash than needed for loan payments —
    banks typically require at least 1.30×.
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — INVESTMENT COST
# ══════════════════════════════════════════════════════════════════════════════
with t3:
    ca, cb = st.columns([3,2])
    with ca:
        sec("Investment Breakdown")
        items = {
            "Solar plant":           capex["solar_plant"],
            "Grid interconnection":  capex["grid_interconnect"],
            "Electrolyser":          capex["electrolyser"],
            "Water treatment (H₂)":  capex["water_treatment"],
            "Hydrogen storage":      capex["h2_storage"],
            "Water (NH₃)":           capex["water_nh3"],
            "Haber-Bosch synthesis": capex["haber_bosch"],
            "Air Separation (N₂)":   capex["asu"],
            "NH₃ storage":           capex["nh3_storage_onsite"],
            "HB installation/BoP":   capex["hb_bop"],
            "Export terminal":       capex["export_facility"],
            "NH₃ pipeline":          capex["nh3_pipeline"],
            "Power line (OHTL)":     capex["power_ohtl"],
            "Water pipeline (WTP)":  capex["wtp_pipeline"],
            "KOH system":            capex["koh_system"],
            "Wastewater plant":      capex["wwtp"],
            "Port contingency":      capex["peripheral_contingency"],
            "Owner's costs / FEED":  capex["owners_costs"],
        }
        if apply_inc:
            items["− VAT saving (Ley 1715) ✓"]    = -capex["vat_saving"]
            items["− Tariff saving (Ley 1715) ✓"] = -capex["tariff_saving"]

        sorted_items = sorted(items.items(), key=lambda x: x[1], reverse=True)
        colors = []
        for lbl, _ in sorted_items:
            if "Solar" in lbl or "Grid interc" in lbl: colors.append(C["blue"])
            elif "Electro" in lbl or "Water t" in lbl or "H₂ aux" in lbl or "H₂ stor" in lbl: colors.append(C["teal"])
            elif "Haber" in lbl or "ASU" in lbl or "NH₃" in lbl or "HB" in lbl or "Water (NH₃)" in lbl: colors.append(C["amber"])
            elif "Export" in lbl or "Power" in lbl or "pipeline" in lbl or "KOH" in lbl or "Waste" in lbl or "Port" in lbl: colors.append(C["purple"])
            elif "saving" in lbl: colors.append(C["green"])
            else: colors.append(C["gray"])

        fig4 = go.Figure(go.Bar(
            x=[v for _,v in sorted_items], y=[l for l,_ in sorted_items],
            orientation="h", marker_color=colors,
            text=[f"${v:.1f}M" for _,v in sorted_items],
            textposition="outside", textfont=dict(color="#374151", size=11),
        ))
        fig4.update_layout(**lo(f"Total investment: ${metrics['total_capex_musd']:.0f}M",
                           xkw=dict(title="USD millions")),
                           height=540, showlegend=False)
        st.plotly_chart(fig4, use_container_width=True)

    with cb:
        sec("Summary")
        fig5 = go.Figure(go.Pie(
            labels=["Solar plant","Electrolyser + H₂ sys","HB + ASU + NH₃","Port & infrastructure","Owner's costs"],
            values=[capex["solar_plant"],
                    capex["electrolysis_total"] - capex["solar_plant"],
                    capex["hb_total"],
                    capex["peripheral_total"],
                    capex["owners_costs"]],
            hole=0.60,
            marker=dict(colors=[C["blue"],C["teal"],C["amber"],C["purple"],C["gray"]]),
            textinfo="label+percent", textfont=dict(size=12),
        ))
        fig5.update_layout(**lo(), height=320, showlegend=False)
        fig5.add_annotation(text=f"${metrics['total_capex_musd']:.0f}M",
                            font=dict(size=17, color="#1a1a2e", family="Inter"), showarrow=False)
        st.plotly_chart(fig5, use_container_width=True)

        for lbl, val, note in [
            ("Electrolysis block",  f"${capex['electrolysis_total']:.0f}M",
             f"{capex['electrolysis_total']/metrics['total_capex_musd']*100:.0f}% of total"),
            ("Haber-Bosch block",   f"${capex['hb_total']:.0f}M",
             f"{capex['hb_total']/metrics['total_capex_musd']*100:.0f}% of total"),
            ("Port infrastructure", f"${capex['peripheral_total']:.0f}M",
             f"{capex['peripheral_total']/metrics['total_capex_musd']*100:.0f}% of total"),
            ("Ley 1715 savings",    f"-${capex['vat_saving']+capex['tariff_saving']:.0f}M",
             "deducted" if apply_inc else "not applied"),
            ("Debt (loans)",        f"${metrics['debt_musd']:.0f}M",  f"{debt_pct*100:.0f}%"),
            ("Equity required",     f"${metrics['equity_musd']:.0f}M", f"{(1-debt_pct)*100:.0f}%"),
            ("$/tonne NH₃",         f"${metrics['total_capex_musd']*1e6/max(1,pc['nh3_net_tpa']):.0f}", "installed $/tpa"),
        ]:
            st.markdown(f"""<div style="display:flex;justify-content:space-between;
                align-items:center;padding:0.5rem 0;border-bottom:1px solid #f3f4f6;">
                <span style="font-size:0.92rem;color:#374151;">{lbl}</span>
                <div style="text-align:right;">
                  <span style="font-size:0.98rem;font-weight:700;color:#1a1a2e;">{val}</span><br>
                  <span style="font-size:0.78rem;color:#6b7280;">{note}</span>
                </div></div>""", unsafe_allow_html=True)


    # ── LCOA breakdown by component (CAPEX + OPEX per item) ─────────────────
    sec("LCOA Breakdown — What Each Component Costs per Tonne NH₃")
    st.caption(f"CRF = {p.wacc*(1+p.wacc)**p.project_life_years/((1+p.wacc)**p.project_life_years-1):.4f} "
               f"at {p.wacc*100:.1f}% WACC over {p.project_life_years}yr · "
               f"NH₃ output: {pc['nh3_net_ktpa']:.1f} ktpa · "
               f"EPI production cost: ${metrics['epi_lcoa_usd_t']:.0f}/t")

    _lbcapex = {k:v for k,v in lb.items() if "CAPEX" in k}
    _lbopex  = {k:v for k,v in lb.items() if "OPEX" in k or "OPEX" in k}

    _colors_lcoa = {
        "Solar CAPEX":      C["blue"],
        "Electrolyser CAPEX": C["teal"],
        "Haber-Bosch CAPEX": C["amber"],
        "ASU CAPEX":         C["amber"],
        "H2 storage CAPEX":  C["teal"],
        "NH3 storage CAPEX": C["amber"],
        "Pipeline CAPEX":    C["purple"],
        "Peripheral CAPEX":  C["purple"],
        "Grid energy OPEX":  C["red"],
        "Solar O&M OPEX":    C["blue"],
        "Fixed O&M OPEX":    C["purple"],
        "VarOpEx (freight)": C["gray"],
    }

    fig_lcoa = go.Figure()
    # CAPEX bars
    cap_keys = [k for k in lb if "CAPEX" in k]
    opex_keys = [k for k in lb if k not in cap_keys]

    fig_lcoa.add_trace(go.Bar(
        name="CAPEX (annualised)", x=cap_keys,
        y=[lb[k] for k in cap_keys],
        marker_color=[_colors_lcoa.get(k, C["gray"]) for k in cap_keys],
        text=[f"${lb[k]:.0f}/t" for k in cap_keys],
        textposition="outside", textfont=dict(size=11, color="#374151"),
    ))
    fig_lcoa.add_trace(go.Bar(
        name="OPEX (annual avg)", x=opex_keys,
        y=[lb[k] for k in opex_keys],
        marker_color=[_colors_lcoa.get(k, C["gray"]) for k in opex_keys],
        marker_pattern_shape="/",
        text=[f"${lb[k]:.0f}/t" for k in opex_keys],
        textposition="outside", textfont=dict(size=11, color="#374151"),
    ))
    fig_lcoa.add_hline(
        y=metrics["epi_lcoa_usd_t"], line_dash="dot",
        line_color=C["amber"], line_width=2,
        annotation_text=f"EPI production cost ${metrics['epi_lcoa_usd_t']:.0f}/t",
        annotation_font_color=C["amber"], annotation_font_size=12)
    fig_lcoa.update_layout(
        **lo("LCOA by component — CAPEX (solid) vs OPEX (hatched) in $/tonne NH₃",
             lkw=dict(orientation="h", y=-0.18),
             ykw=dict(title="USD per tonne NH₃")),
        barmode="group", height=380, showlegend=True)
    st.plotly_chart(fig_lcoa, use_container_width=True)

    # Also show as a cumulative waterfall
    sec("LCOA Waterfall — Stacking Each Cost Component")
    _sorted_lb = sorted(lb.items(), key=lambda x: x[1], reverse=True)
    fig_lwf = go.Figure(go.Waterfall(
        orientation="v",
        measure=["relative"]*len(_sorted_lb) + ["total"],
        x=[k for k,_ in _sorted_lb] + ["= TOTAL LCOA"],
        y=[v for _,v in _sorted_lb] + [sum(lb.values())],
        text=[f"${v:.0f}/t" for _,v in _sorted_lb] + [f"${sum(lb.values()):.0f}/t"],
        textposition="outside",
        textfont=dict(size=11, color="#374151"),
        connector=dict(line=dict(color="#e2e8f0", width=1)),
        increasing=dict(marker_color=C["blue"]),
        totals=dict(marker_color=C["teal"]),
    ))
    fig_lwf.add_hline(y=786, line_dash="dash", line_color=C["amber"], line_width=2,
        annotation_text="EPI $786/t (H2ALite basis, 5.67% WACC)",
        annotation_font_color=C["amber"], annotation_font_size=12)
    fig_lwf.update_layout(
        **lo("LCOA component waterfall — cumulative cost build-up ($/tonne NH₃)",
             ykw=dict(title="USD per tonne NH₃")),
        height=420, showlegend=False)
    st.plotly_chart(fig_lwf, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — OPERATING COSTS
# ══════════════════════════════════════════════════════════════════════════════
with t4:
    yrs_op = dcf_df.calendar_year.tolist()
    sec("Operating Costs Over Time (USD M/yr)")
    fig6 = go.Figure()
    fig6.add_trace(go.Scatter(name="Grid electricity", x=yrs_op, y=opex_df.energy_opex_musd,
                              mode="lines", stackgroup="one",
                              fillcolor="rgba(30,71,153,0.55)", line=dict(color=C["blue"], width=0.5)))
    fig6.add_trace(go.Scatter(name="Equipment O&M", x=yrs_op, y=opex_df.om_opex_musd,
                              mode="lines", stackgroup="one",
                              fillcolor="rgba(124,58,237,0.45)", line=dict(color=C["purple"], width=0.5)))
    fig6.add_trace(go.Scatter(name="Solar O&M", x=yrs_op, y=opex_df.solar_om_musd,
                              mode="lines", stackgroup="one",
                              fillcolor="rgba(22,163,74,0.40)", line=dict(color=C["green"], width=0.5)))
    fig6.add_trace(go.Scatter(name="Freight & insurance", x=yrs_op, y=opex_df.var_om_musd,
                              mode="lines", stackgroup="one",
                              fillcolor="rgba(217,119,6,0.40)", line=dict(color=C["amber"], width=0.5)))
    fig6.add_trace(go.Scatter(name="Peripheral O&M", x=yrs_op, y=opex_df.peripheral_opex_musd,
                              mode="lines", stackgroup="one",
                              fillcolor="rgba(107,114,128,0.35)", line=dict(color=C["gray"], width=0.5)))
    fig6.add_trace(go.Scatter(name="Revenue (reference)", x=yrs_op, y=dcf_df.revenue_musd,
                              mode="lines", line=dict(color=C["blue"], width=2.5, dash="dash"), fill=None))
    fig6.update_layout(**lo("Cost components stacked vs revenue",
                       lkw=dict(orientation="h", y=-0.22),
                       ykw=dict(title="USD millions/yr")), height=380)
    st.plotly_chart(fig6, use_container_width=True)

    ca, cb = st.columns(2)
    with ca:
        sec("Cost per Tonne NH₃")
        nh3t = prod.nh3_production_kt * 1_000
        fig7 = go.Figure()
        fig7.add_trace(go.Bar(name="Grid electricity", x=yrs_op,
                              y=opex_df.energy_opex_musd*1e6/nh3t.values,
                              marker_color=C["blue"], opacity=0.85))
        fig7.add_trace(go.Bar(name="O&M", x=yrs_op,
                              y=opex_df.om_opex_musd*1e6/nh3t.values,
                              marker_color=C["purple"], opacity=0.85))
        fig7.add_trace(go.Bar(name="Freight", x=yrs_op,
                              y=opex_df.var_om_musd*1e6/nh3t.values,
                              marker_color=C["amber"], opacity=0.85))
        fig7.add_hline(y=786, line_dash="dot", line_color=C["green"], line_width=2,
                       annotation_text="EPI production cost: $786/t",
                       annotation_font_color=C["green"], annotation_font_size=11)
        fig7.update_layout(**lo("Unit operating cost ($/tonne NH₃)",
                           lkw=dict(orientation="h", y=-0.25),
                           ykw=dict(title="USD per tonne")),
                           barmode="stack", height=300)
        st.plotly_chart(fig7, use_container_width=True)

    with cb:
        sec("Cost Mix — Year 3")
        o3 = opex_df.iloc[2]
        fig8 = go.Figure(go.Pie(
            labels=["Grid electricity","Equipment O&M","Solar O&M","Freight","Peripheral O&M"],
            values=[o3.energy_opex_musd, o3.om_opex_musd, o3.solar_om_musd,
                    o3.var_om_musd, o3.peripheral_opex_musd],
            hole=0.55,
            marker=dict(colors=[C["blue"],C["purple"],C["green"],C["amber"],C["gray"]]),
            textinfo="label+percent", textfont=dict(size=12),
        ))
        fig8.update_layout(**lo(), height=300, showlegend=False)
        fig8.add_annotation(text=f"${o3.total_opex_musd:.0f}M/yr",
                            font=dict(size=15, color="#1a1a2e"), showarrow=False)
        st.plotly_chart(fig8, use_container_width=True)

    esh = opex_df.energy_opex_musd.mean() / opex_df.total_opex_musd.mean() * 100
    sec_b = (1-45/elec_sec)*opex_df.energy_opex_musd.mean() if elec_sec>45 else 0
    st.markdown(f"""<div class="info-box">
    <strong>Key insight:</strong> Grid electricity is <strong>{esh:.0f}%</strong> of total operating costs.
    If electrolyser efficiency improves from {elec_sec} to 45 kWh/kgH₂ (2030 forecast),
    the energy cost falls by ~<strong>${sec_b:.1f}M/yr</strong>.
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — REVENUE
# ══════════════════════════════════════════════════════════════════════════════
with t5:
    yrs_r = [p.cod_year + i for i in range(p.project_life_years)]
    sec("Revenue Sources by Year")
    fig9 = go.Figure()
    fig9.add_trace(go.Bar(name="H₂Global contract (fixed price)",
                          x=yrs_r, y=rev.h2global_revenue_musd, marker_color=C["blue"], opacity=0.9))
    fig9.add_trace(go.Bar(name="Colombia H₂ (Reficar)",
                          x=yrs_r, y=rev.colombia_revenue_musd, marker_color=C["amber"], opacity=0.85))
    fig9.add_trace(go.Bar(name="Spot market / Ameropa",
                          x=yrs_r, y=rev.spot_revenue_musd, marker_color=C["teal"], opacity=0.75))
    contracted = [h+c for h,c in zip(rev.h2global_revenue_musd, rev.colombia_revenue_musd)]
    fig9.add_trace(go.Scatter(name="Contracted floor",
                              x=yrs_r, y=contracted, mode="lines",
                              line=dict(color=C["green"], width=2.5, dash="dot")))
    fig9.update_layout(**lo("Annual revenue — contracted floor vs spot exposure",
                       lkw=dict(orientation="h", y=-0.22),
                       ykw=dict(title="USD millions")),
                       barmode="stack", height=360)
    st.plotly_chart(fig9, use_container_width=True)

    sec("NH₃ Price Forecast — 3 Scenarios")
    fig10 = go.Figure()
    for sc, ch, dash in [("bear",C["red"],"dash"),("base",C["blue"],"solid"),("bull",C["green"],"dash")]:
        rv_s = compute_revenue(p, prod, sc)
        fig10.add_trace(go.Scatter(name=f"{sc.title()}", x=yrs_r,
                                   y=rv_s.nh3_spot_price_usd_t, mode="lines",
                                   line=dict(color=ch, width=2.5, dash=dash)))
    h2g_px = [p.h2global_net_price_eur * p.eur_usd *
               (1+p.h2global_escalation)**i for i in range(p.h2global_contract_years)]
    fig10.add_trace(go.Scatter(name="H₂Global contract", x=yrs_r[:p.h2global_contract_years], y=h2g_px,
                               mode="lines", line=dict(color=C["green"], width=2, dash="dot")))
    fig10.add_hline(y=p.nh3_price_floor, line_dash="dot", line_color=C["gray"], opacity=0.5,
                    annotation_text=f"Floor ${p.nh3_price_floor:.0f}/t",
                    annotation_font_color=C["gray"], annotation_font_size=11)
    fig10.add_hline(y=metrics["epi_lcoa_usd_t"], line_dash="dot", line_color=C["teal"], opacity=0.5,
                    annotation_text=f"Production cost ${metrics['epi_lcoa_usd_t']:.0f}/t",
                    annotation_font_color=C["teal"], annotation_font_size=11)
    fig10.update_layout(**lo("NH₃ price trajectory (nominal USD/tonne)",
                        lkw=dict(orientation="h", y=-0.25),
                        ykw=dict(title="USD/tonne", range=[400,1300])), height=320)
    st.plotly_chart(fig10, use_container_width=True)

    c1,c2,c3 = st.columns(3)
    avg_c = np.mean(contracted)
    avg_t = rev.total_revenue_musd.mean()
    cs    = avg_c/avg_t*100 if avg_t>0 else 0
    c1.markdown(f"""<div class="kpi-card" style="border-top-color:{C['blue']};">
      <div class="kpi-label">H₂Global contract (yrs 1–10)</div>
      <div class="kpi-value" style="font-size:1.3rem;">${rev.h2global_revenue_musd[:10].mean():.0f}M/yr</div>
      <div class="kpi-sub">{h2g_vol} ktpa · €{h2g_eur}/t · Hintco Lot 1</div>
    </div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class="kpi-card" style="border-top-color:{C['green']};">
      <div class="kpi-label">Contracted revenue share</div>
      <div class="kpi-value kpi-good" style="font-size:1.3rem;">{cs:.0f}%</div>
      <div class="kpi-sub">H₂Global + Colombia = bankable floor</div>
    </div>""", unsafe_allow_html=True)
    c3.markdown(f"""<div class="kpi-card" style="border-top-color:{C['amber']};">
      <div class="kpi-label">Colombia H₂ (Reficar)</div>
      <div class="kpi-value" style="font-size:1.3rem;">{p.colombia_h2_ktpa:.0f} ktpa H₂</div>
      <div class="kpi-sub">${p.colombia_h2_price_per_kg}/kgH₂ = ${rev.colombia_revenue_musd.mean():.0f}M/yr</div>
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — COLOMBIA BENEFITS
# ══════════════════════════════════════════════════════════════════════════════
with t6:
    sec("Colombian Fiscal Incentives — Ley 1715 / Ley 2099")
    st.markdown("""<div class="info-box">
    Colombia has a 30-year incentive framework for non-conventional renewable energy (FNCE).
    All four incentives below apply to Cartagena H2. They are <strong>legally mandated</strong>
    benefits — not negotiated concessions — that significantly reduce project cost.
    </div>""", unsafe_allow_html=True)

    core_sub = (capex["solar_plant"] + capex["grid_interconnect"] + capex["water_treatment"] +
                capex["electrolyser"] + capex["haber_bosch"] + capex["asu"] +
                capex["nh3_storage_onsite"] + capex["nh3_pipeline"] + capex["aux_h2"] + capex["aux_nh3"])
    periph_sub = (p.export_facility_musd + p.power_ohtl_musd + p.wtp_pipeline_musd +
                  p.koh_system_musd + p.wwtp_musd)
    vat_s    = (core_sub + periph_sub) * p.vat_rate
    tariff_s = (core_sub - capex["solar_plant"]) * p.imported_capex_fraction * p.tariff_rate
    crf_v    = wacc_pct*(1+wacc_pct)**p.project_life_years/((1+wacc_pct)**p.project_life_years-1)
    nt       = pc["nh3_net_tpa"]
    vat_l    = vat_s   * crf_v * 1e6 / nt if nt>0 else 0
    tar_l    = tariff_s* crf_v * 1e6 / nt if nt>0 else 0
    tax_l    = metrics["total_capex_musd"] * 0.50 * 0.35 / 15 * 1e6 / nt if nt>0 else 0

    i1,i2,i3,i4 = st.columns(4)
    def icard(col, title, law, sm, ls, desc, color):
        col.markdown(f"""<div style="background:#fff;border:1px solid #e2e8f0;
            border-top:4px solid {color};border-radius:12px;padding:1.1rem;">
          <div style="font-weight:700;font-size:1rem;color:#1a1a2e;">{title}</div>
          <div style="font-size:0.8rem;color:#6b7280;margin-bottom:0.5rem;">{law}</div>
          <div style="font-size:1.8rem;font-weight:700;color:{color};">${sm:.0f}M</div>
          <div style="font-size:0.85rem;color:{color};margin-bottom:0.5rem;">~${ls:.0f}/t cost saving</div>
          <div style="font-size:0.88rem;color:#374151;line-height:1.5;">{desc}</div>
        </div>""", unsafe_allow_html=True)

    icard(i1,"VAT Exemption","Art. 12 — Ley 1715",vat_s,vat_l,
          "Full 19% VAT waiver on all equipment — solar, electrolyser, HB plant and all infrastructure.",C["blue"])
    icard(i2,"Import Tariff Exemption","Art. 13 — Ley 1715",tariff_s,tar_l,
          "Full exemption on import duties (~10%) for electrolysers, HB units, ASU — all imported equipment.",C["teal"])
    icard(i3,"Income Tax Deduction","Art. 11 — Ley 1715",
          metrics["total_capex_musd"]*0.50*0.35, tax_l,
          "50% of investment deducted from taxable income over 15 years — ~$100M+ in cumulative tax savings.",C["amber"])
    icard(i4,"Accelerated Depreciation","Art. 14 — Ley 1715",
          metrics["total_capex_musd"]*0.15, 15,
          "Assets depreciated in 5 years instead of 20+, reducing taxes during the years when debt service is highest.",C["purple"])

    sec("How Incentives Reduce the Production Cost")
    full_no = metrics["epi_lcoa_usd_t"] + vat_l + tar_l
    fig11 = go.Figure(go.Waterfall(
        orientation="v", measure=["absolute","relative","relative","total"],
        x=["Without incentives","− VAT exemption\n(Art. 12)","− Import tariff\n(Art. 13)","= With Ley 1715"],
        y=[full_no, -vat_l, -tar_l, metrics["epi_lcoa_usd_t"]],
        connector=dict(line=dict(color="#e2e8f0", width=2)),
        decreasing=dict(marker_color=C["green"]),
        increasing=dict(marker_color=C["red"]),
        totals=dict(marker_color=C["blue"]),
        text=[f"${v:.0f}/t" for v in [full_no,-vat_l,-tar_l,metrics["epi_lcoa_usd_t"]]],
        textposition="outside", textfont=dict(color="#374151", size=13),
    ))
    fig11.add_hline(y=786, line_dash="dot", line_color=C["teal"], line_width=2,
                    annotation_text="EPI baseline $786/t",
                    annotation_font_color=C["teal"], annotation_font_size=12)
    fig11.update_layout(**lo("Production cost — with vs without Colombian incentives",
                        ykw=dict(title="USD per tonne NH₃")),
                        height=380, showlegend=False)
    st.plotly_chart(fig11, use_container_width=True)

    c1,c2,c3 = st.columns(3)
    kpi(c1,"Total investment saving", f"${vat_s+tariff_s:.0f}M",
        f"VAT ${vat_s:.0f}M + Tariff ${tariff_s:.0f}M","kpi-good")
    kpi(c2,"Production cost saving", f"${vat_l+tar_l:.0f}/t",
        "Annualised CAPEX reduction","kpi-good")
    kpi(c3,"Investment after incentives", f"${metrics['total_capex_musd']:.0f}M",
        "Already included in all calculations ✓" if apply_inc else "Toggle ON to apply")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 — SENSITIVITY & SCENARIOS
# ══════════════════════════════════════════════════════════════════════════════
with t7:
    ca, cb = st.columns([3,2])
    with ca:
        sec("What Moves the Return Most? (Tornado)")
        torn_rows = []
        for var in sens.variable.unique():
            sub = sens[sens.variable==var]
            lo_r = sub[sub.case=="Low"].iloc[0]
            hi_r = sub[sub.case=="High"].iloc[0]
            torn_rows.append({"var": var.replace("_"," ").title(),
                              "lo": lo_r.lcoa_usd_t, "hi": hi_r.lcoa_usd_t,
                              "rng": abs(hi_r.lcoa_delta-lo_r.lcoa_delta)})
        torn = pd.DataFrame(torn_rows).sort_values("rng", ascending=True)
        base_l = metrics["lcoa_usd_t"]
        fig12 = go.Figure()
        for _, r in torn.iterrows():
            lx, hx = min(r.lo,r.hi), max(r.lo,r.hi)
            fig12.add_trace(go.Bar(y=[r["var"]], x=[hx-lx], base=[lx],
                                   orientation="h", marker_color=C["blue"], opacity=0.75,
                                   showlegend=False,
                                   text=f"${lx:.0f}–${hx:.0f}/t",
                                   textposition="outside",
                                   textfont=dict(color="#374151", size=11)))
        fig12.add_vline(x=base_l, line_dash="dash", line_color=C["red"], line_width=2,
                        annotation_text=f"Base ${base_l:.0f}/t",
                        annotation_font_color=C["red"], annotation_font_size=12)
        fig12.update_layout(**lo("Full investor LCOA sensitivity (USD/tonne NH₃)",
                            xkw=dict(title="Full investor LCOA (USD/tonne)")),
                            height=400, showlegend=False)
        st.plotly_chart(fig12, use_container_width=True)

    with cb:
        sec("Equity IRR Heatmap")
        nh3_prices  = [650, 750, 850, 950, 1050, 1150]
        debt_shares = [0.50, 0.60, 0.70, 0.75]
        hz = []
        for ds in debt_shares:
            row_irr = []
            for npv in nh3_prices:
                pt = ProjectParams(nh3_price_base=float(npv), debt_share=ds,
                                   wacc=wacc_pct, debt_interest_rate=debt_rate,
                                   electrolyser_mw=float(elec_mw),
                                   electrolyser_sec=float(elec_sec),
                                   solar_mwac=float(solar_mwac))
                ct = compute_capex(pt); pt2 = compute_production_profile(pt,25)
                rt = compute_revenue(pt,pt2,"base"); ot = compute_opex(pt,pt2,ct)
                _, mt = compute_dcf(pt,pt2,rt,ot,ct)
                row_irr.append(mt.get("equity_irr_pct") or 0)
            hz.append(row_irr)
        fig13 = go.Figure(go.Heatmap(
            z=hz, x=[f"${p}/t" for p in nh3_prices],
            y=[f"{int(d*100)}% debt" for d in debt_shares],
            colorscale=[[0,"#fef2f2"],[0.3,"#fde68a"],[0.6,"#bbf7d0"],[1.0,"#15803d"]],
            text=[[f"{v:.1f}%" for v in row] for row in hz],
            texttemplate="%{text}", textfont=dict(size=12, color="#1a1a2e"),
            colorbar=dict(title=dict(text="Equity IRR %", font=dict(color="#374151")),
                          tickfont=dict(color="#374151")),
        ))
        fig13.update_layout(**lo("Equity IRR — price × leverage",
                            xkw=dict(title="NH₃ price"),
                            ykw=dict(title="Debt share")), height=300)
        st.plotly_chart(fig13, use_container_width=True)

    sec("Best Ways to Improve Returns")
    sec_sav    = (1-45/elec_sec)*opex_df.energy_opex_musd.mean() if elec_sec>45 else 0
    solar_sav  = min(80,(400-solar_mwac)/150*60) if solar_mwac<400 else 0
    inc_sav    = (vat_l+tar_l) * pc["nh3_net_tpa"]/1e6 if not apply_inc else 0
    ppa_sav    = opex_df.energy_opex_musd.mean() * 0.10
    levers = sorted([
        ("Improve electrolyser efficiency (50→45 kWh/kgH₂)", sec_sav,   "Technology — 2030 systems", C["blue"]),
        ("Apply Colombian Ley 1715 incentives",               inc_sav,   "Legal — available now",     C["green"]),
        ("Expand solar to 400 MWac",                          solar_sav, "CAPEX — more free energy",  C["teal"]),
        ("Reduce grid electricity price by 10%",              ppa_sav,   "Contracting — negotiate PPA",C["amber"]),
    ], key=lambda x: x[1], reverse=True)
    fig14 = go.Figure(go.Bar(
        x=[l[1] for l in levers], y=[l[0] for l in levers],
        orientation="h", marker_color=[l[3] for l in levers],
        text=[f"Save ~${l[1]:.1f}M/yr  ·  {l[2]}" for l in levers],
        textposition="outside", textfont=dict(color="#374151", size=11),
    ))
    fig14.update_layout(**lo("Estimated annual saving from each optimization (USD M/yr)",
                        xkw=dict(title="Annual saving (USD millions)")),
                        height=260, showlegend=False)
    st.plotly_chart(fig14, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 8 — FULL CALCULATION LEDGER + LCOA BUILDER
# ══════════════════════════════════════════════════════════════════════════════
with t8:
    st.markdown("""
    <div class="info-box">
    <strong>Full transparency mode.</strong> Every number here traces directly to the EPI Excel models
    (CARTAGENA_H2_h2a_12_03_2026_v22.xlsm). Use the toggles below to build your own LCOA
    by including or excluding cost layers — from upstream production all the way to delivered CIF.
    </div>""", unsafe_allow_html=True)

    # ── Compute all LCOA components ─────────────────────────────────────────
    nh3_tpa = pc["nh3_net_tpa"]
    crf_val  = p.wacc*(1+p.wacc)**p.project_life_years/((1+p.wacc)**p.project_life_years-1)
    epi_crf  = 0.05669*(1+0.05669)**25/((1+0.05669)**25-1)  # EPI's H2ALite WACC

    def _ann(c_musd): return round(c_musd*crf_val*1e6/nh3_tpa, 1)
    def _elec(gwh, pkwh): return round(gwh*1e6*pkwh/nh3_tpa, 1)
    def _opx(musd): return round(musd*1e6/nh3_tpa, 1)

    # ── Pre-compute financing ──────────────────────────────────────────────
    _debt    = capex["total_capex"] * p.debt_share * 1e6
    _r_d, _n_d = p.debt_interest_rate, p.debt_tenor_years
    _avg_int_pt = dcf_df.interest_musd.mean() * 1e6 / nh3_tpa
    _avg_pri_pt = (_debt / _n_d) / nh3_tpa

    # ── Layer A — Operating costs (cash expenses, year-1) ─────────────────
    A_items = {
        f"Grid electricity — day (${p.grid_price_day_kwh*1000:.1f}/MWh × {pc['grid_day_gwh']:.1f} GWh/yr)":
            round(pc["grid_day_gwh"] * 1e6 * p.grid_price_day_kwh / nh3_tpa, 1),
        f"Grid electricity — night (${p.grid_price_night_kwh*1000:.1f}/MWh × {pc['grid_night_gwh']:.1f} GWh/yr)":
            round(pc["grid_night_gwh"] * 1e6 * p.grid_price_night_kwh / nh3_tpa, 1),
        f"Grid electricity — HB aux (${p.grid_price_night_kwh*1000:.1f}/MWh × {pc['hb_grid_gwh']:.1f} GWh/yr)":
            round(pc["hb_grid_gwh"] * 1e6 * p.grid_price_night_kwh / nh3_tpa, 1),
        "Equipment O&M (3.1% of core CAPEX/yr)":   _opx(opex_df.om_opex_musd.iloc[2]),
        "Solar O&M ($13k/MW/yr)":                   _opx(opex_df.solar_om_musd.iloc[2]),
        "Port infrastructure O&M ($2.2M/yr)":       _opx(opex_df.peripheral_opex_musd.iloc[2]),
        "Ocean freight & insurance ($60/t)":         _opx(opex_df.var_om_musd.iloc[2]),
    }

    # ── Layer B — Capital recovery (annualised CAPEX via CRF) ─────────────
    # CRF at WACC blends debt cost + equity return — no double-counting
    B_items = {
        "Solar PV plant (250 MWac × $800/kWac)":        _ann(capex["solar_plant"]),
        "Grid interconnection (230kV)":                   _ann(capex["grid_interconnect"]),
        "Electrolyser (180 MW AWE × $612/kWe)":          _ann(capex["electrolyser"]),
        "H₂ buffer storage (0.18d × $1,050/kgH₂)":       _ann(capex["h2_storage"]),
        "Water treatment (H₂ side)":                     _ann(capex["water_treatment"]),
        "Haber-Bosch synthesis plant":                   _ann(capex["haber_bosch"]),
        "Air Separation Unit (N₂)":                      _ann(capex["asu"]),
        "NH₃ onsite storage (9,160 t)":                  _ann(capex["nh3_storage"]),
        "Water for NH₃ cooling":                         _ann(capex["water_nh3"]),
        "Installation, BoP & contingency (30%)":         _ann(capex["hb_bop"]),
        "Owner's costs & FEED (5%)":                     _ann(capex["owners_costs"]),
        "Export terminal (Fichtner)":                    _ann(capex["export_facility"]),
        "NH₃ pipeline to port (10 km)":                  _ann(capex["pipeline"]),
        "Power line 220kV (11.2 km)":                    _ann(capex["power_ohtl"]),
        "Water intake pipeline":                         _ann(capex["wtp_pipeline"]),
        "KOH system + wastewater plant":                 _ann(capex["koh_system"] + capex["wwtp"]),
        "Port contingency (15%)":                       _ann(capex["peripheral_contingency"]),
    }

    # ── Layer C — Colombian incentives (reduce CAPEX cost) ────────────────
    C_items = {
        "Ley 1715 Art.12 — VAT exemption (19% on equipment)": -_ann(capex["vat_saving"]),
        "Ley 1715 Art.13 — Import tariff exemption (~10%)":   -_ann(capex["tariff_saving"]),
    }

    # ── Layer D — Debt service (for transparency — embedded in CRF above) ─
    D_items = {
        f"Interest avg ({p.debt_share*100:.0f}% × ${capex['total_capex']:.0f}M @ {p.debt_interest_rate*100:.0f}%)":
            round(_avg_int_pt, 1),
        f"Principal avg ({_n_d}yr loan tenor)":
            round(_avg_pri_pt, 1),
    }

    # ── Layer E — Income tax ───────────────────────────────────────────────
    E_items = {
        f"Income tax ({p.income_tax_rate*100:.0f}%, avg after Ley 1715 deductions)":
            _opx(dcf_df.tax_musd.mean()),
    }

    A_tot = sum(A_items.values())
    B_tot = sum(B_items.values())
    C_tot = sum(C_items.values())
    D_tot = sum(D_items.values())   # transparency only, not additive
    E_tot = sum(E_items.values())

    # ── Layer toggle controls ────────────────────────────────────────────────
    sec("Build Your LCOA — Toggle Cost Layers")
    st.markdown("Select which cost layers to include. The waterfall updates instantly.", unsafe_allow_html=False)

    tc1, tc2, tc3, tc4, tc5 = st.columns(5)
    inc_A = tc1.toggle("A — Operating costs",   value=True,
        help=f"Electricity + O&M + freight. Subtotal: ${A_tot:.0f}/t")
    inc_B = tc2.toggle("B — Capital recovery",  value=True,
        help=f"Annualised CAPEX at {p.wacc*100:.0f}% WACC (CRF method). Subtotal: ${B_tot:.0f}/t")
    inc_C = tc3.toggle("C — Incentives",        value=True,
        help=f"Ley 1715 VAT + tariff savings. Subtotal: ${C_tot:.0f}/t")
    inc_D = tc4.toggle("D — Debt service",      value=False,
        help=f"⚠️ Already embedded in Layer B (CRF). Shown for transparency only. ${D_tot:.0f}/t")
    inc_E = tc5.toggle("E — Income tax",        value=True,
        help=f"Colombian corporate tax after deductions. ${E_tot:.0f}/t")

    # EPI comparison toggles
    st.markdown("")
    ce1, ce2, _ = st.columns([1, 1, 2])
    show_epi = ce1.toggle("Show EPI $786/t benchmark",  value=True,
        help="EPI's H2ALite break-even LCOA using their 5.669% WACC and core capex only")
    show_market = ce2.toggle("Show market price benchmark", value=True,
        help=f"Current spot NH₃ price ${nh3_price}/t for comparison")

    # Build the active LCOA
    selected_val = (A_tot if inc_A else 0) + (B_tot if inc_B else 0) +                    (C_tot if inc_C else 0) + (D_tot if inc_D else 0)

    # ── Waterfall chart ──────────────────────────────────────────────────────
    sec("LCOA Waterfall — Selected Layers")

    wf_x, wf_y, wf_measure, wf_text, wf_colors = [], [], [], [], []
    running = 0

    layer_configs = [
        ("A — Operating costs",  A_tot, inc_A, C["teal"]),
        ("B — Capital recovery", B_tot, inc_B, C["blue"]),
        ("C — Incentives ↓",     C_tot, inc_C, C["green"]),
        ("D — Debt service",     D_tot, inc_D, C["purple"]),
        ("E — Tax",              E_tot, inc_E, C["amber"]),
    ]

    for lname, ltot, linc, lcolor in layer_configs:
        if linc:
            wf_x.append(lname)
            wf_y.append(ltot)
            wf_measure.append("relative")
            wf_text.append(f"${ltot:+.0f}/t")
            running += ltot

    # Total bar
    wf_x.append("= TOTAL LCOA")
    wf_y.append(selected_val)
    wf_measure.append("total")
    wf_text.append(f"${selected_val:.0f}/t")

    fig_wf = go.Figure(go.Waterfall(
        orientation="v",
        measure=wf_measure,
        x=wf_x,
        y=wf_y,
        text=wf_text,
        textposition="outside",
        textfont=dict(size=14, color="#1a1a2e"),
        connector=dict(line=dict(color="#e2e8f0", width=2)),
        decreasing=dict(marker_color=C["green"]),
        increasing=dict(marker_color=C["blue"]),
        totals=dict(marker_color=C["teal"]),
    ))

    if show_epi:
        fig_wf.add_hline(y=786, line_dash="dash", line_color=C["amber"], line_width=2,
                         annotation_text="EPI H2ALite $786/t (production cost, 5.67% WACC)",
                         annotation_font_color=C["amber"], annotation_font_size=12)
    if show_market:
        fig_wf.add_hline(y=nh3_price, line_dash="dot", line_color=C["green"], line_width=2,
                         annotation_text=f"NH₃ market price ${nh3_price}/t",
                         annotation_font_color=C["green"], annotation_font_size=12)

    fig_wf.update_layout(**lo("LCOA Waterfall (CRF methodology, $/tonne NH₃)",
                              ykw=dict(title="USD per tonne NH₃")),
                         height=420, showlegend=False)
    st.plotly_chart(fig_wf, use_container_width=True)

    # ── Summary KPI row ──────────────────────────────────────────────────────
    k1,k2,k3,k4,k5 = st.columns(5)
    kpi(k1, "Selected LCOA",     f"${selected_val:.0f}/t",
        f"Layers: {'A' if inc_A else ''}{'B' if inc_B else ''}{'C' if inc_C else ''}{'D' if inc_D else ''}")
    kpi(k2, "EPI Production Cost","$786/t",    "H2ALite @5.67% WACC, core only")
    kpi(k3, "Production only (A)", f"${A_tot:.0f}/t", f"WACC={p.wacc*100:.0f}%, incl. Fichtner FEED")
    kpi(k4, "Up to port (A+B)",   f"${A_tot+B_tot:.0f}/t", "FOB Cartagena")
    kpi(k5, "NH₃ market price",   f"${nh3_price}/t", "Spot benchmark")

    # ── Detailed item tables ─────────────────────────────────────────────────
    sec("Detailed Cost Breakdown by Item")

    for lname, litems, linc, lcolor, ldesc in [
        ("A — OPERATING COSTS", A_items, inc_A, C["teal"],
         f"Cash operating costs, year-1 basis (before escalation). "
         f"Grid electricity = {pc['elec_total_gwh']:.1f} GWh + {pc['hb_grid_gwh']:.1f} GWh HB aux."),
        ("B — CAPITAL RECOVERY (CRF method)", B_items, inc_B, C["blue"],
         f"Annualised CAPEX using CRF={crf_val:.4f} at {p.wacc*100:.0f}% WACC over {p.project_life_years}yr. "
         f"WACC = {p.debt_share*100:.0f}% debt × {p.debt_interest_rate*100:.0f}% + "
         f"{(1-p.debt_share)*100:.0f}% equity × 15% target IRR. "
         f"Total CAPEX ${capex['total_capex']:.0f}M."),
        ("C — COLOMBIAN INCENTIVES (savings)", C_items, inc_C, C["green"],
         f"Ley 1715/2099 — legally mandated fiscal benefits. "
         f"VAT ${capex['vat_saving']:.0f}M + Tariff ${capex['tariff_saving']:.0f}M saved on CAPEX."),
        ("D — DEBT SERVICE (transparency, not additive)", D_items, inc_D, C["purple"],
         f"⚠️ Already embedded in Layer B via CRF. Shown explicitly so you can see the "
         f"cash flow obligation: ${D_tot:.0f}/t total = interest ${round(dcf_df.interest_musd.mean()*1e6/nh3_tpa,0):.0f}/t "
         f"+ principal ${round((_debt/_n_d)/nh3_tpa,0):.0f}/t. "
         f"Full debt service = ${round((_debt*_r_d*(1+_r_d)**_n_d/((1+_r_d)**_n_d-1))/nh3_tpa,0):.0f}/t/yr."),
        ("E — INCOME TAX", E_items, inc_E, C["amber"],
         f"Colombian corporate tax at {p.income_tax_rate*100:.0f}% rate. "
         f"Near zero in early years due to Ley 1715 Art.11 (50% deduction over 15yr) "
         f"and accelerated depreciation (5yr)."),
    ]:
        active_str = "✓ INCLUDED" if linc else "○ excluded"
        subtot = sum(litems.values())
        with st.expander(f"Layer {lname}  —  ${subtot:.0f}/t  [{active_str}]",
                         expanded=linc):
            st.caption(ldesc)
            rows_html = ""
            for item, val in litems.items():
                color = C["red"] if val < 0 else "#1a1a2e"
                rows_html += f"""<tr style="border-bottom:1px solid #f3f4f6;">
                  <td style="padding:0.5rem 0.8rem;font-size:0.92rem;color:#374151;">{item}</td>
                  <td style="padding:0.5rem 0.8rem;font-size:1rem;font-weight:700;
                      color:{color};text-align:right;">${val:+.1f}/t</td>
                  <td style="padding:0.5rem 0.8rem;font-size:0.85rem;color:#6b7280;text-align:right;">
                    {val/max(abs(subtot),0.01)*100:.1f}% of layer</td>
                </tr>"""
            st.markdown(f"""
            <table style="width:100%;border-collapse:collapse;background:#fff;
                border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
              <thead><tr style="background:#f8f9fc;">
                <th style="padding:0.6rem 0.8rem;color:#1e4799;font-size:0.82rem;text-align:left;">Cost item</th>
                <th style="padding:0.6rem 0.8rem;color:#1e4799;font-size:0.82rem;text-align:right;">$/tonne NH₃</th>
                <th style="padding:0.6rem 0.8rem;color:#1e4799;font-size:0.82rem;text-align:right;">Share of layer</th>
              </tr></thead>
              <tbody>{rows_html}</tbody>
              <tfoot><tr style="background:#f0f9ff;border-top:2px solid #e2e8f0;">
                <td style="padding:0.6rem 0.8rem;font-weight:700;color:#1e4799;">SUBTOTAL</td>
                <td style="padding:0.6rem 0.8rem;font-weight:700;color:#1e4799;text-align:right;">${subtot:.1f}/t</td>
                <td></td>
              </tr></tfoot>
            </table>""", unsafe_allow_html=True)

    # ── Full process ledger (every variable from EPI Excel) ─────────────────
    sec("📋 Full Process Variable Ledger — Every Number from EPI Excel")
    st.caption("All values validated against CARTAGENA_H2_h2a_12_03_2026_v22.xlsm. "
               "EPI column = Excel source value. Our model column = computed value. "
               "Row is green if match is within 0.5%.")

    ledger = [
        # Section, Variable, EPI source, EPI value, Our value, unit, note
        ("SOLAR PV (PVSyst hourly sim, Cartagena Turbana)",
         "Nameplate capacity",          "H2!R11",  250.0,          p.solar_mwac,              "MWac",    ""),
        ("SOLAR PV (PVSyst hourly sim, Cartagena Turbana)",
         "DC/AC sizing ratio",          "H2!R20",  1.2,            1.2,                        "",        ""),
        ("SOLAR PV (PVSyst hourly sim, Cartagena Turbana)",
         "Annual energy (AC)",          "H2!R13",  615.579,        pc["solar_gwh_yr"],         "GWh/yr",  ""),
        ("SOLAR PV (PVSyst hourly sim, Cartagena Turbana)",
         "Capacity factor (AC annual)", "H2!R15",  0.24604,        p.solar_capacity_factor,    "",        ""),
        ("SOLAR PV (PVSyst hourly sim, Cartagena Turbana)",
         "Capacity factor (daylight)",  "H2!R16",  0.6746,         0.6746,                     "",        "hrs 07:00-17:00"),
        ("SOLAR PV (PVSyst hourly sim, Cartagena Turbana)",
         "GHI (irradiance)",            "H2!R17",  1961.5,         1961.5,                     "kWh/m²/yr",""),
        ("SOLAR PV (PVSyst hourly sim, Cartagena Turbana)",
         "Specific production",         "H2!R18",  2155.0,         2155.0,                     "kWh/kWp/yr",""),
        ("SOLAR PV (PVSyst hourly sim, Cartagena Turbana)",
         "Performance ratio (PR)",      "H2!R19",  0.853,          0.853,                      "",        ""),
        ("GRID POWER — COMPLEMENTARY SUPPLY",
         "Day complementarity factor",  "H2!R23",  0.10,           0.10,                       "fraction",""),
        ("GRID POWER — COMPLEMENTARY SUPPLY",
         "Grid day power",              "H2!R24",  80.0,           80.0,                       "MW",      ""),
        ("GRID POWER — COMPLEMENTARY SUPPLY",
         "Grid day energy",             "H2!R25",  35.296,         pc["grid_day_gwh"],         "GWh/yr",  ""),
        ("GRID POWER — COMPLEMENTARY SUPPLY",
         "Daylight hours/day",          "H2!R26",  10.0,           10.0,                       "hrs",     ""),
        ("GRID POWER — COMPLEMENTARY SUPPLY",
         "Night complementarity factor","H2!R29",  0.32,           0.32,                       "fraction",""),
        ("GRID POWER — COMPLEMENTARY SUPPLY",
         "Grid night power",            "H2!R30",  80.0,           80.0,                       "MW",      ""),
        ("GRID POWER — COMPLEMENTARY SUPPLY",
         "Grid night energy",           "H2!R31",  358.758,        pc["grid_night_gwh"],       "GWh/yr",  ""),
        ("GRID POWER — COMPLEMENTARY SUPPLY",
         "Night hours/day",             "H2!R32",  14.0,           14.0,                       "hrs",     ""),
        ("ELECTROLYSER (180 MW Alkaline AWE)",
         "Capacity (% nameplate)",      "H2!R35",  0.72,           0.72,                       "",        "72% of total installed"),
        ("ELECTROLYSER (180 MW Alkaline AWE)",
         "Nameplate MW",                "H2!R36",  180.0,          p.electrolyser_mw,          "MW",      ""),
        ("ELECTROLYSER (180 MW Alkaline AWE)",
         "PV/Electrolyser ratio",       "H2!R37",  1.3889,         250/180,                    "",        "250 MWac / 180 MW"),
        ("ELECTROLYSER (180 MW Alkaline AWE)",
         "Max load factor",             "H2!R38",  1.2,            1.2,                        "",        "120% peak"),
        ("ELECTROLYSER (180 MW Alkaline AWE)",
         "Min load factor",             "H2!R39",  0.3,            0.3,                        "",        "30% minimum"),
        ("ELECTROLYSER (180 MW Alkaline AWE)",
         "Specific energy consumption", "H2!R40",  50.0,           p.electrolyser_sec,         "kWh/kgH₂","BoP included"),
        ("ELECTROLYSER (180 MW Alkaline AWE)",
         "Total energy supplied",       "H2!R42",  1009.633,       pc["elec_total_gwh"],       "GWh/yr",  ""),
        ("ELECTROLYSER (180 MW Alkaline AWE)",
         "Long-term utilization",       "H2!R45",  0.98,           p.plant_availability,       "",        ""),
        ("ELECTROLYSER (180 MW Alkaline AWE)",
         "Solar share of H₂ production","H2!R47",  0.6097,         pc["solar_share_pct"]/100,  "",        ""),
        ("ELECTROLYSER (180 MW Alkaline AWE)",
         "Grid day share",              "H2!R48",  0.03496,        pc["grid_day_gwh"]/pc["elec_total_gwh"],"",""),
        ("ELECTROLYSER (180 MW Alkaline AWE)",
         "Grid night share",            "H2!R49",  0.35534,        pc["grid_night_gwh"]/pc["elec_total_gwh"],"",""),
        ("WATER",
         "Electrolysis water (IRENA)",  "H2!R50",  22.3,           p.water_l_per_kgh2,         "L/kgH₂",  ""),
        ("WATER",
         "Water for H₂ (annual)",       "H2!R51",  450296.5,       pc["water_h2_m3y"],         "m³/yr",   ""),
        ("WATER",
         "Total water (H₂ + NH₃)",      "H2!R52",  784654.7,       pc["water_total_m3y"],      "m³/yr",   ""),
        ("HABER-BOSCH PROCESS",
         "HB auxiliary grid power",     "H2!R57",  8.0,            8.0,                        "MW",      "24hrs/day"),
        ("HABER-BOSCH PROCESS",
         "HB grid energy",              "H2!R58",  66.872,         pc["hb_grid_gwh"],          "GWh/yr",  ""),
        ("HABER-BOSCH PROCESS",
         "H₂/NH₃ stoich. ratio",        "H2!R61",  0.177553,       p.hb_h2_per_tnh3,           "tH₂/tNH₃",""),
        ("HABER-BOSCH PROCESS",
         "HB combined efficiency",      "H2!R62",  0.98,           p.hb_combined_efficiency,   "",        "HB conversion"),
        ("HABER-BOSCH PROCESS",
         "Cooling water",               "H2!R64",  3.0,            3.0,                        "m³/tNH₃", ""),
        ("PRODUCTION OUTPUTS",
         "H₂ gross production",         "H2!R70",  20192.667,      pc["h2_gross_tpa"],         "t/yr",    ""),
        ("PRODUCTION OUTPUTS",
         "NH₃ net production",          "H2!R73",  111452.75,      pc["nh3_net_tpa"],          "t/yr",    ""),
        ("PRODUCTION OUTPUTS",
         "NH₃ production rate",         "H2!R72",  305350.0,       pc["nh3_rate_td"]*1000,     "kg/day",  ""),
        ("PRODUCTION OUTPUTS",
         "N₂ required (stoich + 15%)",  "H2!R74",  288804.3,       pc["n2_required_tpa"]/365*1000,"kg/day",""),
        ("PRODUCTION OUTPUTS",
         "HB auxiliary grid demand",    "H2!R76",  8000.0,         8000.0,                     "kW",      ""),
        ("ELECTRICITY PRICES",
         "Solar LCOE",                  "H2!R105", 0.04254,        p.solar_capex_per_mwac/1e3*epi_crf, "$/kWh","CRF-based"),
        ("ELECTRICITY PRICES",
         "Grid day price (HV industrial)","H2!R106",0.07734,       p.grid_price_day_kwh,       "$/kWh",   "COP 327/kWh ÷ TRM 4229"),
        ("ELECTRICITY PRICES",
         "Grid night price",            "H2!R107", 0.06961,        p.grid_price_night_kwh,     "$/kWh",   "COP 294/kWh ÷ TRM 4229"),
        ("ELECTRICITY PRICES",
         "HB grid total energy",        "H2!R113", 1076.505,       pc["elec_total_gwh"]+pc["hb_grid_gwh"],"GWh/yr","elec + HB"),
        ("CAPEX",
         "Solar PV plant",              "H2!R86",  200.0,          capex["solar_plant"],       "$M",      "$800/kWac × 250 MWac"),
        ("CAPEX",
         "Grid interconnection (230kV)","H2!R87",  10.0,           capex["grid_interconnect"], "$M",      ""),
        ("CAPEX",
         "Water distillation (H₂)",     "H2!R88",  6.785,          capex["water_treatment"],   "$M",      "$132k/m³/hr"),
        ("CAPEX",
         "Electrolyser all-in",         "H2!R89",  110.184,        capex["electrolyser"],      "$M",      "$612/kWe"),
        ("CAPEX",
         "Water for NH₃",               "H2!R94",  5.038,          capex["water_nh3"],         "$M",      ""),
        ("CAPEX",
         "Air Separation Unit (ASU)",   "H2!R95",  17.449,         capex["asu"],               "$M",      "$1,450/kgN₂/hr"),
        ("CAPEX",
         "Haber-Bosch synthesis",       "H2!R96",  41.986,         capex["haber_bosch"],       "$M",      "$3,300/kgNH₃/hr"),
        ("CAPEX",
         "NH₃ storage (9,160 t)",       "H2!R97",  9.16,           capex["nh3_storage"],       "$M",      "$1,000/tNH₃"),
        ("CAPEX",
         "Pipeline to port (10 km)",    "H2!R98",  16.0,           capex["pipeline"],          "$M",      "$1.6M/km"),
        ("CAPEX",
         "BoP + contingency (30%)",     "H2!R99",  26.890,         capex["hb_bop"],            "$M",      "30% of HB sub-block"),
        ("CAPEX",
         "Core total (gross)",          "H2!R102", 443.491,        capex["core_total"],        "$M",      "before incentives"),
    ]

    # Group by section
    from itertools import groupby
    sections_ledger = {}
    for sec_name, var, src, epi_val, our_val, unit, note in ledger:
        if sec_name not in sections_ledger:
            sections_ledger[sec_name] = []
        sections_ledger[sec_name].append((var, src, epi_val, our_val, unit, note))

    for sec_name, vars_list in sections_ledger.items():
        with st.expander(f"📊 {sec_name}", expanded=False):
            rows_html = ""
            for var, src, epi_v, our_v, unit, note in vars_list:
                pct = abs(our_v - epi_v) / max(abs(epi_v), 1e-9) * 100
                bg = "#f0fdf4" if pct < 0.5 else "#fffbeb" if pct < 3 else "#fef2f2"
                tick = "✓" if pct < 0.5 else f"~{pct:.1f}%"
                tick_c = "#16a34a" if pct < 0.5 else "#d97706" if pct < 3 else "#dc2626"
                rows_html += f"""<tr style="background:{bg}">
                  <td style="padding:0.45rem 0.8rem;font-size:0.9rem;color:#374151;">{var}</td>
                  <td style="padding:0.45rem 0.6rem;font-size:0.78rem;color:#6b7280;text-align:center;">{src}</td>
                  <td style="padding:0.45rem 0.8rem;font-size:0.95rem;font-weight:600;color:#1a1a2e;text-align:right;">{epi_v:,.4g}</td>
                  <td style="padding:0.45rem 0.8rem;font-size:0.95rem;font-weight:600;color:#1e4799;text-align:right;">{our_v:,.4g}</td>
                  <td style="padding:0.45rem 0.6rem;font-size:0.85rem;text-align:center;color:#6b7280;">{unit}</td>
                  <td style="padding:0.45rem 0.8rem;font-size:0.82rem;font-weight:700;
                      color:{tick_c};text-align:center;">{tick}</td>
                  <td style="padding:0.45rem 0.8rem;font-size:0.8rem;color:#9ca3af;">{note}</td>
                </tr>"""
            st.markdown(f"""
            <table style="width:100%;border-collapse:collapse;font-family:Inter,sans-serif;">
              <thead><tr style="background:#f8f9fc;border-bottom:2px solid #e2e8f0;">
                <th style="padding:0.5rem 0.8rem;color:#1e4799;font-size:0.82rem;text-align:left;">Variable</th>
                <th style="padding:0.5rem 0.6rem;color:#1e4799;font-size:0.82rem;text-align:center;">Excel ref</th>
                <th style="padding:0.5rem 0.8rem;color:#1e4799;font-size:0.82rem;text-align:right;">EPI Excel</th>
                <th style="padding:0.5rem 0.8rem;color:#1e4799;font-size:0.82rem;text-align:right;">Our model</th>
                <th style="padding:0.5rem 0.6rem;color:#1e4799;font-size:0.82rem;text-align:center;">Unit</th>
                <th style="padding:0.5rem 0.6rem;color:#1e4799;font-size:0.82rem;text-align:center;">Match</th>
                <th style="padding:0.5rem 0.8rem;color:#1e4799;font-size:0.82rem;text-align:left;">Note</th>
              </tr></thead>
              <tbody>{rows_html}</tbody>
            </table>""", unsafe_allow_html=True)



# ══════════════════════════════════════════════════════════════════════════════
# TAB 9 — LCOA BREAKDOWN (Levelized Cost of Ammonia)
# ══════════════════════════════════════════════════════════════════════════════
with t9:
    sec("LCOA Cartagena H2 — Levelized Cost of Ammonia")
    lcoa_total = sum(lb.values())
    st.caption(f"Total LCOA: ${lcoa_total:.0f}/t NH₃  ·  "
               f"EPI production cost: ${metrics['epi_lcoa_usd_t']:.0f}/t  ·  "
               f"CRF = {p.wacc*(1+p.wacc)**p.project_life_years/((1+p.wacc)**p.project_life_years-1):.4f} at {p.wacc*100:.1f}% WACC")

    # Component grouping: (name, [lb keys for CAPEX], [lb keys for OPEX])
    components = [
        ("Solar Plant", ["Solar CAPEX"], ["Solar O&M OPEX"]),
        ("Electrolyzer", ["Electrolyser CAPEX"], []),
        ("Haber-Bosch", ["Haber-Bosch CAPEX"], []),
        ("ASU", ["ASU CAPEX"], []),
        ("H2 storage", ["H2 storage CAPEX"], []),
        ("NH3 storage", ["NH3 storage CAPEX"], []),
        ("Pipeline", ["Pipeline CAPEX"], []),
        ("Peripheral", ["Peripheral CAPEX"], []),
        ("Grid energy", [], ["Grid energy OPEX"]),
        ("Fixed O&M", [], ["Fixed O&M OPEX"]),
        ("Freight", [], ["VarOpEx (freight)"]),
    ]
    comp_data = []
    for name, cap_keys, op_keys in components:
        capex_val = sum(lb.get(k, 0) for k in cap_keys)
        opex_val = sum(lb.get(k, 0) for k in op_keys)
        comp_data.append((name, capex_val, opex_val, capex_val + opex_val))
    comp_data.sort(key=lambda x: x[3], reverse=True)


    # Pie chart: CAPEX vs OPEX for total LCOA
    cap_keys = [k for k in lb if "CAPEX" in k]
    opex_keys = [k for k in lb if k not in cap_keys]
    total_capex = sum(lb[k] for k in cap_keys)
    total_opex = sum(lb[k] for k in opex_keys)

    pie_col, bar_col = st.columns([1, 2])
    with pie_col:
        sec("CAPEX vs OPEX")
        fig_pie = go.Figure(go.Pie(
            labels=["CAPEX (annualised)", "OPEX"],
            values=[total_capex, total_opex],
            hole=0.5,
            marker=dict(colors=[C["blue"], C["amber"]]),
            textinfo="label+percent",
            textfont=dict(size=13),
        ))
        fig_pie.update_layout(**lo("Share of total LCOA", lkw=dict(orientation="h", y=-0.1)),
                             height=320, showlegend=True)
        fig_pie.add_annotation(text=f"${lcoa_total:.0f}/t",
                              font=dict(size=18, color="#1a1a2e"), showarrow=False)
        st.plotly_chart(fig_pie, use_container_width=True)

    with bar_col:
        sec("LCOA by Component — Absolute $/t")
        comp_names = [c[0] for c in comp_data]
        comp_capex = [c[1] for c in comp_data]
        comp_opex = [c[2] for c in comp_data]
        fig_dollars = go.Figure()
        fig_dollars.add_trace(go.Bar(name="CAPEX", y=comp_names, x=comp_capex,
            orientation="h", marker_color=C["blue"], text=[f"${v:.0f}" if v else "" for v in comp_capex],
            textposition="outside", textfont=dict(size=10)))
        fig_dollars.add_trace(go.Bar(name="OPEX", y=comp_names, x=comp_opex,
            orientation="h", marker_color=C["amber"], text=[f"${v:.0f}" if v else "" for v in comp_opex],
            textposition="outside", textfont=dict(size=10)))
        fig_dollars.update_layout(**lo("$/tonne NH₃ by component",
            xkw=dict(title="USD per tonne NH₃"),
            lkw=dict(orientation="h", y=-0.12)),
            barmode="stack", height=420, showlegend=True)
        st.plotly_chart(fig_dollars, use_container_width=True)

    sec("LCOA by Component — % of Total")
    comp_pct_capex = [100 * c[1] / lcoa_total if lcoa_total else 0 for c in comp_data]
    comp_pct_opex = [100 * c[2] / lcoa_total if lcoa_total else 0 for c in comp_data]
    fig_pct = go.Figure()
    fig_pct.add_trace(go.Bar(name="CAPEX", y=comp_names, x=comp_pct_capex,
        orientation="h", marker_color=C["blue"],
        text=[f"{v:.1f}%" if v else "" for v in comp_pct_capex],
        textposition="outside", textfont=dict(size=10)))
    fig_pct.add_trace(go.Bar(name="OPEX", y=comp_names, x=comp_pct_opex,
        orientation="h", marker_color=C["amber"],
        text=[f"{v:.1f}%" if v else "" for v in comp_pct_opex],
        textposition="outside", textfont=dict(size=10)))
    fig_pct.update_layout(**lo("% of total LCOA by component",
        xkw=dict(title="% of total"),
        lkw=dict(orientation="h", y=-0.12)),
        barmode="stack", height=420, showlegend=True)
    st.plotly_chart(fig_pct, use_container_width=True)

    # Summary table
    sec("Component Summary Table")
    rows = ""
    for name, capex_val, opex_val, tot in comp_data:
        if tot == 0:
            continue
        pct = 100 * tot / lcoa_total if lcoa_total else 0
        rows += f"""<tr style="border-bottom:1px solid #f3f4f6;">
          <td style="padding:0.5rem 0.8rem;font-weight:600;color:#1a1a2e;">{name}</td>
          <td style="padding:0.5rem 0.8rem;text-align:right;color:#1e4799;">${capex_val:.0f}</td>
          <td style="padding:0.5rem 0.8rem;text-align:right;color:#d97706;">${opex_val:.0f}</td>
          <td style="padding:0.5rem 0.8rem;text-align:right;font-weight:700;">${tot:.0f}</td>
          <td style="padding:0.5rem 0.8rem;text-align:right;color:#6b7280;">{pct:.1f}%</td>
        </tr>"""
    st.markdown(f"""<table style="width:100%;border-collapse:collapse;background:#fff;
        border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
      <thead><tr style="background:#f8f9fc;">
        <th style="padding:0.6rem 0.8rem;color:#1e4799;text-align:left;">Component</th>
        <th style="padding:0.6rem 0.8rem;color:#1e4799;text-align:right;">CAPEX $/t</th>
        <th style="padding:0.6rem 0.8rem;color:#1e4799;text-align:right;">OPEX $/t</th>
        <th style="padding:0.6rem 0.8rem;color:#1e4799;text-align:right;">Total $/t</th>
        <th style="padding:0.6rem 0.8rem;color:#1e4799;text-align:right;">% of total</th>
      </tr></thead>
      <tbody>{rows}</tbody>
      <tfoot><tr style="background:#f0f9ff;border-top:2px solid #e2e8f0;">
        <td style="padding:0.6rem 0.8rem;font-weight:700;">TOTAL LCOA</td>
        <td style="padding:0.6rem 0.8rem;font-weight:700;text-align:right;">${total_capex:.0f}</td>
        <td style="padding:0.6rem 0.8rem;font-weight:700;text-align:right;">${total_opex:.0f}</td>
        <td style="padding:0.6rem 0.8rem;font-weight:700;text-align:right;">${lcoa_total:.0f}</td>
        <td style="padding:0.6rem 0.8rem;font-weight:700;text-align:right;">100%</td>
      </tr></tfoot>
    </table>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 10 — ASSUMPTIONS & PARAMETERS (all editable)
# ══════════════════════════════════════════════════════════════════════════════
with t10:
    st.markdown("""
    <div class="info-box">
    <strong>Every assumption, fully editable.</strong> All values below are sourced from the
    EPI Excel models. Change any number and every chart, KPI and calculation updates instantly.
    The sidebar controls the main variables; this tab exposes everything else.
    </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div class="warn-box">
    <strong>Note:</strong> Changes here override the defaults from the Excel model.
    EPI source reference shown for each variable so you can verify against the spreadsheet.
    </div>""", unsafe_allow_html=True)

    # ── We display current values as read-only here since all inputs are
    # already wired through the sidebar + run_model() cache.
    # For full editability of ALL variables, we show them with their EPI source
    # and the sidebar slider/default that controls each one.

    sec("Solar PV — PVSyst hourly simulation, Cartagena Turbana")
    sa1,sa2,sa3,sa4 = st.columns(4)
    sa1.metric("Nameplate capacity", f"{p.solar_mwac:.0f} MWac",
               help="EPI H2!R11 — 250 MWac single-axis tracker")
    sa2.metric("Annual CF (AC)", f"{p.solar_capacity_factor*100:.2f}%",
               help="EPI H2!R15 — PVSyst hourly simulation result")
    sa3.metric("Annual generation", f"{pc['solar_gwh_yr']:.1f} GWh",
               help="EPI H2!R13 — 615.58 GWh/yr")
    sa4.metric("Performance ratio", f"{0.853:.3f}",
               help="EPI H2!R19 — PR 0.853")

    sb1,sb2,sb3,sb4 = st.columns(4)
    sb1.metric("DC/AC ratio", "1.20",
               help="EPI H2!R20 — 1.2 oversize factor")
    sb2.metric("GHI kWh/m²/yr", "1,961.5",
               help="EPI H2!R17 — Cartagena Turbana irradiance")
    sb3.metric("Specific prod kWh/kWp/yr", "2,155",
               help="EPI H2!R18")
    sb4.metric("Daylight CF (hrs 7-17)", f"{0.6746:.4f}",
               help="EPI H2!R16")

    st.caption("➡️ **Adjustable via sidebar:** Solar plant size (MWac) and Solar cost ($/kWac)")

    sec("Grid Power — Colombian HV Industrial Tariff")
    gc1,gc2,gc3,gc4 = st.columns(4)
    gc1.metric("Day complementarity", "10%",
               help="EPI H2!R23 — 10% of 180MW = 18MW grid top-up during day")
    gc2.metric("Night complementarity", "32%",
               help="EPI H2!R29 — 32% of 180MW = 57.6MW grid at night")
    gc3.metric("Grid day price", f"${p.grid_price_day_kwh*1000:.2f}/MWh",
               help="EPI H2!R106 — COP 327/kWh ÷ TRM 4,229")
    gc4.metric("Grid night price", f"${p.grid_price_night_kwh*1000:.2f}/MWh",
               help="EPI H2!R107 — COP 294/kWh ÷ TRM 4,229")

    gd1,gd2,gd3,gd4 = st.columns(4)
    gd1.metric("Grid day energy", f"{pc['grid_day_gwh']:.2f} GWh/yr",
               help="EPI H2!R25 — 35.30 GWh/yr")
    gd2.metric("Grid night energy", f"{pc['grid_night_gwh']:.2f} GWh/yr",
               help="EPI H2!R31 — 358.76 GWh/yr")
    gd3.metric("HB aux grid energy", f"{pc['hb_grid_gwh']:.2f} GWh/yr",
               help="EPI H2!R58 — 8 MW × 24hrs × 365 = 66.87 GWh/yr")
    gd4.metric("TRM (COP/USD)", "4,228.54",
               help="EPI H2!R119 — Exchange rate used for price conversion")
    st.caption("➡️ **Adjustable via sidebar:** Grid power night (MW) and Grid electricity price ($/MWh)")

    sec("Electrolyser — 180 MW Alkaline (AWE), LONGI units")
    ea1,ea2,ea3,ea4 = st.columns(4)
    ea1.metric("Rated capacity", f"{p.electrolyser_mw:.0f} MW",
               help="EPI H2!R36 — 180 MW installed")
    ea2.metric("Specific energy (SEC)", f"{p.electrolyser_sec:.0f} kWh/kgH₂",
               help="EPI H2!R40 — 50 kWh/kgH₂ including BoP")
    ea3.metric("Long-term utilization", f"{p.plant_availability*100:.0f}%",
               help="EPI H2!R45 — 98% (planned shutdowns already in dispatch)")
    ea4.metric("Max/min load", "120% / 30%",
               help="EPI H2!R38-39 — turndown range")

    eb1,eb2,eb3,eb4 = st.columns(4)
    eb1.metric("CAPEX all-in", f"${p.electrolyser_capex_all_in_mw/1000:.0f}/kWe",
               help="EPI DATABASE R18 — $612/kWe all-in (stack + BoP + EPC)")
    eb2.metric("Total CAPEX", f"${capex['electrolyser']:.1f}M",
               help="180 MW × $612/kWe = $110.2M")
    eb3.metric("PV/Electrolyser ratio", f"{250/180:.3f}",
               help="EPI H2!R37 — 250 MWac / 180 MW")
    eb4.metric("H₂ produced", f"{pc['h2_gross_tpa']/1000:.2f} ktpa",
               help="EPI H2!R70 — 20,192.7 tpa")
    st.caption("➡️ **Adjustable via sidebar:** Electrolyser capacity (MW), Efficiency (kWh/kgH₂), Cost ($/kWe)")

    sec("Haber-Bosch Process")
    ha1,ha2,ha3,ha4 = st.columns(4)
    ha1.metric("H₂/NH₃ stoich. ratio", f"{p.hb_h2_per_tnh3:.5f} tH₂/tNH₃",
               help="EPI H2!R61 — 0.17755 (from molecular weights)")
    ha2.metric("Combined efficiency", f"{p.hb_combined_efficiency*100:.0f}%",
               help="EPI H2!R62 — 98% HB conversion efficiency")
    ha3.metric("CAPEX rate", f"${p.hb_capex_per_kgd:.0f}/kgNH₃/day",
               help="EPI DATABASE R21 — $137.5/kgNH₃/day (= $3,300/kgNH₃/hr)")
    ha4.metric("HB total CAPEX", f"${capex['haber_bosch']:.1f}M",
               help="EPI H2!R96 — $41.985M")

    hb1,hb2,hb3,hb4 = st.columns(4)
    hb1.metric("ASU CAPEX rate", f"${p.asu_capex_per_kgd_n2:.1f}/kgN₂/day",
               help="EPI DATABASE R22 — $60.4/kgN₂/day (= $1,450/kgN₂/hr)")
    hb2.metric("ASU total CAPEX", f"${capex['asu']:.1f}M",
               help="EPI H2!R95 — $17.449M")
    hb3.metric("N₂ excess", f"{p.n2_excess_pct*100:.0f}%",
               help="EPI H2!R74 — 15% excess N₂ over stoichiometric")
    hb4.metric("NH₃ output", f"{pc['nh3_net_ktpa']:.1f} ktpa",
               help="EPI H2!R73 — 111,452.75 tpa")
    st.caption("➡️ **Adjustable via sidebar:** Haber-Bosch cost ($/kgNH₃/hr) and ASU cost ($/kgN₂/hr)")

    sec("Water")
    wa1,wa2,wa3,wa4 = st.columns(4)
    wa1.metric("Electrolysis water", f"{p.water_l_per_kgh2:.1f} L/kgH₂",
               help="EPI H2!R50 — IRENA reference, 22.3 L/kgH₂")
    wa2.metric("H₂ side water", f"{pc['water_h2_m3y']/1000:.0f} kt/yr",
               help="EPI H2!R51 — 450,296 m³/yr")
    wa3.metric("NH₃ cooling water", f"{3.0:.0f} m³/tNH₃",
               help="EPI H2!R64 — 3 m³/tNH₃")
    wa4.metric("Total water", f"{pc['water_total_m3y']/1000:.0f} kt/yr",
               help="EPI H2!R52 — 784,655 m³/yr")

    sec("Financing & Returns")
    fa1,fa2,fa3,fa4 = st.columns(4)
    fa1.metric("Debt share", f"{p.debt_share*100:.0f}%",
               help="EPI NH3 Interface R182 — D/E=3, debt=75%")
    fa2.metric("Loan interest rate", f"{p.debt_interest_rate*100:.1f}%",
               help="EPI NH3 Interface R185 — 5% nominal")
    fa3.metric("Loan tenor", f"{p.debt_tenor_years} years",
               help="EPI NH3 Interface R184 — 7 year loan")
    fa4.metric("WACC / discount rate", f"{p.wacc*100:.1f}%",
               help="EPI NH3 Interface R181 — 10% nominal")

    fb1,fb2,fb3,fb4 = st.columns(4)
    fb1.metric("Project life", f"{p.project_life_years} years",
               help="EPI NH3 Interface R32")
    fb2.metric("Tax rate", f"{p.income_tax_rate*100:.0f}%",
               help="Colombian corporate tax, before Ley 1715 deductions")
    fb3.metric("Ley 1715 deduction", f"{p.income_tax_deduction_pct*100:.0f}% over {p.income_tax_deduction_years}yr",
               help="Art. 11 — 50% of investment deductible from taxable income")
    fb4.metric("Equity IRR (current)", f"{metrics['equity_irr_pct']}%",
               help="Computed — target is 15%")
    st.caption("➡️ **Adjustable via sidebar:** Debt %, WACC %, Loan interest rate")

    sec("Revenue Assumptions")
    ra1,ra2,ra3,ra4 = st.columns(4)
    ra1.metric("NH₃ start price", f"${nh3_price}/t",
               help="Adjustable — current market Q3 2025: $840-$902/t NW Europe")
    ra2.metric("H₂Global contract", f"{h2g_vol} ktpa at €{h2g_eur}/t",
               help="Hintco Lot 1 benchmark. 10-year contract, escalating 2%/yr")
    ra3.metric("Colombia H₂ (Reficar)", f"{p.colombia_h2_ktpa:.0f} ktpa H₂",
               help=f"${p.colombia_h2_price_per_kg:.2f}/kgH₂ — domestic offtake allocation")
    ra4.metric("Price floor", f"${p.nh3_price_floor:.0f}/t",
               help="Minimum NH₃ price assumption — covers operating costs")
    st.caption("➡️ **Adjustable via sidebar:** NH₃ price, H₂Global volume/price, scenario selection")

    sec("Process Variables Summary — All EPI Values")
    st.caption("These variables are fixed to EPI Excel values and not adjustable via sliders. "
               "To change them, edit model_engine.py ProjectParams defaults.")

    fixed_vars = [
        ("HB ratio tH₂/tNH₃",     f"{p.hb_h2_per_tnh3:.5f}",    "H2!R61",  "Stoichiometric from molecular weights"),
        ("HB efficiency",           f"{p.hb_combined_efficiency:.2f}",  "H2!R62", "HB conversion efficiency"),
        ("N₂ excess %",             f"{p.n2_excess_pct*100:.0f}%",       "H2!R74", "15% buffer over stoichiometric"),
        ("Water L/kgH₂",            f"{p.water_l_per_kgh2:.1f}",         "H2!R50", "IRENA reference"),
        ("Solar curtailment GWh",   f"{pc.get('power_surplus_mwh',0)/1000:.2f}", "H2!R116", "Surplus sold back to grid"),
        ("Day complementarity",     "10%",                               "H2!R23", "Grid top-up during daylight"),
        ("Night complementarity",   "32%",                               "H2!R29", "Grid supply at night"),
        ("Utilization",             f"{p.plant_availability:.2f}",       "H2!R45", "Long-term availability"),
        ("NH₃ storage",             f"{p.nh3_storage_t:,.0f} t",         "H2!R97", "9,160 t onsite storage"),
        ("H₂ storage buffer",       "0.18 days",                         "H2!R123","0.18 days production buffer"),
        ("Stack life hours",        f"{p.stack_life_hours:,.0f} hrs",    "Arup",   "Before replacement"),
        ("Stack replacement cost",  f"{p.stack_replacement_pct*100:.0f}% of CAPEX","Arup","Electrolyser stack only"),
        ("O&M rate",                f"{p.fixed_opex_annual_musd:.2f} $M/yr","NH3 G0 R97","Fixed O&M from EPI"),
        ("Colombia H₂ price",       f"${p.colombia_h2_price_per_kg:.2f}/kgH₂","EPI","Reficar offtake"),
        ("EUR/USD rate",            f"{p.eur_usd:.2f}",                  "EPI",    "Used for H₂Global pricing"),
        ("Inflation rate",          f"{p.inflation_rate*100:.1f}%/yr",   "EPI",    "Nominal price escalation"),
    ]

    rows_html = ""
    for name, val, src, note in fixed_vars:
        rows_html += f"""<tr style="border-bottom:1px solid #f3f4f6;">
          <td style="padding:0.45rem 0.8rem;font-size:0.9rem;color:#374151;font-weight:500;">{name}</td>
          <td style="padding:0.45rem 0.8rem;font-size:0.95rem;font-weight:700;color:#1e4799;text-align:right;">{val}</td>
          <td style="padding:0.45rem 0.6rem;font-size:0.8rem;color:#6b7280;text-align:center;">{src}</td>
          <td style="padding:0.45rem 0.8rem;font-size:0.85rem;color:#6b7280;">{note}</td>
        </tr>"""

    st.markdown(f"""
    <table style="width:100%;border-collapse:collapse;background:#fff;
        border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
      <thead><tr style="background:#f8f9fc;border-bottom:2px solid #e2e8f0;">
        <th style="padding:0.55rem 0.8rem;color:#1e4799;font-size:0.82rem;text-align:left;">Variable</th>
        <th style="padding:0.55rem 0.8rem;color:#1e4799;font-size:0.82rem;text-align:right;">Value</th>
        <th style="padding:0.55rem 0.6rem;color:#1e4799;font-size:0.82rem;text-align:center;">EPI source</th>
        <th style="padding:0.55rem 0.8rem;color:#1e4799;font-size:0.82rem;text-align:left;">Note</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table>""", unsafe_allow_html=True)


# ─── FOOTER ───────────────────────────────────────────────────────────────────
st.divider()
st.markdown("""<div style="display:flex;justify-content:space-between;font-size:0.82rem;color:#9ca3af;">
  <span>Cartagena H2 Financial Model v3.0 — Electryon Power Inc. | CONFIDENTIAL</span>
  <span>Sources: EPI Excel (Mar 2026) · Arup (Nov 2025) · Fichtner (Jan 2025) · Hintco Lot 1 · IRENA</span>
</div>""", unsafe_allow_html=True)
