"""
Cartagena H2 — Investment Model | v3.3
Electryon Power Inc.
=============================================

Investment-banking style dashboard for the Cartagena H2 green ammonia export
project. Toggle between two scenarios anchored to verified sources:

  • Feasibility (Arup + Fichtner)         — what the IDB-commissioned study says
  • EPI Optimized (2026 procurement)      — Electryon's view of executable pricing

Three-tier LCOA:
  • Ex-works       — core process plant (Arup-comparable)
  • FOB Cartagena  — + Fichtner peripheral (H2Global FOB-comparable)
  • CIF Europe     — + ocean freight (H2Global delivered Rotterdam comparable)

Revenue: single-stream — NH3 export volume × USD price FOB Cartagena.
Default scenario: EPI Optimized (2026 procurement). Default view: Executive.
Project NPV at WACC (10% default). Equity NPV at cost of equity Ke (12.5% default).
Default leverage 63/37 (ATOME Villeta cleared structure, April 2026 FID).
Default energy: long-term hydro PPA ($55/MWh).
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from model_engine import (
    ProjectParams,
    SCENARIOS,
    SCENARIO_LABELS,
    SCENARIO_DESCRIPTIONS,
    compute_process_chain,
    compute_capex,
    compute_lcoa_h2a,
    compute_production_profile,
    compute_revenue,
    compute_opex,
    compute_dcf,
    compute_lcoa_breakdown,
)

# =============================================================================
# PAGE CONFIG & THEME
# =============================================================================

st.set_page_config(
    page_title="Electryon · Cartagena H2 Investment Model",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "Cartagena H2 financial model v3.3 — Electryon Power Inc."
    },
)

# Design tokens
NAVY      = "#1F3864"
NAVY_DARK = "#152848"
ACCENT    = "#2E7D5B"
ACCENT_LT = "#E1F5EE"
AMBER     = "#B45309"
AMBER_LT  = "#FEF3E2"
GREY_900  = "#1A1F2E"
GREY_700  = "#4A5468"
GREY_500  = "#8B95A8"
GREY_300  = "#D4DAE3"
GREY_100  = "#F4F6FA"
WHITE     = "#FFFFFF"

# Plotly theme — base layout (legend handled per-chart)
PLOTLY_LAYOUT = dict(
    font=dict(family="Georgia, 'Times New Roman', serif", size=12, color=GREY_900),
    plot_bgcolor=WHITE,
    paper_bgcolor=WHITE,
    margin=dict(l=40, r=20, t=40, b=40),
    xaxis=dict(
        showgrid=False, showline=True, linewidth=1, linecolor=GREY_300,
        ticks="outside", tickwidth=1, tickcolor=GREY_300, tickfont=dict(size=11, color=GREY_700),
    ),
    yaxis=dict(
        showgrid=True, gridwidth=1, gridcolor=GREY_100,
        showline=False, ticks="outside", tickwidth=1, tickcolor=GREY_300,
        tickfont=dict(size=11, color=GREY_700),
    ),
    hoverlabel=dict(bgcolor=NAVY, font=dict(family="Georgia, serif", color=WHITE, size=12)),
)

# =============================================================================
# CUSTOM CSS — institutional financial dashboard aesthetic
# =============================================================================

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"], .stApp {{
    font-family: 'Inter', -apple-system, sans-serif;
    color: {GREY_900};
}}

/* Hide default Streamlit chrome we don't need */
#MainMenu, footer, header[data-testid="stHeader"] {{
    visibility: hidden;
}}

/* Page background */
.stApp {{
    background: {WHITE};
}}

/* Headings use serif for institutional gravitas */
h1, h2, h3, h4 {{
    font-family: 'EB Garamond', Georgia, serif;
    font-weight: 600;
    letter-spacing: -0.01em;
    color: {NAVY};
}}

h1 {{
    font-size: 2.4rem;
    margin-bottom: 0.2rem;
}}
h2 {{
    font-size: 1.6rem;
    margin-top: 1.8rem;
    margin-bottom: 0.6rem;
    border-bottom: 1px solid {GREY_300};
    padding-bottom: 0.4rem;
}}
h3 {{
    font-size: 1.2rem;
    color: {ACCENT};
    margin-top: 1.2rem;
}}

/* Hero header */
.hero {{
    background: linear-gradient(135deg, {NAVY_DARK} 0%, {NAVY} 100%);
    color: {WHITE};
    padding: 1.8rem 2rem 1.4rem 2rem;
    margin: -1rem -1rem 2rem -1rem;
    border-bottom: 4px solid {ACCENT};
}}
.hero h1 {{
    color: {WHITE};
    font-family: 'EB Garamond', Georgia, serif;
    font-weight: 600;
    font-size: 2.4rem;
    margin: 0;
    letter-spacing: -0.015em;
}}
.hero-subtitle {{
    color: rgba(255,255,255,0.8);
    font-family: 'Inter', sans-serif;
    font-size: 0.9rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-top: 0.4rem;
}}
.hero-meta {{
    color: rgba(255,255,255,0.7);
    font-family: 'EB Garamond', serif;
    font-size: 1.0rem;
    font-style: italic;
    margin-top: 0.8rem;
}}

/* Scenario pills */
.scenario-strip {{
    display: flex;
    gap: 0.5rem;
    padding: 0.6rem 0;
    margin-bottom: 1.2rem;
    border-bottom: 1px solid {GREY_300};
}}
.scenario-pill {{
    font-family: 'Inter', sans-serif;
    font-size: 0.78rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    padding: 0.4rem 0.9rem;
    border: 1px solid {GREY_300};
    border-radius: 0;
    background: {WHITE};
    color: {GREY_700};
}}
.scenario-pill.active {{
    background: {NAVY};
    color: {WHITE};
    border-color: {NAVY};
}}

/* KPI cards — investment-bank style */
.kpi-grid {{
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 1rem;
    margin: 1rem 0 2rem 0;
}}
@media (max-width: 1200px) {{
    .kpi-grid {{ grid-template-columns: repeat(3, 1fr); }}
}}
.kpi-card {{
    background: {WHITE};
    border: 1px solid {GREY_300};
    border-top: 3px solid {NAVY};
    padding: 1.0rem 1.1rem 0.9rem 1.1rem;
    transition: border-top-color 0.2s ease;
}}
.kpi-card.positive {{
    border-top-color: {ACCENT};
}}
.kpi-card.attention {{
    border-top-color: {AMBER};
}}
.kpi-label {{
    font-family: 'Inter', sans-serif;
    font-size: 0.7rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: {GREY_500};
    margin-bottom: 0.4rem;
    font-weight: 500;
}}
.kpi-value {{
    font-family: 'EB Garamond', Georgia, serif;
    font-size: 2.0rem;
    line-height: 1.0;
    font-weight: 600;
    color: {NAVY};
    margin-bottom: 0.3rem;
    letter-spacing: -0.02em;
}}
.kpi-value.positive {{ color: {ACCENT}; }}
.kpi-value.attention {{ color: {AMBER}; }}
.kpi-sub {{
    font-family: 'Inter', sans-serif;
    font-size: 0.72rem;
    color: {GREY_700};
    line-height: 1.4;
}}
.kpi-sub-secondary {{
    font-family: 'Inter', sans-serif;
    font-size: 0.68rem;
    color: {GREY_500};
    margin-top: 0.15rem;
    font-style: italic;
}}

/* Two-tier LCOA card */
.lcoa-card {{
    background: {WHITE};
    border: 1px solid {GREY_300};
    border-top: 3px solid {NAVY};
    padding: 1.0rem 1.1rem 0.9rem 1.1rem;
}}
.lcoa-row {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 0.25rem 0;
}}
.lcoa-label {{
    font-family: 'Inter', sans-serif;
    font-size: 0.7rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: {GREY_500};
}}
.lcoa-value {{
    font-family: 'EB Garamond', serif;
    font-size: 1.3rem;
    font-weight: 600;
    color: {NAVY};
}}
.lcoa-value.complete {{
    font-size: 1.7rem;
    color: {NAVY};
    border-top: 1px dotted {GREY_300};
    padding-top: 0.4rem;
}}

/* Section labels */
.section-eyebrow {{
    font-family: 'Inter', sans-serif;
    font-size: 0.72rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: {GREY_500};
    margin: 1.8rem 0 0.3rem 0;
    font-weight: 600;
}}

/* Scenario context box */
.scenario-context {{
    background: {GREY_100};
    border-left: 3px solid {NAVY};
    padding: 0.9rem 1.1rem;
    margin: 0.5rem 0 1.5rem 0;
    font-family: 'EB Garamond', serif;
    font-size: 1.0rem;
    color: {GREY_900};
    line-height: 1.5;
    font-style: italic;
}}
.scenario-context strong {{
    font-style: normal;
    color: {NAVY};
}}

/* Sidebar styling */
section[data-testid="stSidebar"] {{
    background: {GREY_100};
    border-right: 1px solid {GREY_300};
}}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {{
    color: {NAVY};
}}

/* Streamlit buttons */
.stButton > button {{
    font-family: 'Inter', sans-serif;
    font-size: 0.78rem;
    font-weight: 500;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    border-radius: 0;
    border: 1px solid {GREY_300};
    background: {WHITE};
    color: {GREY_700};
    padding: 0.5rem 1.2rem;
    transition: all 0.15s ease;
}}
.stButton > button:hover {{
    border-color: {NAVY};
    color: {NAVY};
    background: {WHITE};
}}
.stButton > button:focus:not(:active) {{
    border-color: {NAVY};
    box-shadow: none;
}}

/* Radio buttons (scenario toggle) */
div[role="radiogroup"] {{
    gap: 0.4rem;
}}
div[role="radiogroup"] label {{
    background: {WHITE};
    border: 1px solid {GREY_300};
    padding: 0.5rem 1rem;
    cursor: pointer;
    transition: all 0.15s ease;
    margin: 0;
}}
div[role="radiogroup"] label:hover {{
    border-color: {NAVY};
}}

/* Tables */
.stDataFrame {{
    border: 1px solid {GREY_300};
}}
.stDataFrame thead th {{
    background: {NAVY} !important;
    color: {WHITE} !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    font-weight: 500 !important;
}}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{
    gap: 0;
    border-bottom: 1px solid {GREY_300};
}}
.stTabs [data-baseweb="tab"] {{
    height: 44px;
    background: transparent;
    border-radius: 0;
    padding: 0 1.4rem;
    font-family: 'Inter', sans-serif;
    font-size: 0.82rem;
    letter-spacing: 0.03em;
    color: {GREY_700};
    border-bottom: 2px solid transparent;
    transition: all 0.15s ease;
}}
.stTabs [aria-selected="true"] {{
    color: {NAVY};
    border-bottom-color: {NAVY};
    font-weight: 600;
    background: transparent;
}}

/* Source citations */
.source-line {{
    font-family: 'EB Garamond', serif;
    font-style: italic;
    font-size: 0.78rem;
    color: {GREY_500};
    margin-top: 0.4rem;
}}

/* Note callouts */
.note-callout {{
    background: {ACCENT_LT};
    border-left: 3px solid {ACCENT};
    padding: 0.7rem 1rem;
    margin: 0.6rem 0 1rem 0;
    font-family: 'EB Garamond', serif;
    font-size: 0.95rem;
    color: {GREY_900};
    line-height: 1.5;
}}
.note-attention {{
    background: {AMBER_LT};
    border-left: 3px solid {AMBER};
    padding: 0.7rem 1rem;
    margin: 0.6rem 0 1rem 0;
    font-family: 'EB Garamond', serif;
    font-size: 0.95rem;
    color: {GREY_900};
    line-height: 1.5;
}}

</style>
""", unsafe_allow_html=True)


# =============================================================================
# SIDEBAR — scenario selection + view toggle
# =============================================================================

ENERGY_TARIFFS = [
    {"key": "industrial", "label": "Industrial tariff", "price_mwh": 78, "price_kwh": 0.078},
    {"key": "hydro_ppa", "label": "Long-term hydro PPA", "price_mwh": 55, "price_kwh": 0.055},
]

with st.sidebar:
    st.markdown(f"""
    <div style="padding: 0.4rem 0 1rem 0; border-bottom: 2px solid {NAVY}; margin-bottom: 1rem;">
      <div style="font-family: 'EB Garamond', serif; font-size: 1.6rem; color: {NAVY}; font-weight: 600; letter-spacing: -0.01em;">
        Electryon
      </div>
      <div style="font-family: 'Inter', sans-serif; font-size: 0.72rem; letter-spacing: 0.15em; color: {GREY_700}; text-transform: uppercase; margin-top: 0.2rem;">
        Cartagena H₂ · Investment Model
      </div>
      <div style="font-family: 'EB Garamond', serif; font-size: 0.85rem; color: {GREY_500}; margin-top: 0.4rem; font-style: italic;">
        v3.3 · May 2026
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-eyebrow">Scenario</div>', unsafe_allow_html=True)

    scenario_key = st.radio(
        "Scenario",
        options=list(SCENARIO_LABELS.keys()),
        format_func=lambda k: SCENARIO_LABELS[k],
        index=1,  # default to EPI Optimized (2026 procurement)
        label_visibility="collapsed",
    )

    st.markdown(f"""
    <div style="font-family: 'EB Garamond', serif; font-style: italic; font-size: 0.88rem; color: {GREY_700}; line-height: 1.5; padding: 0.4rem 0 1rem 0;">
        {SCENARIO_DESCRIPTIONS[scenario_key]}
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-eyebrow">View</div>', unsafe_allow_html=True)

    view_mode = st.radio(
        "View",
        options=["Executive", "Analyst"],
        index=0,
        horizontal=True,
        label_visibility="collapsed",
    )

    st.markdown('<div class="section-eyebrow">Macro overrides</div>', unsafe_allow_html=True)

    wacc_override = st.slider(
        "WACC (project discount rate)", 0.06, 0.14, 0.10, 0.005,
        format="%.3f",
        help="Project discount rate / weighted cost of capital. Used to discount unlevered Project FCF for Project NPV.",
    )

    ke_override = st.slider(
        "Cost of equity (Ke)", 0.08, 0.20, 0.125, 0.005,
        format="%.3f",
        help="Required return on equity. Used to discount levered Equity FCF for Equity NPV. "
             "Default 12.5% = US 10-yr Treasury (~4.5%) + Colombia country risk (~3-4%) + "
             "renewable project premium (~4-5%).",
    )

    debt_share_override = st.slider(
        "Leverage (debt %)", 0.50, 0.80, 0.63, 0.01,
        format="%.2f",
        help="ATOME Villeta (April 2026 FID): 63% debt / 37% equity. DFI underwriting "
             "typically caps at 65-70%. Slider default matches ATOME comp.",
    )

    debt_rate_override = st.slider(
        "Cost of debt (interest rate)", 0.030, 0.075, 0.050, 0.005,
        format="%.3f",
        help="ATOME Villeta (April 2026 FID) cleared at ~5.0% blended across DFI consortium: "
             "IDB Invest, IFC, EIB ($135M), FMO, GCF ($50M concessional). Senior DFI tranches "
             "price 5.5-6.0%; GCF concessional pulls blended down to ~5.0%. Without GCF, "
             "expect 5.5-6.0%. Slider default matches ATOME comp.",
    )

    tax_rate_override = st.slider(
        "Income tax rate", 0.0, 0.35, 0.35, 0.05,
        format="%.2f", help="Colombia: 0.30 (FNCER) or 0.35 (general corporate). Default 35%.",
    )

    nh3_price_override = st.slider(
        "NH₃ price (USD/t FOB Cartagena)", 600, 1100, 920, 20,
        help="Year-1 base case FOB Cartagena. Reference benchmarks: ACME-Yara Oman ~$650-700/t · "
             "H2Global Window 1 FOB Egypt $868/t · H2Global delivered Rotterdam $1,070/t. "
             "Price escalates 2% nominal/yr.",
    )

    st.markdown('<div class="section-eyebrow">Energy supply</div>', unsafe_allow_html=True)
    # Scenario-aware energy default:
    #   Feasibility   → Industrial tariff ($78/MWh) — Arup-published, audit chain intact
    #   EPI Optimized → Long-term hydro PPA ($55/MWh) — internal execution case
    energy_option_labels = [
        f"{t['label']} — ${t['price_mwh']}/MWh" for t in ENERGY_TARIFFS
    ]
    energy_default_idx = 0 if scenario_key == "feasibility" else 1
    energy_selection = st.radio(
        "Energy supply",
        options=energy_option_labels,
        index=energy_default_idx,
        label_visibility="collapsed",
        help="Industrial tariff ($78/MWh): Colombian HV grid pricing — matches Arup's "
             "published assumption in the IDB-commissioned feasibility study. "
             "Long-term hydro PPA ($55/MWh): take-or-pay agreement with EPM/ISAGEN/Celsia — "
             "Electryon's internal execution basis and a key post-FEED value-creation lever.",
    )
    selected_tariff = ENERGY_TARIFFS[energy_option_labels.index(energy_selection)]
    energy_price_kwh = selected_tariff["price_kwh"]
    st.caption(
        f"Active energy cost: ${selected_tariff['price_mwh']}/MWh "
        f"(${selected_tariff['price_kwh']:.3f}/kWh)"
    )

    # Sidebar context note
    st.markdown(f"""
    <div style="margin-top: 1.4rem; padding: 0.6rem 0.8rem; background: {WHITE}; border-left: 3px solid {ACCENT}; font-family: 'EB Garamond', serif; font-size: 0.8rem; color: {GREY_700}; line-height: 1.4; font-style: italic;">
        Revenue is single-stream: NH₃ export volume × USD FOB price.
        LCOA shown in three tiers (ex-works / FOB Cartagena / CIF Europe).
        Project NPV at WACC; Equity NPV at Ke.
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="margin-top: 2rem; padding-top: 1rem; border-top: 1px solid {GREY_300}; font-family: 'EB Garamond', serif; font-size: 0.78rem; color: {GREY_500}; font-style: italic; line-height: 1.5;">
        All figures in 2026 USD unless noted.<br>
        Source data: Arup Nov 2025, Fichtner Jan 2025, EPI 2026, public market data verified May 2026.
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# BUILD MODEL — run all calculations for chosen scenario
# =============================================================================

@st.cache_data(show_spinner=False)
def run_scenario(scenario_key: str,
                 wacc: float, cost_of_equity: float,
                 debt_share: float,
                 tax_rate: float, nh3_price: float,
                 energy_price_kwh: float,
                 debt_rate: float):
    """Build full model run. DCF basis is always FOB Cartagena.
    The three LCOA tiers (ex-works, FOB, CIF) are computed independently."""
    base_params = dict(SCENARIOS[scenario_key])
    base_params.update({
        "wacc":               wacc,
        "cost_of_equity":     cost_of_equity,
        "debt_share":         debt_share,
        "debt_interest_rate": debt_rate,
        "income_tax_rate":    tax_rate,
        "nh3_price_base":     nh3_price,
        "freight_basis":      "FOB",  # DCF always FOB; three LCOA tiers shown independently
        # Energy price override (applies to all three grid_price_* fields uniformly)
        "grid_price_day_kwh":   energy_price_kwh,
        "grid_price_night_kwh": energy_price_kwh,
        "grid_price_hb_kwh":    energy_price_kwh,
    })
    p = ProjectParams(**base_params)
    pc = compute_process_chain(p)
    capex = compute_capex(p)
    prod = compute_production_profile(p, p.project_life_years)
    rev = compute_revenue(p, prod)
    opex = compute_opex(p, prod, capex)
    df, metrics = compute_dcf(p, prod, rev, opex, capex)
    lcoa_h2a = compute_lcoa_h2a(p, capex)
    return {
        "params": p,
        "process_chain": pc,
        "capex": capex,
        "production": prod,
        "revenue": rev,
        "opex": opex,
        "cashflow": df,
        "metrics": metrics,
        "lcoa_h2a": lcoa_h2a,
    }

result = run_scenario(scenario_key, wacc_override, ke_override, debt_share_override,
                      tax_rate_override, nh3_price_override, energy_price_kwh,
                      debt_rate_override)
m = result["metrics"]
df = result["cashflow"]
pc = result["process_chain"]
capex = result["capex"]
p = result["params"]


# =============================================================================
# HERO HEADER
# =============================================================================

st.markdown(f"""
<div class="hero">
  <div class="hero-subtitle">Project Cartagena H₂ · Confidential Investment Model</div>
  <h1>Green Ammonia Export · 120 ktpa · COD 2030</h1>
  <div class="hero-meta">
    Currently viewing: <strong style="color: {WHITE};">{SCENARIO_LABELS[scenario_key]}</strong>
    &nbsp;·&nbsp; Cartagena, Colombia &nbsp;→&nbsp; Europe / Asia
  </div>
</div>
""", unsafe_allow_html=True)


# =============================================================================
# EXECUTIVE HEADLINE METRICS
# =============================================================================

# Determine return-attention level
proj_irr_level = "positive" if m["project_irr_pct"] and m["project_irr_pct"] >= 12 else "attention"
eq_irr_level   = "positive" if m["equity_irr_pct"] and m["equity_irr_pct"] >= 15 else "attention"
dscr_level     = "positive" if m["min_dscr"] and m["min_dscr"] >= 1.3 else "attention" if m["min_dscr"] and m["min_dscr"] >= 1.1 else ""

def fmt_money(v, decimals=0):
    if v is None: return "—"
    return f"${v:,.{decimals}f}M"

def kpi_card_html(label, value, sub="", sub2="", level=""):
    sub2_html = f'<div class="kpi-sub-secondary">{sub2}</div>' if sub2 else ''
    return f"""<div class="kpi-card {level}">
<div class="kpi-label">{label}</div>
<div class="kpi-value {level}">{value}</div>
<div class="kpi-sub">{sub}</div>
{sub2_html}
</div>"""

st.markdown('<div class="section-eyebrow">Headline Metrics</div>', unsafe_allow_html=True)

# Build full KPI grid as one HTML block (avoids Streamlit's markdown escaping issues
# when concatenating multiple st.markdown calls with raw HTML).
card1 = kpi_card_html(
    "Total Investment",
    fmt_money(m["total_capex_musd"]),
    f"Gross ${m['gross_capex_musd']:.0f}M",
    f"Ley 1715 incentives ${m['vat_saving_musd'] + m['tariff_saving_musd']:.0f}M",
)
card2 = kpi_card_html(
    "Equity NPV",
    fmt_money(m["equity_npv_musd"]),
    f"@ {m['cost_of_equity_pct']:.1f}% Ke · 25-yr life",
    f"Project NPV ${m['project_npv_musd']:.0f}M @ {m['wacc_pct']:.1f}% WACC",
    "positive" if m["equity_npv_musd"] > 0 else "attention",
)
card3 = kpi_card_html(
    "Equity IRR",
    f"{m['equity_irr_pct']:.1f}%" if m['equity_irr_pct'] else "—",
    f"Project IRR {m['project_irr_pct']:.1f}%" if m['project_irr_pct'] else "",
    f"{int(p.debt_share*100)}/{int((1-p.debt_share)*100)} debt-equity · {p.debt_tenor_years}-yr tenor",
    eq_irr_level,
)
card4 = kpi_card_html(
    "Average Revenue",
    fmt_money(m["avg_annual_revenue_musd"]) + "/yr",
    f"EBITDA margin {m['avg_ebitda_margin_pct']:.0f}%",
    f"NH₃ ${p.nh3_price_base:.0f}/t Y1 → 2% nominal escalation",
)
card5 = kpi_card_html(
    "Equity Payback",
    f"{m['payback_years']} yrs" if m['payback_years'] else "—",
    f"Min DSCR {m['min_dscr']:.2f}×" if m['min_dscr'] else "",
    f"Lifetime tax ${m['lifetime_tax_musd']:.0f}M",
    "positive" if m["payback_years"] and m["payback_years"] <= 8 else "",
)
card6 = f"""<div class="lcoa-card">
<div class="kpi-label">LCOA — USD/t NH₃</div>
<div class="lcoa-row">
<span class="lcoa-label">Ex-works</span>
<span class="lcoa-value">${m['lcoa_ex_works_usd_t']:.0f}/t</span>
</div>
<div class="lcoa-row" style="font-size: 0.65rem; color: {GREY_500};">
<span class="lcoa-label" style="font-size: 0.62rem;">+ Fichtner</span>
<span class="lcoa-value" style="font-size: 0.85rem; color: {GREY_700};">+${m['lcoa_fichtner_delta_usd_t']:.0f}/t</span>
</div>
<div class="lcoa-row complete">
<span class="lcoa-label" style="color: {NAVY}; font-weight: 600;">FOB Cartagena</span>
<span class="lcoa-value complete">${m['lcoa_fob_usd_t']:.0f}/t</span>
</div>
<div class="lcoa-row" style="font-size: 0.65rem; color: {GREY_500}; margin-top: 0.2rem;">
<span class="lcoa-label" style="font-size: 0.62rem;">+ Ocean freight</span>
<span class="lcoa-value" style="font-size: 0.85rem; color: {GREY_700};">+${m['lcoa_freight_delta_usd_t']:.0f}/t</span>
</div>
<div class="lcoa-row" style="border-top: 1px dotted {GREY_300}; padding-top: 0.3rem;">
<span class="lcoa-label" style="color: {GREY_700};">CIF Europe</span>
<span class="lcoa-value" style="font-size: 1.1rem; color: {GREY_700};">${m['lcoa_cif_usd_t']:.0f}/t</span>
</div>
</div>"""

st.markdown(
    f'<div class="kpi-grid">{card1}{card2}{card3}{card4}{card5}{card6}</div>',
    unsafe_allow_html=True,
)

# Three-tier LCOA reading note with explicit benchmarks for each tier
benchmark_text = f"""
<div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; margin-top: 0.6rem;">

<div style="border-left: 3px solid {GREY_500}; padding-left: 0.7rem;">
<div style="font-family: 'Inter', sans-serif; font-size: 0.7rem; letter-spacing: 0.08em; text-transform: uppercase; color: {GREY_500}; margin-bottom: 0.2rem;">Ex-works · ${m['lcoa_ex_works_usd_t']:.0f}/t</div>
<div style="font-family: 'EB Garamond', serif; font-size: 0.9rem; line-height: 1.4;">
Core process plant. Compares to <strong>Arup $812/t</strong> (Nov 2025), Chile feasibility studies ($780–1,180/t), Brazil ($760–1,250/t).
</div>
</div>

<div style="border-left: 3px solid {NAVY}; padding-left: 0.7rem;">
<div style="font-family: 'Inter', sans-serif; font-size: 0.7rem; letter-spacing: 0.08em; text-transform: uppercase; color: {NAVY}; margin-bottom: 0.2rem;">FOB Cartagena · ${m['lcoa_fob_usd_t']:.0f}/t</div>
<div style="font-family: 'EB Garamond', serif; font-size: 0.9rem; line-height: 1.4;">
At Puerto Bahía loading flange. Compares to <strong>H2Global Window 1 FOB Egypt $868/t</strong> (€811/t × 1.07). Cartagena sits <strong style="color: {ACCENT};">${868-m['lcoa_fob_usd_t']:.0f} below</strong>.
</div>
</div>

<div style="border-left: 3px solid {GREY_500}; padding-left: 0.7rem;">
<div style="font-family: 'Inter', sans-serif; font-size: 0.7rem; letter-spacing: 0.08em; text-transform: uppercase; color: {GREY_500}; margin-bottom: 0.2rem;">CIF Europe · ${m['lcoa_cif_usd_t']:.0f}/t</div>
<div style="font-family: 'EB Garamond', serif; font-size: 0.9rem; line-height: 1.4;">
Delivered Rotterdam. Compares to <strong>H2Global Window 1 delivered $1,070/t</strong> (€1,000/t × 1.07). Cartagena sits <strong style="color: {ACCENT};">${1070-m['lcoa_cif_usd_t']:.0f} below</strong>.
</div>
</div>

</div>
"""

st.markdown(f"""
<div class="note-callout" style="padding: 1rem 1.1rem;">
<strong style="color: {NAVY};">Three-tier LCOA framework.</strong>
Each tier reflects a specific delivery point and matches a different industry benchmark.
DCF cashflows assume FOB sale (offtaker pays ocean freight) — standard for green NH₃ trade.
{benchmark_text}
</div>
""", unsafe_allow_html=True)


# =============================================================================
# EXECUTIVE VIEW — clean, focused presentation
# =============================================================================

if view_mode == "Executive":

    # ─────────────────────────────────────────────────────────────────────
    # SCENARIO CONTEXT
    # ─────────────────────────────────────────────────────────────────────
    st.markdown("## Project Economics at a Glance")

    col1, col2 = st.columns([3, 2])

    with col1:
        # 25-year cashflow chart
        st.markdown('<div class="section-eyebrow">25-Year Cashflow Profile</div>', unsafe_allow_html=True)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df["op_year"], y=df["revenue_musd"],
            name="Revenue", marker_color=NAVY, opacity=0.85,
            hovertemplate="<b>Year %{x}</b><br>Revenue: $%{y:.1f}M<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            x=df["op_year"], y=-df["opex_musd"],
            name="OpEx", marker_color=GREY_500, opacity=0.7,
            hovertemplate="<b>Year %{x}</b><br>OpEx: $%{y:.1f}M<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=df["op_year"], y=df["ebitda_musd"],
            name="EBITDA", mode="lines+markers",
            line=dict(color=ACCENT, width=2.5),
            marker=dict(color=ACCENT, size=6),
            hovertemplate="<b>Year %{x}</b><br>EBITDA: $%{y:.1f}M<extra></extra>",
        ))

        fig.update_layout(
            **PLOTLY_LAYOUT,
            barmode="relative",
            height=380,
            title=dict(text="Revenue, OpEx and EBITDA (USD millions)", font=dict(size=13, color=GREY_700)),
            xaxis_title="Operating Year",
            yaxis_title="USD millions",
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Cumulative equity returns
        st.markdown('<div class="section-eyebrow">Equity Investor Returns</div>', unsafe_allow_html=True)

        cum_eq = df["equity_fcf_musd"].cumsum() - m["equity_musd"]
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=df["op_year"], y=cum_eq,
            name="Cumulative Equity Position",
            mode="lines",
            line=dict(color=NAVY, width=2.5),
            fill="tozeroy", fillcolor=f"rgba(31,56,100,0.08)",
            hovertemplate="<b>Year %{x}</b><br>Cumulative: $%{y:.1f}M<extra></extra>",
        ))
        # Zero line
        fig2.add_hline(y=0, line=dict(color=GREY_500, width=1, dash="dot"))
        # Equity invested
        fig2.add_hline(y=-m["equity_musd"], line=dict(color=AMBER, width=1, dash="dash"),
                       annotation_text=f"Equity invested: ${m['equity_musd']:.0f}M",
                       annotation_position="bottom right",
                       annotation_font_size=10)

        fig2.update_layout(
            **PLOTLY_LAYOUT,
            height=380,
            title=dict(text="Cumulative Equity Cash Position (USD M)", font=dict(size=13, color=GREY_700)),
            xaxis_title="Operating Year",
            yaxis_title="Cumulative USD M",
            showlegend=False,
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ─────────────────────────────────────────────────────────────────────
    # CAPEX BREAKDOWN & SCENARIO COMPARISON
    # ─────────────────────────────────────────────────────────────────────
    st.markdown("## Investment Composition")

    col1, col2 = st.columns([2, 3])

    with col1:
        st.markdown('<div class="section-eyebrow">CAPEX Build-Up</div>', unsafe_allow_html=True)

        capex_items = [
            ("Solar PV (250 MW)",  capex["solar_plant"]),
            ("Electrolyser",        capex["electrolyser"]),
            ("Haber-Bosch + ASU",   capex["haber_bosch"] + capex["asu"]),
            ("Storage + Pipeline",  capex["h2_storage"] + capex["nh3_storage"] + capex["pipeline"]),
            ("HB BoP + Other Core", capex["hb_bop"] + capex["water_treatment"] + capex["water_nh3"] + capex["grid_interconnect"]),
            ("Fichtner Peripheral", capex["peripheral_total"]),
            ("Owner's Costs (5%)",  capex["owners_costs"]),
        ]
        labels = [x[0] for x in capex_items]
        values = [x[1] for x in capex_items]
        colors = [NAVY, ACCENT, "#4A6FA5", "#6B8BC4", GREY_500, AMBER, "#9CA8BD"]

        fig3 = go.Figure(go.Bar(
            y=labels, x=values,
            orientation="h",
            marker_color=colors,
            text=[f"${v:.0f}M" for v in values],
            textposition="outside",
            textfont=dict(size=11, color=GREY_900),
            hovertemplate="<b>%{y}</b><br>$%{x:.1f}M<extra></extra>",
        ))
        fig3.update_layout(
            **{**PLOTLY_LAYOUT, "margin": dict(l=140, r=60, t=40, b=40)},
            height=320,
            title=dict(text=f"Gross CAPEX: ${m['gross_capex_musd']:.0f}M",
                       font=dict(size=13, color=GREY_700)),
            xaxis_title="USD millions",
            showlegend=False,
        )
        fig3.update_yaxes(autorange="reversed")
        st.plotly_chart(fig3, use_container_width=True)

        st.markdown(f"""
        <div style="text-align: center; font-family: 'EB Garamond', serif; font-size: 0.95rem; color: {GREY_700}; padding: 0.2rem 0 1rem 0;">
            Less Ley 1715 incentives: <strong style="color: {ACCENT};">−${m['vat_saving_musd']+m['tariff_saving_musd']:.0f}M</strong>
            &nbsp;·&nbsp; Net CAPEX: <strong style="color: {NAVY};">${m['total_capex_musd']:.0f}M</strong>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="section-eyebrow">Cross-Scenario Comparison</div>', unsafe_allow_html=True)

        # Run all three scenarios for comparison
        compare_data = []
        for sname in ['feasibility', 'epi_optimized']:
            r = run_scenario(sname, wacc_override, ke_override, debt_share_override,
                            tax_rate_override, nh3_price_override, energy_price_kwh,
                            debt_rate_override)
            cm = r["metrics"]
            compare_data.append({
                "Scenario": SCENARIO_LABELS[sname].split(" (")[0],
                "Net CAPEX ($M)": f"${cm['total_capex_musd']:.0f}M",
                "Ex-works": f"${cm['lcoa_ex_works_usd_t']:.0f}/t",
                "FOB Cartagena": f"${cm['lcoa_fob_usd_t']:.0f}/t",
                "CIF Europe": f"${cm['lcoa_cif_usd_t']:.0f}/t",
                "Project NPV @ WACC": f"${cm['project_npv_musd']:.0f}M",
                "Equity NPV @ Ke": f"${cm['equity_npv_musd']:.0f}M",
                "Project IRR": f"{cm['project_irr_pct']:.1f}%",
                "Equity IRR": f"{cm['equity_irr_pct']:.1f}%",
                "DSCR": f"{cm['min_dscr']:.2f}×" if cm['min_dscr'] else "—",
            })

        comp_df = pd.DataFrame(compare_data).set_index("Scenario")
        # Highlight selected scenario
        active_label = SCENARIO_LABELS[scenario_key].split(" (")[0]
        def highlight_active(row):
            if row.name == active_label:
                return [f"background-color: {ACCENT_LT}; font-weight: 600;"] * len(row)
            return [""] * len(row)
        styled = comp_df.style.apply(highlight_active, axis=1)
        st.dataframe(styled, use_container_width=True, height=170)

        st.markdown(f"""
        <div class="source-line">
            Cross-scenario comparison uses identical macro inputs (WACC, leverage, tax) — only the scenario-specific CAPEX/OPEX/efficiency inputs differ.
            Currently selected scenario is highlighted. See <em>Analyst → Scenarios</em> for line-by-line input differences.
        </div>
        """, unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────
    # REVENUE COMPOSITION
    # ─────────────────────────────────────────────────────────────────────
    rev_df = result["revenue"]

    st.markdown("## Revenue Composition")
    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown('<div class="section-eyebrow">Revenue & Price Evolution</div>', unsafe_allow_html=True)

        # v3.3: Single revenue stream (NH3 export × USD price)
        # Show revenue bars + price line on secondary axis
        fig4 = make_subplots(specs=[[{"secondary_y": True}]])
        fig4.add_trace(
            go.Bar(
                x=rev_df["op_year"], y=rev_df["nh3_revenue_musd"],
                name="NH₃ revenue (USD M)",
                marker_color=NAVY, opacity=0.82,
                hovertemplate="<b>Year %{x}</b><br>Revenue: $%{y:.1f}M<extra></extra>",
            ),
            secondary_y=False,
        )
        fig4.add_trace(
            go.Scatter(
                x=rev_df["op_year"], y=rev_df["nh3_price_usd_t"],
                name="NH₃ price (USD/t)",
                mode="lines+markers",
                line=dict(color=ACCENT, width=2.5),
                marker=dict(size=5),
                hovertemplate="<b>Year %{x}</b><br>Price: $%{y:.0f}/t<extra></extra>",
            ),
            secondary_y=True,
        )

        fig4.update_layout(
            **PLOTLY_LAYOUT,
            height=320,
            title=dict(text=f"Single-stream revenue: NH₃ export × FOB Cartagena price", font=dict(size=13, color=GREY_700)),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        fig4.update_xaxes(title_text="Operating Year")
        fig4.update_yaxes(title_text="Annual revenue (USD millions)", secondary_y=False)
        fig4.update_yaxes(title_text="NH₃ price (USD/t FOB)", secondary_y=True, showgrid=False)
        st.plotly_chart(fig4, use_container_width=True)

    with col2:
        st.markdown('<div class="section-eyebrow">Revenue Snapshot</div>', unsafe_allow_html=True)

        # Replace 3-channel pie with a clean snapshot panel
        y1 = rev_df[rev_df["op_year"] == 1].iloc[0]
        y10 = rev_df[rev_df["op_year"] == 10].iloc[0]
        y25 = rev_df[rev_df["op_year"] == 25].iloc[0]
        avg = rev_df["nh3_revenue_musd"].mean()
        total_25 = rev_df["nh3_revenue_musd"].sum()

        st.markdown(f"""
        <div style="background: {WHITE}; border: 1px solid {GREY_300}; padding: 1.1rem 1.2rem;">

        <div style="font-family: 'Inter', sans-serif; font-size: 0.7rem; letter-spacing: 0.1em; text-transform: uppercase; color: {GREY_500}; margin-bottom: 0.4rem;">Year 1 (operations start)</div>
        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.8rem;">
            <span style="font-family: 'EB Garamond', serif; font-size: 1.6rem; color: {NAVY}; font-weight: 600;">${y1.nh3_revenue_musd:.0f}M</span>
            <span style="font-family: 'EB Garamond', serif; font-size: 1.0rem; color: {GREY_700}; font-style: italic;">at ${y1.nh3_price_usd_t:.0f}/t</span>
        </div>

        <div style="font-family: 'Inter', sans-serif; font-size: 0.7rem; letter-spacing: 0.1em; text-transform: uppercase; color: {GREY_500}; margin-bottom: 0.4rem;">Year 10</div>
        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.8rem;">
            <span style="font-family: 'EB Garamond', serif; font-size: 1.6rem; color: {NAVY}; font-weight: 600;">${y10.nh3_revenue_musd:.0f}M</span>
            <span style="font-family: 'EB Garamond', serif; font-size: 1.0rem; color: {GREY_700}; font-style: italic;">at ${y10.nh3_price_usd_t:.0f}/t</span>
        </div>

        <div style="font-family: 'Inter', sans-serif; font-size: 0.7rem; letter-spacing: 0.1em; text-transform: uppercase; color: {GREY_500}; margin-bottom: 0.4rem;">Year 25 (final)</div>
        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.8rem;">
            <span style="font-family: 'EB Garamond', serif; font-size: 1.6rem; color: {NAVY}; font-weight: 600;">${y25.nh3_revenue_musd:.0f}M</span>
            <span style="font-family: 'EB Garamond', serif; font-size: 1.0rem; color: {GREY_700}; font-style: italic;">at ${y25.nh3_price_usd_t:.0f}/t</span>
        </div>

        <div style="border-top: 1px solid {GREY_300}; padding-top: 0.8rem; margin-top: 0.6rem;">
            <div style="display: flex; justify-content: space-between; font-family: 'Inter', sans-serif; font-size: 0.8rem; color: {GREY_700};">
                <span>Annual avg:</span><span style="color: {NAVY}; font-weight: 600;">${avg:.0f}M</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-family: 'Inter', sans-serif; font-size: 0.8rem; color: {GREY_700}; margin-top: 0.2rem;">
                <span>25-yr total:</span><span style="color: {NAVY}; font-weight: 600;">${total_25:,.0f}M</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-family: 'Inter', sans-serif; font-size: 0.8rem; color: {GREY_700}; margin-top: 0.2rem;">
                <span>Price escalation:</span><span style="color: {NAVY}; font-weight: 600;">2.0% nominal/yr</span>
            </div>
        </div>

        </div>
        """, unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────
    # SENSITIVITY
    # ─────────────────────────────────────────────────────────────────────
    st.markdown("## Returns Sensitivity")
    st.markdown(f"""
    <div class="source-line">
        Single-variable sensitivity around the {SCENARIO_LABELS[scenario_key]} base case. Each line shows project IRR as a single input is varied while others held constant.
    </div>
    """, unsafe_allow_html=True)

    # Run sensitivity on key variables
    @st.cache_data(show_spinner=False)
    def sensitivity_curves(scenario_key, wacc, cost_of_equity, debt_share, tax_rate, nh3_price, energy_price_kwh, debt_rate):
        results = {}
        for var, range_pcts in [
            ("nh3_price_base", [-0.30, -0.15, 0, 0.15, 0.30]),
            ("electrolyser_capex_all_in_mw", [-0.30, -0.15, 0, 0.15, 0.30]),
            ("grid_price_day_kwh", [-0.30, -0.15, 0, 0.15, 0.30]),
            ("solar_capex_per_mwac", [-0.30, -0.15, 0, 0.15, 0.30]),
        ]:
            irrs = []
            base_params = dict(SCENARIOS[scenario_key])
            base_val = base_params.get(var, getattr(ProjectParams(), var))
            for pct in range_pcts:
                params = dict(base_params)
                params[var] = base_val * (1 + pct)
                params.update({
                    "wacc": wacc, "cost_of_equity": cost_of_equity, "debt_share": debt_share,
                    "debt_interest_rate": debt_rate,
                    "income_tax_rate": tax_rate, "nh3_price_base": nh3_price,
                    "freight_basis": "FOB",
                    "grid_price_day_kwh": energy_price_kwh,
                    "grid_price_night_kwh": energy_price_kwh,
                    "grid_price_hb_kwh": energy_price_kwh,
                })
                # but the override might step on var if var is nh3_price_base
                if var == "nh3_price_base":
                    params["nh3_price_base"] = nh3_price * (1 + pct)
                p_test = ProjectParams(**params)
                cap_t = compute_capex(p_test)
                prod_t = compute_production_profile(p_test, p_test.project_life_years)
                rev_t = compute_revenue(p_test, prod_t)
                opex_t = compute_opex(p_test, prod_t, cap_t)
                _, m_t = compute_dcf(p_test, prod_t, rev_t, opex_t, cap_t)
                irrs.append(m_t["project_irr_pct"] if m_t["project_irr_pct"] else 0)
            results[var] = (range_pcts, irrs)
        return results

    sens = sensitivity_curves(scenario_key, wacc_override, ke_override, debt_share_override,
                              tax_rate_override, nh3_price_override, energy_price_kwh,
                              debt_rate_override)

    fig6 = go.Figure()
    var_labels = {
        "nh3_price_base":              ("NH₃ spot price",          NAVY),
        "electrolyser_capex_all_in_mw": ("Electrolyser CAPEX",      ACCENT),
        "grid_price_day_kwh":           ("Grid/PPA energy price",   AMBER),
        "solar_capex_per_mwac":          ("Solar CAPEX",             "#6B8BC4"),
    }
    for var, (pcts, irrs) in sens.items():
        label, color = var_labels[var]
        fig6.add_trace(go.Scatter(
            x=[p*100 for p in pcts], y=irrs,
            name=label,
            mode="lines+markers",
            line=dict(color=color, width=2.2),
            marker=dict(size=8),
            hovertemplate=f"<b>{label}</b><br>" + "%{x:+.0f}% input<br>IRR: %{y:.1f}%<extra></extra>",
        ))

    fig6.add_vline(x=0, line=dict(color=GREY_500, width=1, dash="dot"))
    fig6.update_layout(
        **PLOTLY_LAYOUT,
        height=380,
        title=dict(text="Project IRR sensitivity to ±30% in key inputs", font=dict(size=13, color=GREY_700)),
        xaxis_title="Input change vs base case (%)",
        yaxis_title="Project IRR (%)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig6.update_xaxes(ticksuffix="%")
    fig6.update_yaxes(ticksuffix="%")
    st.plotly_chart(fig6, use_container_width=True)


# =============================================================================
# ANALYST VIEW — detailed tables and parameter exposure
# =============================================================================

else:  # Analyst view

    tabs = st.tabs([
        "▌ Scenarios",
        "▌ Operating metrics",
        "▌ CAPEX detail",
        "▌ OPEX detail",
        "▌ Cashflow (25yr)",
        "▌ Revenue",
        "▌ LCOA build",
        "▌ Tax & Financing",
    ])

    # --- Tab: Scenarios ---
    with tabs[0]:
        st.markdown('<div class="section-eyebrow">Three-way Scenario Reconciliation</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="scenario-context">
            Each scenario applies a different parameter pack to the same underlying engine.
            <strong>Feasibility</strong> uses Arup Resumen Ejecutivo Nov 2025 Tabla 6.
            <strong>EPI Own</strong> uses your father's CARTAGENA_Alk_H2_h2a_3_12_2025_v21.xlsm.
            <strong>FEED Base</strong> uses the recommended consensus values from the reconciliation memo.
            All three include Fichtner Jan 2025 peripheral infrastructure for scope completeness.
        </div>
        """, unsafe_allow_html=True)

        # Side-by-side input table
        param_keys = [
            ("solar_capex_per_mwac",        "Solar CAPEX (USD/MWac)",  "{:,.0f}"),
            ("solar_opex_per_mwac",          "Solar OPEX (USD/MW/yr)",   "{:,.0f}"),
            ("electrolyser_capex_all_in_mw", "Electrolyser CAPEX (USD/MW all-in)", "{:,.0f}"),
            ("electrolyser_sec",              "Electrolyser SEC (kWh/kg H₂)",       "{:.1f}"),
            ("hb_capex_per_kgd",              "Haber-Bosch CAPEX (USD/kg-d)",       "{:.1f}"),
            ("asu_capex_per_kgd_n2",          "ASU CAPEX (USD/kg-d N₂)",            "{:.1f}"),
            ("pipeline_km",                    "NH₃ pipeline length (km)",            "{:.1f}"),
            ("hb_bop_pct",                    "HB BoP/contingency",                  "{:.0%}"),
            ("grid_price_day_kwh",             "Energy price (USD/kWh)",              "{:.4f}"),
        ]

        scen_inputs = []
        for sname in ['feasibility', 'epi_optimized']:
            base = dict(SCENARIOS[sname])
            row = {"Parameter": "—", "Source": SCENARIO_LABELS[sname]}
            scen_inputs.append((sname, base))

        # Build the comparison
        rows = []
        for pkey, plabel, pfmt in param_keys:
            row = {"Parameter": plabel}
            for sname, base in scen_inputs:
                v = base.get(pkey, getattr(ProjectParams(), pkey, "—"))
                row[SCENARIO_LABELS[sname].split(" (")[0]] = pfmt.format(v) if not isinstance(v, str) else v
            rows.append(row)

        input_df = pd.DataFrame(rows).set_index("Parameter")
        st.dataframe(input_df, use_container_width=True, height=380)

        st.markdown('<div class="section-eyebrow">Side-by-side Outputs (current macro overrides applied)</div>', unsafe_allow_html=True)
        compare_data = []
        for sname in ['feasibility', 'epi_optimized']:
            r = run_scenario(sname, wacc_override, ke_override, debt_share_override,
                            tax_rate_override, nh3_price_override, energy_price_kwh,
                            debt_rate_override)
            cm = r["metrics"]
            compare_data.append({
                "Scenario":              SCENARIO_LABELS[sname],
                "Gross CAPEX":           f"${cm['gross_capex_musd']:.0f}M",
                "Net CAPEX":             f"${cm['total_capex_musd']:.0f}M",
                "Ex-works":              f"${cm['lcoa_ex_works_usd_t']:.0f}/t",
                "FOB Cartagena":         f"${cm['lcoa_fob_usd_t']:.0f}/t",
                "CIF Europe":            f"${cm['lcoa_cif_usd_t']:.0f}/t",
                "Project NPV @ WACC":    f"${cm['project_npv_musd']:.0f}M",
                "Equity NPV @ Ke":       f"${cm['equity_npv_musd']:.0f}M",
                "Project IRR":           f"{cm['project_irr_pct']:.1f}%",
                "Equity IRR":            f"{cm['equity_irr_pct']:.1f}%",
                "Payback (yrs)":         str(cm['payback_years']),
                "Min DSCR":              f"{cm['min_dscr']:.2f}×" if cm['min_dscr'] else "—",
                "Lifetime tax":          f"${cm['lifetime_tax_musd']:.0f}M",
            })
        st.dataframe(pd.DataFrame(compare_data).set_index("Scenario"), use_container_width=True)

        st.markdown(f"""
        <div class="note-callout">
            <strong style="color: {NAVY};">Benchmark anchors (three-tier framework):</strong>
            Arup published $812/t (Nov 2025) — an ex-works / core-plant LCOA, since Arup compares directly to Chile ($780-1,180/t) and Brazil ($760-1,250/t) feasibility studies that exclude shipping.
            Feasibility scenario at 10% WACC produces <strong>ex-works ${result['metrics']['lcoa_ex_works_usd_t']:.0f}/t</strong>,
            <strong>FOB Cartagena ${result['metrics']['lcoa_fob_usd_t']:.0f}/t</strong>, and
            <strong>CIF Europe ${result['metrics']['lcoa_cif_usd_t']:.0f}/t</strong>.
            Each tier is directly comparable to a distinct industry benchmark.
        </div>
        """, unsafe_allow_html=True)

    # --- Tab: Operating metrics ---
    with tabs[1]:
        st.markdown('<div class="section-eyebrow">Plant Configuration &amp; Operating Metrics</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="scenario-context">
            Annual steady-state operating metrics at the active scenario configuration.
            Energy dispatch follows the EPI three-period model: all solar routed to electrolyser,
            grid top-ups during day and night, plus dedicated grid feed to the Haber-Bosch loop.
            HB conversion+availability combined at {p.hb_combined_efficiency*100:.0f}%; plant availability {p.plant_availability*100:.0f}%.
        </div>
        """, unsafe_allow_html=True)

        # ── Plant configuration ──────────────────────────────────────────────
        st.markdown('<div style="margin-top:1rem;"></div>', unsafe_allow_html=True)
        st.markdown("**Plant configuration**")
        _src_arup    = "Arup Tabla 6"
        _src_fichtner= "Fichtner Jan 2025"
        _src_epi     = "EPI PVSyst dispatch"
        _src_derived = "Derived"
        plant_cfg = pd.DataFrame([
            {"Component": "Solar PV (AC)",          "Value": f"{p.solar_mwac:,.1f} MWac",         "Notes": f"DC:AC ~1.20 → ~{p.solar_mwac*1.2:,.0f} MWp DC · CF {p.solar_capacity_factor*100:.1f}%",                            "Source": f"{_src_arup} (sizing) · {_src_epi} (CF)"},
            {"Component": "Solar PV (DC peak)",     "Value": f"{p.solar_mwac*1.2:,.0f} MWp",      "Notes": "Single-axis tracking, Cartagena/Turbana (Meteonorm 8.1)",                                                          "Source": _src_epi},
            {"Component": "Hydro PPA (night feed)", "Value": f"{getattr(p,'hydro_ppa_mw',80):.0f} MW","Notes": f"Complementarity {p.grid_night_complementarity*100:.0f}% night · {p.grid_day_complementarity*100:.0f}% day", "Source": _src_epi},
            {"Component": "Electrolyser (AWE)",     "Value": f"{p.electrolyser_mw:,.0f} MW",      "Notes": f"SEC {p.electrolyser_sec:.1f} kWh/kgH₂ · avail. {p.electrolyser_availability*100:.0f}% · stack life {p.stack_life_hours/1000:.0f}k h", "Source": _src_arup if scenario_key=="feasibility" else "EPI Optimized (2026 procurement)"},
            {"Component": "Haber-Bosch loop",       "Value": f"{pc['nh3_rate_td']:,.0f} tNH₃/day","Notes": f"Combined efficiency {p.hb_combined_efficiency*100:.0f}% · stoichiometric H₂:NH₃ {p.hb_h2_per_tnh3:.5f}",       "Source": _src_arup if scenario_key=="feasibility" else "Casale 2026 indicative"},
            {"Component": "ASU (N₂ supply)",        "Value": f"{pc['n2_rate_th']:.2f} tN₂/h",     "Notes": f"Stoichiometric N₂:NH₃ {p.n2_per_tnh3:.3f} · {p.n2_excess_pct*100:.0f}% excess design",                            "Source": _src_arup},
            {"Component": "NH₃ refrigerated storage","Value": f"{p.nh3_storage_t:,.0f} t",        "Notes": f"~{p.nh3_storage_t/(pc['nh3_rate_td'] or 1):.0f} days of production",                                              "Source": _src_epi},
            {"Component": "NH₃ pipeline to port",   "Value": f"{p.pipeline_km:.1f} km",           "Notes": "Mamonal export terminal (Fichtner peripheral scope)",                                                              "Source": _src_fichtner},
        ])
        st.dataframe(plant_cfg, use_container_width=True, hide_index=True)

        # ── Energy balance ───────────────────────────────────────────────────
        st.markdown('<div style="margin-top:1.4rem;"></div>', unsafe_allow_html=True)
        st.markdown("**Annual energy balance (GWh/yr)**")
        total_elec_input = pc["solar_gwh_yr"] + pc["grid_day_gwh"] + pc["grid_night_gwh"]
        total_with_hb    = total_elec_input + pc["hb_grid_gwh"]
        energy_rows = [
            {"Stream": "Solar generation (gross)",                "GWh/yr": pc["solar_gwh_yr"],     "% of total": pc["solar_gwh_yr"]/total_with_hb*100, "Source": "EPI PVSyst (R13)"},
            {"Stream": "  → to electrolyser",                     "GWh/yr": pc["solar_gwh_yr"] - pc["solar_curtailed_gwh"], "% of total": (pc["solar_gwh_yr"] - pc["solar_curtailed_gwh"])/total_with_hb*100, "Source": "Derived"},
            {"Stream": "  → curtailed surplus (sold to grid)",    "GWh/yr": pc["solar_curtailed_gwh"], "% of total": pc["solar_curtailed_gwh"]/total_with_hb*100, "Source": "EPI dispatch (R83)"},
            {"Stream": "Grid day top-up (to electrolyser)",        "GWh/yr": pc["grid_day_gwh"],     "% of total": pc["grid_day_gwh"]/total_with_hb*100,  "Source": "EPI dispatch (R25)"},
            {"Stream": "Grid night feed (to electrolyser)",       "GWh/yr": pc["grid_night_gwh"],   "% of total": pc["grid_night_gwh"]/total_with_hb*100,"Source": "EPI dispatch (R31)"},
            {"Stream": "Grid feed to HB loop",                    "GWh/yr": pc["hb_grid_gwh"],      "% of total": pc["hb_grid_gwh"]/total_with_hb*100,   "Source": "EPI dispatch (R58)"},
            {"Stream": "TOTAL ENERGY DRAW",                       "GWh/yr": total_with_hb,          "% of total": 100.0,                                "Source": ""},
            {"Stream": "—",                                        "GWh/yr": None,                   "% of total": None,                                 "Source": ""},
            {"Stream": "Electrolyser load factor",                 "GWh/yr": f"{pc['elec_load_pct']:.1f}%", "% of total": "",                            "Source": "Derived"},
            {"Stream": "Solar share of electrolyser input",        "GWh/yr": f"{pc['solar_share_pct']:.1f}%", "% of total": "",                          "Source": "Derived"},
            {"Stream": "Grid share of electrolyser input",         "GWh/yr": f"{pc['grid_share_pct']:.1f}%",  "% of total": "",                         "Source": "Derived"},
        ]
        energy_df = pd.DataFrame(energy_rows)
        # Format numeric columns
        def _fmt_gwh(v):
            if v is None: return ""
            if isinstance(v, str): return v
            return f"{v:,.1f}"
        def _fmt_pct(v):
            if v is None or v == "": return ""
            return f"{v:,.1f}%"
        energy_df["GWh/yr"]      = energy_df["GWh/yr"].apply(_fmt_gwh)
        energy_df["% of total"]  = energy_df["% of total"].apply(_fmt_pct)
        st.dataframe(energy_df, use_container_width=True, hide_index=True)

        # ── Production output ────────────────────────────────────────────────
        st.markdown('<div style="margin-top:1.4rem;"></div>', unsafe_allow_html=True)
        st.markdown("**Annual production (steady state)**")
        prod_rows = [
            {"Output":          "Hydrogen (gross from electrolyser)", "Quantity": f"{pc['h2_gross_tpa']:,.0f} t/yr", "Notes": f"{pc['h2_gross_tpa']/365:,.1f} t/day"},
            {"Output":          "Hydrogen (net to HB)",                "Quantity": f"{pc['h2_net_tpa']:,.0f} t/yr",   "Notes": "No compression loss applied (EPI convention)"},
            {"Output":          "Nitrogen (from ASU)",                 "Quantity": f"{pc['n2_required_tpa']:,.0f} t/yr","Notes": f"Includes {p.n2_excess_pct*100:.0f}% excess design margin"},
            {"Output":          "Ammonia (net export)",                "Quantity": f"{pc['nh3_net_tpa']:,.0f} t/yr",  "Notes": f"{pc['nh3_net_ktpa']:.2f} ktpa · {pc['nh3_rate_td']:.0f} t/day"},
            {"Output":          "Oxygen (electrolysis byproduct)",     "Quantity": f"{pc['o2_tpa']:,.0f} t/yr",       "Notes": "Not monetized in base case (sell_o2 = False)"},
            {"Output":          "Water demand (H₂ + NH₃ process)",     "Quantity": f"{pc['water_total_m3y']:,.0f} m³/yr","Notes": f"~{pc['water_m3h']:.1f} m³/h"},
        ]
        st.dataframe(pd.DataFrame(prod_rows), use_container_width=True, hide_index=True)

        # ── Efficiency KPIs ──────────────────────────────────────────────────
        st.markdown('<div style="margin-top:1.4rem;"></div>', unsafe_allow_html=True)
        st.markdown("**Efficiency &amp; intensity KPIs**")
        # H2/NH3 efficiency ratios
        h2_per_mwh = (pc["h2_net_tpa"] * 1000) / (pc["elec_total_gwh"] * 1000) if pc["elec_total_gwh"] > 0 else 0  # kgH2/MWh
        nh3_per_mwh = (pc["nh3_net_tpa"] * 1000) / (total_with_hb * 1000) if total_with_hb > 0 else 0              # kgNH3/MWh (full energy basis)
        water_per_t_nh3 = pc["water_total_m3y"] / pc["nh3_net_tpa"] if pc["nh3_net_tpa"] > 0 else 0
        capex_per_tnh3 = (capex["total_capex"] * 1e6) / pc["nh3_net_tpa"] if pc["nh3_net_tpa"] > 0 else 0
        capex_per_mw_total = (capex["total_capex"] * 1e6) / (p.solar_mwac + p.electrolyser_mw + getattr(p,'hydro_ppa_mw',80)) if (p.solar_mwac + p.electrolyser_mw) > 0 else 0

        kpi_rows = [
            {"KPI":              "Energy intensity (NH₃ basis)",        "Value": f"{pc['overall_kwh_per_kgnh3']:.2f} kWh/kgNH₃",  "Benchmark": "Industry best ~10.0 · 2030 forecast 9–11"},
            {"KPI":              "Electrolyser SEC",                    "Value": f"{p.electrolyser_sec:.1f} kWh/kgH₂",            "Benchmark": "AWE 2026 commercial: 47–52 · 2030 best ~45"},
            {"KPI":              "H₂ yield per MWh (electrolyser)",     "Value": f"{h2_per_mwh:,.1f} kgH₂/MWh",                  "Benchmark": "At 50 kWh/kg → 20 kg/MWh theoretical"},
            {"KPI":              "NH₃ yield per MWh (full plant)",      "Value": f"{nh3_per_mwh:,.1f} kgNH₃/MWh",                "Benchmark": "Includes HB loop power"},
            {"KPI":              "Water intensity (NH₃ basis)",         "Value": f"{water_per_t_nh3:.1f} m³/tNH₃",               "Benchmark": "IRENA: 4–5 m³/tNH₃ green basis"},
            {"KPI":              "GHG intensity (grid scope 2)",        "Value": f"{pc['ghg_kg_co2_per_kg_nh3']:.2f} kgCO₂/kgNH₃","Benchmark": f"RED III RFNBO threshold: 3.0 · Grey NH₃ ~2.4 (Colombia grid {0.12*1000:.0f} gCO₂/kWh)"},
            {"KPI":              "CAPEX per tonne NH₃ output",          "Value": f"${capex_per_tnh3:,.0f}/tpa",                  "Benchmark": "Greenfield green NH₃ peer range: $3,200–4,200/tpa"},
            {"KPI":              "Plant availability (steady state)",   "Value": f"{p.plant_availability*100:.0f}%",             "Benchmark": "Operating target 95–98%; reflects Arup HAZID conclusions"},
        ]
        st.dataframe(pd.DataFrame(kpi_rows), use_container_width=True, hide_index=True)

        # ── Ramp profile ─────────────────────────────────────────────────────
        st.markdown('<div style="margin-top:1.4rem;"></div>', unsafe_allow_html=True)
        st.markdown("**Production ramp (Years 1–3)**")
        ramp_rows = [
            {"Year": "Year 1 (COD year)",        "Ramp factor": f"{p.ramp_yr1*100:.0f}%", "NH₃ output":  f"{pc['nh3_net_tpa']*p.ramp_yr1:,.0f} t",   "H₂ output": f"{pc['h2_net_tpa']*p.ramp_yr1:,.0f} t"},
            {"Year": "Year 2",                   "Ramp factor": f"{p.ramp_yr2*100:.0f}%", "NH₃ output":  f"{pc['nh3_net_tpa']*p.ramp_yr2:,.0f} t",   "H₂ output": f"{pc['h2_net_tpa']*p.ramp_yr2:,.0f} t"},
            {"Year": "Year 3+ (steady state)",   "Ramp factor": "100%",                    "NH₃ output":  f"{pc['nh3_net_tpa']:,.0f} t",              "H₂ output": f"{pc['h2_net_tpa']:,.0f} t"},
        ]
        st.dataframe(pd.DataFrame(ramp_rows), use_container_width=True, hide_index=True)

        st.markdown(f"""
        <div class="source-line">
            <strong>Provenance:</strong> Plant configuration (MW sizing, SEC, HB throughput, ASU) per Arup Resumen Ejecutivo Nov 2025 Tabla 6 for the Feasibility scenario,
            and per EPI 2026 procurement benchmarks (Chinese AWE, Casale 2026, LATAM solar) for the EPI Optimized scenario.
            Peripheral infrastructure (pipeline, export terminal) per Fichtner FIS0001954MRP001 Jan 2025 in both scenarios.
            <strong>Energy dispatch GWh values</strong> (solar generation, grid day/night top-ups, HB grid feed, curtailment) are from the EPI PVSyst three-period dispatch model — accepted by Arup §3 as the input basis — and are <em>not</em> recomputed when electrolyser sizing or SEC changes between scenarios.
            Production, water demand and KPIs are derived from these inputs.
            All metrics shown reflect the {SCENARIO_LABELS[scenario_key]} scenario at current sidebar overrides.
        </div>
        """, unsafe_allow_html=True)

    # --- Tab: CAPEX detail ---
    with tabs[2]:
        st.markdown('<div class="section-eyebrow">CAPEX Line Items (USD millions)</div>', unsafe_allow_html=True)

        cap_items = [
            ("CORE — Process plant (Arup scope)", "", ""),
            ("  Solar PV plant",                  "solar_plant",      "section"),
            ("  Grid interconnection",            "grid_interconnect", "section"),
            ("  Water treatment (H₂)",            "water_treatment",  "section"),
            ("  Electrolyser",                    "electrolyser",     "section"),
            ("  H₂ storage",                      "h2_storage",       "section"),
            ("  Water (NH₃)",                     "water_nh3",        "section"),
            ("  ASU",                             "asu",              "section"),
            ("  Haber-Bosch",                     "haber_bosch",      "section"),
            ("  NH₃ storage",                     "nh3_storage",      "section"),
            ("  Pipeline (to port)",              "pipeline",         "section"),
            ("  HB BoP + contingency",            "hb_bop",           "section"),
            ("  CORE SUBTOTAL",                   "core_total",       "subtotal"),
            ("PERIPHERAL — Fichtner scope",        "",                  ""),
            ("  Export facility (Mamonal)",       "export_facility",  "section"),
            ("  Power OHTL transmission",         "power_ohtl",       "section"),
            ("  Water pipeline",                  "wtp_pipeline",     "section"),
            ("  KOH electrolyte system",          "koh_system",       "section"),
            ("  Wastewater treatment",            "wwtp",             "section"),
            ("  +15% peripheral contingency",     "peripheral_contingency", "section"),
            ("  PERIPHERAL SUBTOTAL",             "peripheral_total", "subtotal"),
            ("Owner's costs (5%)",                "owners_costs",     "section"),
            ("GROSS CAPEX",                        "gross_total",       "total"),
            ("Less: VAT exemption (Ley 1715)",    "vat_saving",       "incentive"),
            ("Less: Tariff exemption",            "tariff_saving",    "incentive"),
            ("NET CAPEX (post-Ley 1715)",         "total_capex",      "net"),
        ]

        capex_rows = []
        for label, key, typ in cap_items:
            if not key:
                capex_rows.append({"Line item": label, "USD M": "", "% of Gross": ""})
            else:
                v = capex.get(key, 0)
                if typ == "incentive":
                    capex_rows.append({"Line item": label, "USD M": f"({v:,.1f})", "% of Gross": ""})
                else:
                    pct = v / capex["gross_total"] * 100 if capex["gross_total"] else 0
                    capex_rows.append({"Line item": label, "USD M": f"{v:,.1f}", "% of Gross": f"{pct:.1f}%"})

        st.dataframe(pd.DataFrame(capex_rows), use_container_width=True, height=580, hide_index=True)

        st.markdown(f"""
        <div class="source-line">
            Sources: Arup Resumen Ejecutivo Nov 2025 Tabla 6 (core process plant) · Fichtner FIS0001954MRP001 Jan 2025 (peripheral infrastructure) · EPI Excel CARTAGENA_Alk_H2_h2a_3_12_2025_v21.xlsm cross-reference.
        </div>
        """, unsafe_allow_html=True)

    # --- Tab: OPEX detail ---
    with tabs[3]:
        st.markdown('<div class="section-eyebrow">Annual Operating Expenditure</div>', unsafe_allow_html=True)
        opex_df = result["opex"]

        # Build OPEX summary
        avg_opex = pd.DataFrame({
            "Component": ["Energy (grid/PPA)", "Fixed O&M", "Solar O&M", "Var O&M (freight+insurance)", "Peripheral O&M", "Stack replacement (annualized)"],
            "Year-1 (USD M)": [
                opex_df.iloc[0]["energy_opex_musd"],
                opex_df.iloc[0]["om_opex_musd"],
                opex_df.iloc[0]["solar_om_musd"],
                opex_df.iloc[0]["var_om_musd"],
                opex_df.iloc[0]["peripheral_opex_musd"],
                opex_df["stack_replacement_musd"].sum() / 25,
            ],
            "Avg over 25 yrs (USD M)": [
                opex_df["energy_opex_musd"].mean(),
                opex_df["om_opex_musd"].mean(),
                opex_df["solar_om_musd"].mean(),
                opex_df["var_om_musd"].mean(),
                opex_df["peripheral_opex_musd"].mean(),
                opex_df["stack_replacement_musd"].sum() / 25,
            ],
        })
        avg_opex["% of total"] = avg_opex["Avg over 25 yrs (USD M)"] / avg_opex["Avg over 25 yrs (USD M)"].sum() * 100
        avg_opex["Year-1 (USD M)"] = avg_opex["Year-1 (USD M)"].round(2)
        avg_opex["Avg over 25 yrs (USD M)"] = avg_opex["Avg over 25 yrs (USD M)"].round(2)
        avg_opex["% of total"] = avg_opex["% of total"].round(1).astype(str) + "%"
        st.dataframe(avg_opex.set_index("Component"), use_container_width=True)

        # Annual OPEX chart
        fig_opex = go.Figure()
        components = [("energy_opex_musd", "Energy", NAVY),
                      ("om_opex_musd", "Fixed O&M", ACCENT),
                      ("solar_om_musd", "Solar O&M", "#4A6FA5"),
                      ("var_om_musd", "Variable O&M", AMBER),
                      ("peripheral_opex_musd", "Peripheral", GREY_500),
                      ("stack_replacement_musd", "Stack replacement", "#9CA8BD")]
        for key, name, color in components:
            fig_opex.add_trace(go.Bar(
                x=opex_df["op_year"], y=opex_df[key],
                name=name, marker_color=color,
                hovertemplate=f"<b>{name}</b><br>Year %{{x}}: $%{{y:.2f}}M<extra></extra>",
            ))
        fig_opex.update_layout(
            **PLOTLY_LAYOUT,
            barmode="stack",
            height=350,
            title=dict(text="Annual OPEX over project life (USD M)", font=dict(size=13, color=GREY_700)),
            xaxis_title="Operating Year",
            yaxis_title="USD millions",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_opex, use_container_width=True)

    # --- Tab: Cashflow ---
    with tabs[4]:
        st.markdown('<div class="section-eyebrow">25-Year Cashflow Statement (USD M)</div>', unsafe_allow_html=True)

        display_df = df[[
            "op_year", "calendar_year", "revenue_musd", "opex_musd",
            "ebitda_musd", "ebitda_margin_pct", "depreciation_musd",
            "ley_1715_deduction_musd", "nol_used_musd", "interest_musd",
            "tax_levered_musd", "project_fcf_musd", "equity_fcf_musd",
            "debt_outstanding_musd", "dscr",
        ]].copy()
        display_df.columns = [
            "Yr", "Cal Yr", "Revenue", "OpEx", "EBITDA", "EBITDA %",
            "Depreciation", "Ley 1715 ded.", "NOL used", "Interest",
            "Tax", "Project FCF", "Equity FCF", "Debt o/s", "DSCR"
        ]
        st.dataframe(display_df.set_index("Yr"), use_container_width=True, height=680)

    # --- Tab: Revenue ---
    with tabs[5]:
        st.markdown('<div class="section-eyebrow">Revenue Detail — Single-Stream Model</div>', unsafe_allow_html=True)
        rev_df = result["revenue"]
        rev_display = rev_df[[
            "op_year", "nh3_revenue_musd", "nh3_price_usd_t",
        ]].copy()
        rev_display.columns = ["Yr", "NH₃ revenue (USD M)", "NH₃ price (USD/t FOB)"]
        # Add running total
        rev_display["Cumulative (USD M)"] = rev_display["NH₃ revenue (USD M)"].cumsum().round(1)
        st.dataframe(rev_display.set_index("Yr"), use_container_width=True, height=680)

        st.markdown(f"""
        <div class="source-line">
            <strong>Single-stream model (v3.3):</strong> Revenue = NH₃ export volume × FOB Cartagena USD price.
            Year-1 base ${p.nh3_price_base:.0f}/t, escalating 2% nominal/yr.
            No H2Global HPA, Reficar H₂, or O₂ co-product in base case — those are upside sensitivities.
            <br><br>
            <strong>Reference benchmarks (FOB to producer):</strong> H2Global Window 1 Egypt = $868/t (€811 × 1.07, July 2024) ·
            Yara-ACME Oman binding ≈ $650-700/t · BNEF 2030 forecast $700-900/t · Grey NH₃ spot CFR NW Europe (April 2026) $608-745/t.
        </div>
        """, unsafe_allow_html=True)

    # --- Tab: LCOA build ---
    with tabs[6]:
        st.markdown('<div class="section-eyebrow">LCOA Build-up (H2A method)</div>', unsafe_allow_html=True)

        breakdown = compute_lcoa_breakdown(p, capex, result["production"])

        if breakdown:
            bdf = pd.DataFrame({
                "Component": list(breakdown.keys()),
                "USD/t NH₃": [round(v, 1) for v in breakdown.values()],
            })
            bdf["% of total"] = (bdf["USD/t NH₃"] / bdf["USD/t NH₃"].sum() * 100).round(1).astype(str) + "%"
            st.dataframe(bdf, use_container_width=True, height=480, hide_index=True)

        st.markdown('<div class="section-eyebrow">LCOA tiers and methodologies</div>', unsafe_allow_html=True)
        method_df = pd.DataFrame({
            "View": [
                "Ex-works (core plant only)",
                "FOB Cartagena (+ Fichtner peripheral)",
                "CIF Europe (+ ocean freight $60/t)",
                "DCF (PV all costs / PV production)",
                "H2A/CRF nameplate (NREL standard)",
                "EPI legacy (avg method)",
            ],
            "USD/t NH₃": [
                f"${m['lcoa_ex_works_usd_t']:.0f}",
                f"${m['lcoa_fob_usd_t']:.0f}",
                f"${m['lcoa_cif_usd_t']:.0f}",
                f"${m['lcoa_dcf_usd_t']:.0f}",
                f"${m['lcoa_h2a_usd_t']:.0f}",
                f"${m['lcoa_epi_usd_t']:.0f}",
            ],
            "Benchmark / use": [
                "Arup Nov 2025 ($812/t); Chile/Brazil feasibility ranges",
                "H2Global Window 1 FOB Egypt ($868/t); Yara-ACME Oman",
                "H2Global Window 1 delivered Rotterdam ($1,070/t)",
                "Internal — includes stack replacements properly",
                "Industry-standard CRF on nameplate output",
                "EPI Excel legacy convention (analyst reference)",
            ],
        })
        st.dataframe(method_df.set_index("View"), use_container_width=True)

    # --- Tab: Tax & Financing ---
    with tabs[7]:
        st.markdown('<div class="section-eyebrow">Tax & Financing Detail</div>', unsafe_allow_html=True)

        # ATOME comp context
        st.markdown(f"""
        <div class="note-callout">
            <strong style="color: {NAVY};">Financing benchmark — ATOME Villeta (FID 23 April 2026):</strong>
            $665M total project · <strong>$420M debt (63%)</strong> · $245M equity (37%) · 15-year tenor.
            Debt consortium: <strong>IDB Invest (coordinator), IFC, EIB ($135M), FMO, Green Climate Fund ($50M concessional)</strong>.
            Equity led by <strong>Hy24</strong> + IFC + KfW DEG + IFDK + EFSD+ + Sudameris + ATOME PLC.
            EPC: Casale fixed-price $465M lumpsum. Offtake: Yara 10-yr take-or-pay.
            This is the live comparable for Cartagena H₂ — the same DFI consortium and structure
            Electryon would target. Our model default ({int(p.debt_share*100)}% / {int((1-p.debt_share)*100)}%)
            mirrors ATOME's actual cleared structure.
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### Financing structure (current scenario)")
            fin_df = pd.DataFrame({
                "Parameter": [
                    "Total CAPEX (net)", "Debt", "Equity",
                    "Debt share", "Debt interest rate", "Debt tenor (years)",
                    "Annual debt service", "Min DSCR",
                    "WACC (Project NPV discount rate)",
                    "Cost of equity Ke (Equity NPV discount rate)",
                ],
                "Value": [
                    f"${m['total_capex_musd']:.0f}M",
                    f"${m['debt_musd']:.0f}M",
                    f"${m['equity_musd']:.0f}M",
                    f"{p.debt_share*100:.0f}%",
                    f"{p.debt_interest_rate*100:.1f}%",
                    f"{p.debt_tenor_years}",
                    f"${m['debt_musd'] * p.debt_interest_rate * (1+p.debt_interest_rate)**p.debt_tenor_years / ((1+p.debt_interest_rate)**p.debt_tenor_years - 1):.1f}M",
                    f"{m['min_dscr']:.2f}×" if m['min_dscr'] else "—",
                    f"{m['wacc_pct']:.1f}%",
                    f"{m['cost_of_equity_pct']:.1f}%",
                ],
            })
            st.dataframe(fin_df.set_index("Parameter"), use_container_width=True)

        with col2:
            st.markdown("##### ATOME Villeta comp (April 2026)")
            atome_df = pd.DataFrame({
                "Parameter": [
                    "Total project size", "Debt amount", "Equity amount",
                    "Debt share", "Debt tenor",
                    "Lead debt provider",
                    "Other debt providers",
                    "Lead equity",
                    "Other equity",
                    "EPC contractor",
                    "Offtake",
                ],
                "Value": [
                    "$665M",
                    "$420M",
                    "$245M",
                    "63%",
                    "15 years",
                    "IDB Invest",
                    "IFC, EIB ($135M), FMO, GCF ($50M concessional)",
                    "Hy24 (Clean H₂ Infrastructure Fund)",
                    "IFC, KfW DEG, IFDK, EFSD+, Sudameris, ATOME, Casale",
                    "Casale ($465M fixed-price)",
                    "Yara (10-yr take-or-pay, 260 ktpa CAN)",
                ],
            })
            st.dataframe(atome_df.set_index("Parameter"), use_container_width=True, height=420)

        st.markdown("##### Tax structure (current scenario)")
        tax_df = pd.DataFrame({
            "Parameter": [
                "Income tax rate", "Ley 1715 deduction (% of gross CAPEX)",
                "Ley 1715 period (years)", "Ley 1715 annual amount",
                "Cap (% of taxable income)",
                "Depreciation method", "Depreciation period (years)",
                "NOL carryforward (years)",
                "Freight basis (LCOA)",
                "Lifetime tax paid (25 yrs)",
            ],
            "Value": [
                f"{p.income_tax_rate*100:.0f}% (FNCER — Decreto 829)",
                f"{p.income_tax_deduction_pct*100:.0f}%",
                f"{p.income_tax_deduction_years}",
                f"${capex['gross_total'] * p.income_tax_deduction_pct / p.income_tax_deduction_years:.1f}M/yr",
                f"{p.income_tax_deduction_max_pct_of_taxable*100:.0f}% of taxable",
                "Colombian 5-yr straight-line (FNCER)",
                "5",
                f"{p.nol_carryforward_years} (Estatuto Tributario Art. 147)",
                "FOB Cartagena — offtaker pays ocean freight (H2Global structure)",
                f"${m['lifetime_tax_musd']:.0f}M",
            ],
        })
        st.dataframe(tax_df.set_index("Parameter"), use_container_width=True)

        st.markdown(f"""
        <div class="note-callout">
            <strong style="color: {NAVY};">v3.3 changelog:</strong>
            (1) Single-stream revenue model — NH₃ export × FOB Cartagena USD price. H2Global/Reficar/O₂ removed from base case.
            (2) NH₃ price $920/t FOB base, 2% nominal escalation — defensible vs H2Global Window 1 FOB $868/t.
            (3) Equity NPV now discounted at cost of equity Ke (15% default), not WACC — methodologically correct.
            (4) Default energy: $55/MWh long-term hydro PPA with toggle to $78/MWh industrial tariff.
            (5) Scenarios reduced to two: Feasibility (Arup audit reference) and EPI Optimized (2026 procurement reality).
            (6) EPI Optimized: Chinese AWE ($400k/MW), LATAM solar ($620k/MWac), Casale 2026 HB ($80k/tpd), SEC 47 kWh/kg.
            (7) EPI Optimized OPEX scaled with CAPEX reduction.
            <br><br>
            <strong style="color: {NAVY};">v3.2 corrections (engine, retained):</strong>
            Project NPV nets total CAPEX. Income tax 30% FNCER with NOL carryforward (was 0%).
            Colombian 5-yr straight-line depreciation (was U.S. MACRS). Project FCF uses unlevered tax;
            equity gets debt tax shield. 15-year debt tenor (was 7y). Default leverage 63/37 (ATOME Villeta).
            Three-tier LCOA framework (ex-works / FOB Cartagena / CIF Europe).
        </div>
        """, unsafe_allow_html=True)


# =============================================================================
# FOOTER
# =============================================================================

st.markdown(f"""
<div style="margin-top: 4rem; padding: 1.5rem 0; border-top: 1px solid {GREY_300}; font-family: 'EB Garamond', serif; font-style: italic; font-size: 0.85rem; color: {GREY_500}; text-align: center;">
    Electryon Power Inc. · Cartagena H₂ Investment Model v3.3 · {SCENARIO_LABELS[scenario_key]} scenario active
    <br>
    Confidential and proprietary. Figures subject to FEED refinement and due diligence.
</div>
""", unsafe_allow_html=True)
