"""
Cartagena H2 — Green Ammonia Financial Model Engine  v3.1
=========================================================
Parameters derived directly from EPI Excel models (March 2026):
  - CARTAGENA_H2_h2a_12_03_2026_v22.xlsm  (H2A/NREL dispatch + LCOH)
  - CARTAGENA_H2_NH3_7_03_2026_v22.xlsm   (H2FAST NH3 financial model)

Validated outputs at defaults:
  H2: 20,192 t/yr  NH3: 111.5 ktpa  H2A LCOA: ~$660/t  Equity IRR: target 10%

Key methodology:
  Three-period dispatch (solar / grid-day / grid-night)
  EPI direct GWh values used — all solar goes to electrolyser,
  curtailed surplus is sold to grid as byproduct revenue.
  HB uses combined 98% efficiency (conversion + availability).
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class ProjectParams:
    # ── Project ──────────────────────────────────────────────────────────────
    project_life_years:  int   = 25
    cod_year:            int   = 2030
    construction_years:  int   = 2

    # ── Solar PV (PVSyst: Cartagena Turbana, Meteonorm 8.1) ──────────────────
    solar_mwac:              float = 250.0    # EPI: 250 MWac single-axis tracking
    solar_capacity_factor:   float = 0.2460   # EPI: 0.24604 annual CF
    solar_capex_per_mwac:    float = 800_000  # EPI: $800k/MWac
    solar_opex_per_mwac:     float = 13_000   # USD/MWac/yr O&M
    # EPI direct GWh values (H2 INPUTS-RESULTS R13,25,31,58)
    # These are used directly -- set to 0 to use formula-derived values
    solar_gwh_yr:            float = 615.579  # EPI R13: gross solar GWh/yr
    grid_day_gwh_yr:         float = 35.296   # EPI R25: grid day top-up GWh/yr
    grid_night_gwh_yr:       float = 358.758  # EPI R31: grid night GWh/yr
    grid_day_complementarity:  float = 0.10   # EPI R23: 10% of elec capacity from grid during day
    grid_night_complementarity:float = 0.32   # EPI R29: 32% of elec capacity from grid at night
    hb_grid_gwh_yr:          float = 66.872   # EPI R58: HB process grid GWh/yr
    solar_curtailed_gwh:     float = 18.451   # EPI R83: surplus sold to grid

    # ── Grid electricity prices (EPI R105-107, COP→USD at 4228 COP/USD) ─────
    grid_price_day_kwh:      float = 0.0773   # USD/kWh HV day  (EPI: 0.07734)
    grid_price_night_kwh:    float = 0.06961  # USD/kWh night   (EPI R107: COP 294.35 @ 4228.54 COP/USD)
    grid_price_hb_kwh:       float = 0.0773   # USD/kWh HB grid
    grid_price_escalation:   float = 0.025    # 2.5%/yr

    # ── Electrolyser — Alkaline (AWE), Longi units ───────────────────────────
    electrolyser_mw:              float = 180.0   # EPI: 180 MW AWE
    electrolyser_sec:             float = 50.0    # EPI: 50 kWh/kgH2 (BoP incl.)
    electrolyser_availability:    float = 0.98    # EPI: 98% utilisation
    electrolyser_degradation:     float = 0.005   # 0.5%/yr SEC increase
    electrolyser_capex_all_in_mw: float = 612_133 # EPI: $612k/MW all-in (DATABASE R18)
    water_l_per_kgh2:             float = 22.3    # EPI R50: IRENA 22.3 L/kgH2
    stack_life_hours:             float = 90_000
    stack_replacement_pct:        float = 0.15

    # ── HB synthesis ─────────────────────────────────────────────────────────
    hb_h2_per_tnh3:               float = 0.17755  # EPI R61: stoichiometric
    hb_combined_efficiency:       float = 0.98     # EPI R62: combined eff+avail
    # NOTE: EPI does NOT separately apply HB_availability on top of hb_combined_efficiency

    # ── ASU ──────────────────────────────────────────────────────────────────
    n2_per_tnh3:                  float = 0.823    # stoichiometric tN2/tNH3
    n2_excess_pct:                float = 0.15     # EPI R74: 15% excess
    asu_capex_per_kgd_n2:         float = 60.4     # EPI R95: $1,450/kg/h → /kg/d

    # ── Plant-level ───────────────────────────────────────────────────────────
    plant_availability:           float = 0.98     # EPI: 98% long-term utilisation
    ramp_yr1:                     float = 0.85
    ramp_yr2:                     float = 0.95

    # ── CAPEX (EPI H2 INPUTS-RESULTS R85-100) ────────────────────────────────
    grid_interconnect_capex:      float = 10_000_000  # EPI R87: $10M 230kV
    water_capex_per_m3h:          float = 132_000     # EPI R88/186: ARUP $132k/m3/h
    hb_capex_per_kgd:             float = 137.5       # EPI R96: $3,300/kg/h → /kg/d
    nh3_storage_capex_per_t:      float = 1_000       # EPI R97: $1,000/tNH3
    nh3_storage_t:                float = 9_160       # EPI: 9,160 t
    pipeline_capex_per_km:        float = 1_600_000   # EPI R98: $16M / 10 km
    pipeline_km:                  float = 10.0        # EPI: 10 km to port
    hb_bop_pct:                   float = 0.30        # EPI R99: 30% BoP+contingency
    water_nh3_capex_per_m3y:      float = 15.07       # EPI R94: water for NH3

    # ── Fichtner peripheral ───────────────────────────────────────────────────
    export_facility_musd:         float = 48.0
    power_ohtl_musd:              float = 9.0
    wtp_pipeline_musd:            float = 8.7
    koh_system_musd:              float = 7.1
    wwtp_musd:                    float = 3.8
    peripheral_contingency_pct:   float = 0.15

    # ── OPEX (EPI NH3 Parameters R46-52, G0 R95-107) ────────────────────────
    freight_insurance_per_t:      float = 60.0    # EPI R46: $60/tNH3
    fixed_opex_annual_musd:       float = 13.72   # EPI G0 R97: $13.72M/yr
    om_escalation_pct:            float = 0.025

    # ── Colombia H2 offtake (v3.3: DISABLED — export-only project) ──────────
    # Set to zero by default. Project is positioned as 100% green ammonia export.
    # If Reficar offtake materializes, this would reduce NH3 export volume.
    colombia_h2_ktpa:             float = 0.0
    colombia_h2_price_per_kg:     float = 4.02    # USD/kgH2 — kept for sensitivity case

    # ── O2 co-product (v3.3: DISABLED in base case) ─────────────────────────
    # O2 is a real electrolysis co-product but merchant market is thin.
    # Toggle sell_o2=True only for upside sensitivity analysis.
    o2_price_per_kg:              float = 0.01    # EPI R52
    sell_o2:                      bool  = False   # v3.3: disabled in base case
    elec_surplus_price_kwh:       float = 0.040   # EPI R51: sell surplus to grid

    # ── Colombian fiscal incentives (Ley 1715/2099) ───────────────────────────
    # BUG FIX v3.2 #2: Income tax rate was hardcoded to 0%. Correct rates:
    #   • 35% general Colombian corporate rate (Estatuto Tributario Art. 240)
    #   • 30% reduced rate available for FNCER-qualifying projects (Decreto 829)
    # We default to 30% (FNCER) since Cartagena H2 qualifies.
    income_tax_rate:              float = 0.30   # FNCER rate (Decreto 829)
    income_tax_deduction_pct:     float = 0.50   # Ley 1715: 50% of investment deductible
    income_tax_deduction_years:   int   = 15     # over 15 years
    # BUG FIX v3.2 #2/#4: NOL carryforward (Estatuto Tributario Art. 147)
    nol_carryforward_years:       int   = 12     # Colombia: 12-year NOL carryforward
    # Cap on annual income tax deduction (Ley 1715: cannot exceed 50% of net taxable income)
    income_tax_deduction_max_pct_of_taxable: float = 0.50
    vat_exempt:                   bool  = True
    vat_rate:                     float = 0.19
    tariff_exempt:                bool  = True
    tariff_rate:                  float = 0.10
    imported_capex_fraction:      float = 0.60

    # ── Financing ─────────────────────────────────────────────────────────────
    # v3.2: Default leverage updated to match ATOME Villeta comp (FID April 2026):
    #   $665M project, $420M debt, $245M equity = 63% / 37% leverage.
    #   ATOME secured the structure with IDB Invest, IFC, EIB, FMO, GCF — the
    #   same DFI consortium Cartagena would target. The 63/37 ratio is what
    #   DFI underwriters actually wrote in 2026; 75/25 was an aspirational
    #   EPI internal assumption that no live deal has cleared.
    debt_share:                   float = 0.63  # ATOME Villeta comp (April 2026 FID)
    debt_interest_rate:           float = 0.050  # EPI H2ALite R62: 5% nominal
    # BUG FIX v3.2 #6: Increased default debt tenor from 7 to 15 years.
    # Project finance for green H2/NH3 export typically uses 12-18 year tenors
    # matching offtake contract length (e.g., H2Global 10-yr HPA + 5-yr extension).
    # ATOME Villeta confirmed 15-yr tenor with DFI consortium.
    debt_tenor_years:             int   = 15
    wacc:                         float = 0.10   # 10% nominal discount rate
    inflation_rate:               float = 0.025

    # ── LCOA pricing basis (v3.2): FOB Cartagena vs CIF delivered ─────────────
    # FOB Cartagena: ammonia loaded onto vessel at Puerto Bahía/Mamonal.
    #   Offtaker pays for ocean shipping. This is the H2Global benchmark basis
    #   (€811/t FOB Egypt -> producer = $868/t at 1.07 EUR/USD).
    # CIF/delivered: includes ocean freight + insurance to destination.
    #   Higher LCOA but matches H2Global's "delivered Europe" price of €1,000/t.
    # The Fichtner export facility CAPEX ($48M) and OPEX ($2.21M/yr) cover the
    # refrigerated terminal, BOG re-liquefaction, loading arms, and pipeline up
    # to ship loading flange — these are always included (FOB infrastructure).
    # The freight_insurance_per_t covers ONLY ocean shipping post-loading.
    freight_basis:                str   = "FOB"   # "FOB" or "CIF"

    # ── NH3 price curve ───────────────────────────────────────────────────────
    # ── NH3 pricing (v3.3: simplified — single USD price, no EUR mixing) ─────
    # Base case $920/t FOB Cartagena — defensible institutional anchor:
    #   • 6% above H2Global Window 1 FOB Egypt ($868/t = €811 × 1.07) —
    #     justified by structural green NH3 premium expected by 2030 COD,
    #     RFNBO compliance demand, Colombia's 4,000km logistics advantage to EU
    #   • Above ACME-Yara Oman binding ($650-700/t FOB)
    #   • Within upper BNEF 2030 green NH3 forecast range ($700-900/t base case)
    #   • Below H2Global Window 1 delivered Rotterdam ($1,070/t CIF)
    nh3_price_base:               float = 920.0    # USD/t FOB Cartagena
    nh3_price_bear:               float = 700.0
    nh3_price_bull:               float =  900.0
    nh3_price_floor:              float = 650.0
    # v3.3: Use NOMINAL escalation only (2%/yr) — no separate "real change" knob.
    # Green NH3 has structural support from RFNBO compliance; no negative real-change story.
    nh3_price_escalation:         float = 0.02     # 2% nominal/yr
    # Legacy real-change params kept at 0 to maintain backward compatibility
    nh3_real_change_base:         float = 0.0
    nh3_real_change_bear:         float = 0.0
    nh3_real_change_bull:         float = 0.0

    # ── Cost of equity (v3.3: distinct from WACC for proper Equity NPV) ──────
    # Equity NPV is now correctly discounted at cost of equity (Ke), not WACC.
    # Project NPV remains discounted at WACC (correct for unlevered FCF).
    # Default Ke = 15% reflects:
    #   • US 10-yr Treasury ~4.0-4.5% (early 2026)
    #   • Colombia country risk premium ~3-4%
    #   • Renewable project risk premium ~5-6%
    cost_of_equity:               float = 0.15     # Ke = 15% base case

    # ── H2Global benchmark (REFERENCE ONLY in v3.3 — NOT a revenue stream) ───
    # H2Global Window 1 ($868/t FOB Egypt = €811 × 1.07) is preserved here for
    # use in the LCOA benchmark display only. It is NOT used in revenue
    # calculations — Cartagena did not win Window 1 and Window 2 outcome is
    # speculative. If/when an HPA is signed, this becomes an upside case.
    h2global_volume_ktpa:         float = 0.0      # v3.3: no committed H2Global volume
    h2global_net_price_eur:       float = 811.0    # reference only
    eur_usd:                      float = 1.07
    h2global_escalation:          float = 0.02
    h2global_contract_years:      int   = 0        # v3.3: no committed contract

    # ── Colombia H2 sales (v3.3: REMOVED — export-only project) ──────────────
    # The project is positioned as a green ammonia export facility. Any
    # domestic H2 sales (e.g. to Reficar) would reduce export ammonia volume
    # proportionally and should be modeled as an alternative scope.
    # (Variables retained at zero for backward compatibility.)

    # ── O2 co-product (v3.3: disabled by default) ────────────────────────────
    # O2 is a real co-product of electrolysis but the merchant market is small
    # and pricing speculative. Disabled in base case; can be toggled on as
    # upside sensitivity.

    # ── Legacy aliases (backward compat with app.py) ──────────────────────────
    solar_mwp:                    float = 250.0
    hydro_ppa_mw:                 float = 80.0
    hydro_ppa_cf:                 float = 0.95
    hydro_ppa_cost:               float = 57.0
    lcoe_ppa:                     float = 57.0
    total_opex_per_tnh3:          float = 499.0
    energy_opex_per_tnh3:         float = 499.0
    ppa_escalation_pct:           float = 0.025
    peripheral_opex_mpa:          float = 2.21
    peripheral_opex_escalation:   float = 0.025
    om_pct_of_capex:              float = 0.015
    h2_compression_loss:          float = 0.005


def compute_process_chain(p: ProjectParams) -> Dict:
    """
    EPI three-period dispatch. Uses calibrated GWh values from H2 INPUTS-RESULTS.
    ALL solar goes to electrolyser; curtailed surplus (~18.5 GWh) sold to grid.
    HB uses combined 98% efficiency (no separate HB availability factor).

    Validated: H2=20,192 t/yr, NH3=111.5 ktpa, Elec=1,009.6 GWh/yr
    """
    # ── Energy inputs ─────────────────────────────────────────────────────────
    # Scale EPI base values by slider adjustments
    # Base: 250 MWac -> user may change solar_mwac
    solar_scale     = p.solar_mwac / 250.0
    elec_scale      = p.electrolyser_mw / 180.0
    sec_scale       = 50.0 / p.electrolyser_sec  # higher SEC = less H2

    solar_gwh       = p.solar_gwh_yr   * solar_scale
    # Grid energy computed from complementarity factors × electrolyser capacity × hours
    # Day: electrolyser_mw × comp × daylight_hours × 365
    # Night: grid_night_mw × comp × night_hours × 365
    # If user has overridden the fixed GWh values, use those; otherwise compute from factors
    _comp_day   = getattr(p, 'grid_day_complementarity', 0.10)
    _comp_night = getattr(p, 'grid_night_complementarity', 0.32)
    _computed_day   = p.electrolyser_mw * _comp_day   * 10 * 365 / 1000  # GWh/yr
    _computed_night = p.hydro_ppa_mw    * _comp_night * 14 * 365 / 1000  # GWh/yr
    # Use computed values if complementarity params are set, else use EPI fixed values
    grid_day_gwh    = _computed_day   if _comp_day   != 0.10 else p.grid_day_gwh_yr
    grid_night_gwh  = _computed_night if _comp_night != 0.32 else p.grid_night_gwh_yr
    hb_grid_gwh     = p.hb_grid_gwh_yr
    solar_curtailed = p.solar_curtailed_gwh * solar_scale

    # Total electrolyser input: all solar + grid top-ups
    elec_total_gwh  = solar_gwh + grid_day_gwh + grid_night_gwh

    # ── H2 production ─────────────────────────────────────────────────────────
    # EPI: no availability reduction on raw production; 98% = scheduling factor
    h2_gross_t   = elec_total_gwh * 1e6 / p.electrolyser_sec / 1_000  # tonnes
    h2_net_t     = h2_gross_t  # EPI: no compression loss applied (H2 gross = H2 net)

    # ── NH3 via HB ────────────────────────────────────────────────────────────
    # EPI: combined efficiency 0.98 covers HB conversion + availability
    nh3_net_t    = h2_net_t / p.hb_h2_per_tnh3 * p.hb_combined_efficiency

    # Note: hb_combined_efficiency already captures HB availability.
    # EPI does NOT apply a separate plant_availability factor here.
    # plant_availability is already embedded in the electrolyser dispatch.

    # ── N2 from ASU ──────────────────────────────────────────────────────────
    n2_required_t = nh3_net_t * p.n2_per_tnh3 * (1 + p.n2_excess_pct)
    n2_rate_th    = nh3_net_t * p.n2_per_tnh3 / 8_760  # stoichiometric rate (no excess) matches EPI R60

    # ── O2 co-product ────────────────────────────────────────────────────────
    o2_tpa = h2_gross_t * 8.0  # 8 kgO2 per kgH2 from electrolysis

    # ── Water ────────────────────────────────────────────────────────────────
    water_h2_m3y   = h2_gross_t * 1_000 * p.water_l_per_kgh2 / 1_000
    water_nh3_m3y  = nh3_net_t * 3.0
    water_total_m3y = water_h2_m3y + water_nh3_m3y
    water_m3h       = water_total_m3y / (8_760 * p.plant_availability)

    # ── Grid energy costs (EPI R80: $24.8M/yr yr1) ───────────────────────────
    annual_grid_cost_musd = (
        grid_day_gwh   * p.grid_price_day_kwh   +
        grid_night_gwh * p.grid_price_night_kwh  +
        hb_grid_gwh    * p.grid_price_hb_kwh
    )  # GWh * $/kWh = k$ ... wait, GWh * $/kWh = M$ directly? No.
    # GWh * 1000 = MWh, MWh * 1000 = kWh, $/kWh = $
    # GWh * $/kWh = GWh * $/kWh = 1e6 kWh * $/kWh = 1e6 $ = 1 M$
    # So: GWh * price_per_kwh = M$ ✓

    # ── Electrolyser load factor ──────────────────────────────────────────────
    elec_rated_gwh  = p.electrolyser_mw * 8_760 / 1_000  # GWh at full capacity
    elec_load_pct   = elec_total_gwh / elec_rated_gwh * 100 if elec_rated_gwh > 0 else 0
    solar_share_pct = solar_gwh / elec_total_gwh * 100 if elec_total_gwh > 0 else 0

    # ── GHG intensity ─────────────────────────────────────────────────────────
    grid_total_gwh           = grid_day_gwh + grid_night_gwh + hb_grid_gwh
    colombia_grid_kgco2_kwh  = 0.12  # kgCO2/kWh Colombian grid (~80% hydro)
    ghg = (grid_total_gwh * 1e6 * colombia_grid_kgco2_kwh
           / (nh3_net_t * 1_000) if nh3_net_t > 0 else 0)

    return {
        # Energy (GWh/yr unless noted)
        "solar_gwh_yr":          round(solar_gwh,         2),
        "solar_curtailed_gwh":   round(solar_curtailed,   2),
        "grid_day_gwh":          round(grid_day_gwh,      2),
        "grid_night_gwh":        round(grid_night_gwh,    2),
        "hb_grid_gwh":           round(hb_grid_gwh,       2),
        "elec_total_gwh":        round(elec_total_gwh,    2),
        "elec_load_pct":         round(elec_load_pct,     1),
        "solar_share_pct":       round(solar_share_pct,   1),
        "grid_share_pct":        round(100-solar_share_pct, 1),
        # H2 (tonnes/yr)
        "h2_gross_tpa":          round(h2_gross_t,        1),
        "h2_net_tpa":            round(h2_net_t,          1),
        "h2_to_hb_tpa":          round(h2_net_t,          1),
        # N2 (tonnes/yr)
        "n2_required_tpa":       round(n2_required_t,     1),
        "n2_rate_th":            round(n2_rate_th,        2),
        # NH3 (tonnes/yr)
        "nh3_net_tpa":           round(nh3_net_t,         1),
        "nh3_net_ktpa":          round(nh3_net_t / 1_000, 2),
        "nh3_rate_td":           round(nh3_net_t / 365,   1),
        # O2 (tonnes/yr)
        "o2_tpa":                round(o2_tpa,            0),
        # Water
        "water_h2_m3y":          round(water_h2_m3y,      0),
        "water_nh3_m3y":         round(water_nh3_m3y,     0),
        "water_total_m3y":       round(water_total_m3y,   0),
        "water_m3h":             round(water_m3h,         1),
        # Costs
        "annual_grid_cost_musd": round(annual_grid_cost_musd, 2),
        # KPIs
        "ghg_kg_co2_per_kg_nh3": round(ghg, 4),
        "overall_kwh_per_kgnh3": round(
            elec_total_gwh * 1e6 / (nh3_net_t * 1_000), 2) if nh3_net_t > 0 else 0,
        # Legacy aliases
        "solar_mwh_yr":          round(solar_gwh * 1_000,       0),
        "elec_mwh_consumed":     round(elec_total_gwh * 1_000,  0),
        "elec_solar_mwh":        round(solar_gwh * 1_000,       0),
        "elec_hydro_mwh":        round(grid_night_gwh * 1_000,  0),
        "hydro_ppa_mwh_used":    round(grid_night_gwh * 1_000,  0),
        "parasitic_mwh_yr":      round(hb_grid_gwh * 1_000,     0),
        "total_power_mwh_yr":    round((solar_gwh+grid_day_gwh+grid_night_gwh)*1_000, 0),
        "hydro_mwh_yr":          round(grid_night_gwh * 1_000,  0),
        "power_surplus_mwh":     round(solar_curtailed * 1_000, 0),
        "h2_colombia_tpa":       p.colombia_h2_ktpa * 1_000,
    }


def compute_capex(p: ProjectParams) -> Dict[str, float]:
    """All values in USD millions. Validated against EPI: core~$444M gross."""
    pc      = compute_process_chain(p)
    nh3_tpa = pc["nh3_net_tpa"]
    n2_tpa  = pc["n2_required_tpa"]
    nh3_kgd = nh3_tpa / 365 * 1_000
    n2_kgd  = n2_tpa  / 365 * 1_000
    c = {}

    # ── Electrolysis block ────────────────────────────────────────────────────
    c["solar_plant"]        = p.solar_mwac * p.solar_capex_per_mwac / 1e6
    c["grid_interconnect"]  = p.grid_interconnect_capex / 1e6
    water_h2_m3h = pc["water_h2_m3y"] / (8_760 * p.plant_availability)
    c["water_treatment"]    = water_h2_m3h * p.water_capex_per_m3h / 1e6
    c["electrolyser"]       = p.electrolyser_mw * p.electrolyser_capex_all_in_mw / 1e6
    # H2 storage: 0.18 days × daily production × $1,050/kg
    h2_storage_kg = pc["h2_gross_tpa"] / 365 * 1_000 * 0.18
    c["h2_storage"]         = h2_storage_kg * 1_050 / 1e6
    c["electrolysis_total"] = sum(c[k] for k in
        ["solar_plant","grid_interconnect","water_treatment","electrolyser","h2_storage"])

    # ── HB block ──────────────────────────────────────────────────────────────
    c["water_nh3"]   = nh3_tpa * 3.0 * p.water_nh3_capex_per_m3y / 1e6
    c["asu"]         = n2_kgd  * p.asu_capex_per_kgd_n2 / 1e6
    c["haber_bosch"] = nh3_kgd * p.hb_capex_per_kgd / 1e6
    c["nh3_storage"] = p.nh3_storage_t * p.nh3_storage_capex_per_t / 1e6
    c["pipeline"]    = p.pipeline_km * p.pipeline_capex_per_km / 1e6
    hb_sub           = sum(c[k] for k in
        ["water_nh3","asu","haber_bosch","nh3_storage","pipeline"])
    c["hb_bop"]      = hb_sub * p.hb_bop_pct
    c["hb_total"]    = hb_sub + c["hb_bop"]
    c["core_total"]  = c["electrolysis_total"] + c["hb_total"]

    # ── Peripheral ────────────────────────────────────────────────────────────
    c["export_facility"] = p.export_facility_musd
    c["power_ohtl"]      = p.power_ohtl_musd
    c["wtp_pipeline"]    = p.wtp_pipeline_musd
    c["koh_system"]      = p.koh_system_musd
    c["wwtp"]            = p.wwtp_musd
    periph_sub = (p.export_facility_musd + p.power_ohtl_musd +
                  p.wtp_pipeline_musd + p.koh_system_musd + p.wwtp_musd)
    c["peripheral_contingency"] = periph_sub * p.peripheral_contingency_pct
    c["peripheral_total"]       = periph_sub + c["peripheral_contingency"]

    c["owners_costs"] = (c["core_total"] + c["peripheral_total"]) * 0.05
    gross             = c["core_total"] + c["peripheral_total"] + c["owners_costs"]

    # ── Colombian Ley 1715 savings ─────────────────────────────────────────────
    equip_base        = c["core_total"] + periph_sub
    c["vat_saving"]   = equip_base * p.vat_rate if p.vat_exempt else 0.0
    c["tariff_saving"]= c["core_total"] * p.imported_capex_fraction * p.tariff_rate if p.tariff_exempt else 0.0
    c["total_incentive_saving"] = c["vat_saving"] + c["tariff_saving"]
    c["gross_total"]  = round(gross, 2)
    c["total_capex"]  = round(gross - c["total_incentive_saving"], 2)

    # Legacy aliases
    c["nh3_storage_onsite"] = c["nh3_storage"]
    c["aux_h2"]             = c["h2_storage"]
    c["aux_nh3"]            = c["hb_bop"]
    c["core_contingency"]   = c["hb_bop"]
    c["nh3_pipeline"]       = c["pipeline"]
    return {k: round(v, 3) for k, v in c.items()}


def compute_lcoa_h2a(p: ProjectParams, capex: Dict) -> Dict:
    """H2A/NREL production-cost LCOA using Capital Recovery Factor.
    EPI target: ~$786/t (NH3 Parameters sheet break-even value).

    v3.2: Respects FOB / CIF basis.
      • FOB Cartagena: var_om = 0 (offtaker pays ocean shipping). Compares
        directly to H2Global Window 1 benchmark of €811/t FOB Egypt.
      • CIF/delivered: includes freight + insurance ($60/t) for delivered
        Europe pricing. Compares to H2Global €1,000/t delivered.
    The Fichtner export terminal CAPEX/OPEX is always included — it's the
    FOB infrastructure at Puerto Bahía.
    """
    pc = compute_process_chain(p)
    nh3_tpa = pc["nh3_net_tpa"]
    if nh3_tpa <= 0:
        return {}
    n, w = p.project_life_years, p.wacc
    crf  = w * (1 + w) ** n / ((1 + w) ** n - 1)
    capex_ann  = capex["total_capex"] * 1e6 * crf
    energy_ann = pc["annual_grid_cost_musd"] * 1e6
    fixed_om   = p.fixed_opex_annual_musd * 1e6
    # v3.2: Ocean freight + insurance only included in CIF/delivered basis.
    var_om     = nh3_tpa * p.freight_insurance_per_t if p.freight_basis == "CIF" else 0.0
    stack_int  = p.stack_life_hours / (8_760 * p.plant_availability)
    stack_ann  = capex["electrolyser"] * 1e6 * p.stack_replacement_pct * (n / stack_int) / n
    total      = capex_ann + energy_ann + fixed_om + var_om + stack_ann
    return {
        "lcoa_h2a_usd_t":        round(total / nh3_tpa, 2),
        "lcoa_capex_component":  round(capex_ann  / nh3_tpa, 2),
        "lcoa_energy_component": round(energy_ann / nh3_tpa, 2),
        "lcoa_fixed_om":         round(fixed_om   / nh3_tpa, 2),
        "lcoa_var_om":           round(var_om     / nh3_tpa, 2),
        "lcoa_stack":            round(stack_ann  / nh3_tpa, 2),
        "crf":                   round(crf, 5),
        "total_annual_cost_musd":round(total / 1e6, 2),
    }


def compute_production_profile(p: ProjectParams, years: int) -> pd.DataFrame:
    pc             = compute_process_chain(p)
    stack_interval = round(p.stack_life_hours / (8_760 * p.plant_availability))
    rows = []
    for yr in range(years):
        op_year       = yr + 1
        calendar_year = p.cod_year + yr
        ramp = p.ramp_yr1 if op_year == 1 else (p.ramp_yr2 if op_year == 2 else 1.0)
        eff  = 1.0 / (1 + p.electrolyser_degradation) ** yr
        rows.append({
            "op_year":           op_year,
            "calendar_year":     calendar_year,
            "nh3_production_kt": round(pc["nh3_net_ktpa"] * ramp * eff, 2),
            "h2_production_kt":  round(pc["h2_gross_tpa"] / 1_000 * ramp * eff, 2),
            "o2_production_kt":  round(pc["o2_tpa"] / 1_000 * ramp * eff, 2),
            "stack_replacement": (op_year % stack_interval == 0),
            "ramp_factor":       ramp,
            "eff_factor":        round(eff, 4),
        })
    return pd.DataFrame(rows)


def compute_revenue(p: ProjectParams, prod: pd.DataFrame,
                    scenario: str = "base") -> pd.DataFrame:
    """
    v3.3: Single-stream revenue model.

      Revenue = NH3 production (tonnes) × NH3 price (USD/t FOB Cartagena)

    Pricing is in USD throughout. The H2Global Window 1 award price
    ($868/t = €811/t × 1.07) is preserved as a reference benchmark in the
    LCOA display but is NOT used in revenue calculations — Cartagena did not
    win Window 1 and any future HPA win would be modeled as an upside case.

    Reficar/Colombia H2 sales and O2 co-product are disabled in the base case
    (parameter defaults set to zero). These can be enabled as sensitivity
    cases via ProjectParams overrides if needed.

    Price escalates at p.nh3_price_escalation (default 2% nominal/yr),
    floored at p.nh3_price_floor.
    """
    price_map = {"bear": p.nh3_price_bear, "base": p.nh3_price_base, "bull": p.nh3_price_bull}
    base_p   = price_map.get(scenario, p.nh3_price_base)
    rows = []
    for _, row in prod.iterrows():
        yr, nh3_kt = row["op_year"], row["nh3_production_kt"]
        o2_kt, ramp = row["o2_production_kt"], row["ramp_factor"]

        # Single NH3 price (USD/t FOB), escalated 2% nominal/yr
        nh3_price = max(p.nh3_price_floor, base_p * (1 + p.nh3_price_escalation) ** (yr - 1))
        nh3_rev   = nh3_kt * 1_000 * nh3_price / 1e6

        # Disabled streams (kept zero for backward compat with downstream code)
        h2g_rev    = 0.0
        col_rev    = (p.colombia_h2_ktpa * ramp * 1_000 * p.colombia_h2_price_per_kg * 1_000 / 1e6
                       if p.colombia_h2_ktpa > 0 else 0.0)
        o2_rev     = (o2_kt * 1_000 * p.o2_price_per_kg / 1e6) if p.sell_o2 else 0.0
        total      = nh3_rev + h2g_rev + col_rev + o2_rev

        rows.append({
            "op_year":                 yr,
            "nh3_revenue_musd":        round(nh3_rev,   2),  # v3.3: new primary stream
            "h2global_revenue_musd":   round(h2g_rev,   2),  # always 0 in v3.3 base
            "colombia_revenue_musd":   round(col_rev,   2),  # always 0 in v3.3 base
            "spot_revenue_musd":       round(nh3_rev,   2),  # alias for backward compat
            "o2_revenue_musd":         round(o2_rev,    2),
            "total_revenue_musd":      round(total,     2),
            "nh3_price_usd_t":         round(nh3_price, 1),  # v3.3: single price
            "blended_nh3_price_usd_t": round(total*1e6/(nh3_kt*1_000), 1) if nh3_kt > 0 else 0,
            "nh3_spot_price_usd_t":    round(nh3_price, 1),  # alias for backward compat
        })
    return pd.DataFrame(rows)


def compute_opex(p: ProjectParams, prod: pd.DataFrame,
                 capex: Dict) -> pd.DataFrame:
    """
    v3.2: Ocean freight + insurance ($60/t default) only charged under CIF basis.
    Under FOB (default), the offtaker pays ocean shipping, so freight is NOT
    in operating costs. Revenue assumptions (H2Global €811/t FOB Egypt
    benchmark; spot NH3 $900/t reference) are FOB-consistent.

    The Fichtner export terminal CAPEX (~$48M) and peripheral OPEX (~$2.21M/yr,
    embedded within fixed_opex_annual_musd) are always included — those are
    FOB infrastructure costs at Puerto Bahía, not ocean shipping.
    """
    pc = compute_process_chain(p)
    base_nh3 = pc["nh3_net_tpa"]
    rows = []
    for _, row in prod.iterrows():
        yr     = row["op_year"]
        esc    = (1 + p.om_escalation_pct)     ** (yr - 1)
        g_esc  = (1 + p.grid_price_escalation) ** (yr - 1)
        nh3_kt = row["nh3_production_kt"]
        frac   = (nh3_kt * 1_000) / base_nh3 if base_nh3 > 0 else 1.0
        energy  = pc["annual_grid_cost_musd"] * frac * g_esc
        solar_om= p.solar_mwac * p.solar_opex_per_mwac / 1e6 * esc
        fixed_om= p.fixed_opex_annual_musd * esc
        # v3.2: Freight included ONLY in CIF basis (offtaker pays under FOB)
        if p.freight_basis == "CIF":
            var_om = nh3_kt * 1_000 * p.freight_insurance_per_t / 1e6 * esc
        else:
            var_om = 0.0
        stack   = capex["electrolyser"] * p.stack_replacement_pct if row["stack_replacement"] else 0.0
        total   = energy + solar_om + fixed_om + var_om
        rows.append({
            "op_year":                yr,
            "energy_opex_musd":       round(energy,   2),
            "solar_om_musd":          round(solar_om, 2),
            "om_opex_musd":           round(fixed_om, 2),
            "var_om_musd":            round(var_om,   2),
            "peripheral_opex_musd":   round(fixed_om * 0.16, 2),
            "total_opex_musd":        round(total,    2),
            "stack_replacement_musd": round(stack,    2),
            "total_cash_costs_musd":  round(total + stack, 2),
            "core_opex_musd":         round(energy,   2),
        })
    return pd.DataFrame(rows)


def compute_dcf(p: ProjectParams, prod: pd.DataFrame, rev: pd.DataFrame,
                opex_df: pd.DataFrame, capex: Dict) -> Tuple[pd.DataFrame, Dict]:
    """
    v3.2 corrections vs v3.1:
      • Bug 1: Project NPV correctly subtracts total CAPEX (not equity).
      • Bug 2: Income tax rate restored from 0% to 30% (FNCER) default.
      • Bug 3: Replaced U.S. MACRS depreciation with Colombian 5-yr straight-line
               (Ley 1715/2099 accelerated depreciation for FNCER assets).
      • Bug 4: Added NOL carryforward tracking (Estatuto Tributario Art. 147,
               12-year window).
      • Bug 5: Project FCF now uses UNLEVERED tax (no interest deduction);
               Equity FCF uses LEVERED tax (with interest deduction).
               Previously, both used levered tax which gave Project FCF the
               benefit of the debt tax shield it shouldn't earn.
      • Ley 1715 deduction capped at 50% of taxable income per Colombian rules.
    """
    total_capex = capex["total_capex"]
    gross_capex = capex["gross_total"]
    debt    = total_capex * p.debt_share
    equity  = total_capex * (1 - p.debt_share)
    r, n    = p.debt_interest_rate, p.debt_tenor_years
    annual_ds = debt * (r * (1+r)**n) / ((1+r)**n - 1)

    # Colombian Ley 1715: 50% of GROSS capex deductible, over 15 yrs.
    # Cap: each year's deduction cannot exceed 50% of taxable income (after dep,
    # before this deduction). Capped portion does NOT carry forward.
    annual_dedn_uncapped = gross_capex * p.income_tax_deduction_pct / p.income_tax_deduction_years

    # Colombian accelerated depreciation for FNCER (Decreto 829): up to 33.33%/yr.
    # We use 5-year straight-line as the base case (more conservative). The
    # Colombian Tax Code (Estatuto Tributario Art. 137) allows accelerated
    # depreciation for renewable assets via FNCER certification.
    dep_schedule = [0.20, 0.20, 0.20, 0.20, 0.20]  # 5-yr straight-line

    debt_out = debt
    nol_balance = []  # list of (year_incurred, remaining_amount) tuples
    rows = []

    for _, prow in prod.iterrows():
        yr      = int(prow["op_year"])
        revenue = rev[rev.op_year == yr].iloc[0].total_revenue_musd
        opex    = opex_df[opex_df.op_year == yr].iloc[0].total_cash_costs_musd

        # Debt service
        interest= debt_out * r if yr <= n else 0.0
        prin    = min(debt_out, annual_ds - interest) if yr <= n else 0.0
        debt_out= max(0.0, debt_out - prin)

        # Depreciation: Colombian 5-yr straight-line on total_capex
        dep = total_capex * dep_schedule[yr-1] if yr <= len(dep_schedule) else 0.0

        # Ley 1715 deduction is active for first 15 yrs but capped at 50% of taxable
        col_dedn_uncapped = annual_dedn_uncapped if yr <= p.income_tax_deduction_years else 0.0

        ebitda = revenue - opex

        # -----------------------------------------------------------------------
        # UNLEVERED tax (for Project FCF): no interest deduction
        # -----------------------------------------------------------------------
        unlev_pre_1715 = revenue - opex - dep
        col_dedn_unlev = min(col_dedn_uncapped, max(0, unlev_pre_1715 * p.income_tax_deduction_max_pct_of_taxable))
        unlev_taxable_before_nol = unlev_pre_1715 - col_dedn_unlev
        # Apply NOL carryforward (unlevered side uses its own NOL tracking — simplified
        # by using a shared NOL pool, consistent with how a tax authority would
        # actually look at the firm; we keep a single combined pool for both views)
        # We compute NOL adjustment AFTER levered side to keep the pool shared.

        # -----------------------------------------------------------------------
        # LEVERED tax (for Equity FCF): includes interest deduction
        # -----------------------------------------------------------------------
        lev_pre_1715  = revenue - opex - interest - dep
        col_dedn_lev = min(col_dedn_uncapped, max(0, lev_pre_1715 * p.income_tax_deduction_max_pct_of_taxable))
        lev_taxable_before_nol = lev_pre_1715 - col_dedn_lev

        # Apply NOL carryforward (Colombia: 12-year window, FIFO consumption)
        # Use a single pool tracking levered position (since that's how the firm
        # actually files). Project FCF uses an approximation: tax_unlev =
        # tax_lev + interest*tax_rate (i.e., add back the interest tax shield).
        # This is the canonical project-vs-equity tax shield decomposition.
        nol_used = 0.0
        if lev_taxable_before_nol > 0 and nol_balance:
            remaining_to_offset = lev_taxable_before_nol
            new_nol = []
            for (yr_inc, amt) in nol_balance:
                if remaining_to_offset <= 0 or (yr - yr_inc) > p.nol_carryforward_years:
                    if (yr - yr_inc) <= p.nol_carryforward_years:
                        new_nol.append((yr_inc, amt))
                    continue
                use = min(amt, remaining_to_offset)
                nol_used += use
                remaining_to_offset -= use
                if amt - use > 0:
                    new_nol.append((yr_inc, amt - use))
            nol_balance = new_nol

        lev_taxable_after_nol = lev_taxable_before_nol - nol_used

        if lev_taxable_after_nol < 0:
            # Generate new NOL
            nol_balance.append((yr, -lev_taxable_after_nol))
            tax_levered = 0.0
        else:
            tax_levered = lev_taxable_after_nol * p.income_tax_rate

        # Unlevered tax = levered tax + interest tax shield (add back what equity got)
        tax_unlevered = tax_levered + interest * p.income_tax_rate
        # Ensure unlevered tax is not negative
        tax_unlevered = max(0.0, tax_unlevered)

        # Cash flows
        pf = ebitda - tax_unlevered                                      # Project FCF (unlevered)
        ef = ebitda - tax_levered - (annual_ds if yr <= n else 0.0)      # Equity FCF (levered)

        rows.append({
            "op_year":               yr,
            "calendar_year":         prow.calendar_year,
            "revenue_musd":          round(revenue, 2),
            "opex_musd":             round(opex,    2),
            "ebitda_musd":           round(ebitda,  2),
            "ebitda_margin_pct":     round(ebitda/revenue*100, 1) if revenue > 0 else 0,
            "depreciation_musd":     round(dep,        2),
            "ley_1715_deduction_musd": round(col_dedn_lev, 2),
            "nol_used_musd":         round(nol_used,  2),
            "nol_balance_musd":      round(sum(a for _,a in nol_balance), 2),
            "interest_musd":         round(interest,2),
            "tax_levered_musd":      round(tax_levered,   2),
            "tax_unlevered_musd":    round(tax_unlevered, 2),
            "tax_musd":              round(tax_levered,   2),  # legacy alias = levered (equity view)
            "project_fcf_musd":      round(pf,      2),
            "equity_fcf_musd":       round(ef,      2),
            "project_pv_musd":       round(pf/(1+p.wacc)**yr, 2),
            "debt_outstanding_musd": round(debt_out,2),
            "nh3_production_kt":     prow.nh3_production_kt,
            "dscr":                  round(ebitda/annual_ds, 2) if yr<=n and annual_ds>0 else None,
            "stack_replacement_musd": opex_df[opex_df.op_year == yr].iloc[0].get("stack_replacement_musd", 0.0),
        })
    df       = pd.DataFrame(rows)
    # BUG FIX v3.2 #1: Project NPV must subtract total CAPEX, not equity.
    # Project FCF represents the project's unlevered cash flows; the comparison
    # base is the total investment (debt + equity), not just equity. Project
    # NPV is discounted at WACC (the project's blended cost of capital).
    proj_npv = df.project_pv_musd.sum() - total_capex
    # v3.3 FIX: Equity NPV must be discounted at COST OF EQUITY (Ke), not WACC.
    # WACC is the blended (debt + equity) cost — using it for equity FCF would
    # understate the cost of equity capital and overstate Equity NPV.
    # Standard corporate finance: unlevered FCF @ WACC, levered FCF @ Ke.
    df["equity_pv_musd"] = df.equity_fcf_musd / (1+p.cost_of_equity)**df.op_year
    equity_npv = df["equity_pv_musd"].sum() - equity
    disc_nh3 = (df.nh3_production_kt*1_000 / (1+p.wacc)**df.op_year).sum()
    # BUG FIX v3.2 #5: include stack replacement in investor LCOA cash costs.
    disc_cost= (df.opex_musd / (1+p.wacc)**df.op_year).sum() + total_capex
    disc_stack = (df.get("stack_replacement_musd", pd.Series([0]*len(df))) / (1+p.wacc)**df.op_year).sum() if "stack_replacement_musd" in df.columns else 0.0
    lcoa_inv = (disc_cost + disc_stack) / disc_nh3 * 1e6 if disc_nh3 > 0 else 0
    # EPI production-cost LCOA (CRF method — matches their $786/t baseline)
    _crf     = p.wacc * (1+p.wacc)**p.project_life_years / ((1+p.wacc)**p.project_life_years - 1)
    lcoa_epi = (total_capex * _crf * 1e6 + df.opex_musd.mean() * 1e6) / \
               (df.nh3_production_kt.mean() * 1_000) if df.nh3_production_kt.mean() > 0 else 0
    proj_irr = _irr([-total_capex] + df.project_fcf_musd.tolist())
    eq_irr   = _irr([-equity]      + df.equity_fcf_musd.tolist())
    min_dscr = df[df.dscr.notna()].dscr.min() if df.dscr.notna().any() else None

    # ─── LCOA — THREE-TIER FRAMEWORK (v3.2 final) ────────────────────────────
    # Three distinct delivery points produce three distinct LCOAs. Each is
    # directly comparable to a specific industry benchmark.
    #
    #   Ex-works:      Core plant only, no Fichtner peripheral, no freight.
    #                  Comparable to Arup $812/t, Chile/Brazil feasibility ranges.
    #   FOB Cartagena: Core + Fichtner export terminal at Puerto Bahía,
    #                  no ocean freight. Comparable to Yara/ACME Oman,
    #                  H2Global Window 1 FOB Egypt $868/t.
    #   CIF Europe:    Everything above + $60/t ocean freight + insurance.
    #                  Comparable to H2Global Window 1 delivered Rotterdam $1,070/t.
    #
    # All three use the same H2A/CRF methodology; they differ only in scope.
    lcoa_ex_works     = _compute_lcoa_tier(p, capex, include_peripheral=False, include_freight=False)
    lcoa_fob          = _compute_lcoa_tier(p, capex, include_peripheral=True,  include_freight=False)
    lcoa_cif          = _compute_lcoa_tier(p, capex, include_peripheral=True,  include_freight=True)

    metrics  = {
        "total_capex_musd":         round(total_capex, 1),
        "gross_capex_musd":         round(capex.get("gross_total", total_capex), 1),
        "core_capex_musd":          round(capex["core_total"],       1),
        "peripheral_capex_musd":    round(capex["peripheral_total"], 1),
        "vat_saving_musd":          round(capex.get("vat_saving", 0), 1),
        "tariff_saving_musd":       round(capex.get("tariff_saving", 0), 1),
        "debt_musd":                round(debt,   1),
        "equity_musd":              round(equity, 1),
        "project_npv_musd":         round(proj_npv, 1),
        "equity_npv_musd":          round(equity_npv, 1),
        "project_irr_pct":          round(proj_irr*100, 1) if proj_irr else None,
        "equity_irr_pct":           round(eq_irr  *100, 1) if eq_irr   else None,
        "wacc_pct":                 round(p.wacc * 100, 2),
        "cost_of_equity_pct":       round(p.cost_of_equity * 100, 2),

        # ─── LCOA — THREE TIERS (canonical v3.2 outputs) ───────────────────
        "lcoa_ex_works_usd_t":      round(lcoa_ex_works, 1),
        "lcoa_fob_usd_t":           round(lcoa_fob, 1),
        "lcoa_cif_usd_t":           round(lcoa_cif, 1),
        # Increments between tiers, for the dashboard:
        "lcoa_fichtner_delta_usd_t": round(lcoa_fob - lcoa_ex_works, 1),
        "lcoa_freight_delta_usd_t":  round(lcoa_cif - lcoa_fob, 1),
        # Default headline = FOB Cartagena (bankable scope, standard offtake basis):
        "headline_lcoa_usd_t":      round(lcoa_fob, 1),

        # ─── Legacy / alternative method results (kept for analyst view) ───
        "lcoa_h2a_usd_t":           round((compute_lcoa_h2a(p, capex) or {}).get("lcoa_h2a_usd_t", 0), 1),
        "lcoa_dcf_usd_t":           round(lcoa_inv, 1),
        "lcoa_epi_usd_t":           round(lcoa_epi, 1),
        # Legacy aliases for v3.1 backward compatibility:
        "lcoa_plant_gate_usd_t":      round(lcoa_ex_works, 1),  # = ex-works (renamed)
        "lcoa_project_complete_usd_t": round(lcoa_fob, 1),       # = FOB Cartagena (renamed)
        "lcoa_peripheral_component_usd_t": round(lcoa_fob - lcoa_ex_works, 1),
        "lcoa_usd_t":               round(lcoa_inv, 1),
        "epi_lcoa_usd_t":           round(lcoa_epi, 1),

        "avg_annual_revenue_musd":  round(df.revenue_musd.mean(), 1),
        "avg_ebitda_margin_pct":    round(df.ebitda_margin_pct.mean(), 1),
        "lifetime_tax_musd":        round(df.tax_levered_musd.sum(), 1),
        "payback_years":            _payback(equity, df.equity_fcf_musd.tolist()),
        "min_dscr":                 round(min_dscr, 2) if min_dscr else None,
    }
    return df, metrics


def _compute_lcoa_tier(p: ProjectParams, capex: Dict,
                        include_peripheral: bool, include_freight: bool) -> float:
    """
    Generic H2A/CRF LCOA computed for a specified scope tier.

    Args:
        p: ProjectParams
        capex: CAPEX dict from compute_capex()
        include_peripheral: If True, includes Fichtner peripheral CAPEX
                             (export terminal, OHTL, water, KOH, WWTP).
                             If False, core plant only (ex-works).
        include_freight: If True, includes $60/t ocean freight + insurance
                          in variable OPEX (CIF Europe delivery).
                          If False, omitted (ex-works or FOB).

    Returns:
        LCOA in USD per tonne NH3.
    """
    pc = compute_process_chain(p)
    nh3_tpa = pc["nh3_net_tpa"]
    if nh3_tpa <= 0:
        return 0.0

    # Construct the relevant CAPEX scope
    if include_peripheral:
        net_capex = capex["total_capex"]  # already includes peripheral + incentives
    else:
        # Strip peripheral: reconstruct CAPEX with peripheral_total = 0
        core   = capex["core_total"]
        owners = core * 0.05  # owner's costs reapplied at 5% of core only
        gross_no_periph = core + owners
        # Scale incentives proportionally
        if capex["gross_total"] > 0:
            incentive_ratio = (capex["vat_saving"] + capex["tariff_saving"]) / capex["gross_total"]
        else:
            incentive_ratio = 0.0
        net_capex = gross_no_periph * (1 - incentive_ratio)

    n, w = p.project_life_years, p.wacc
    crf  = w * (1 + w) ** n / ((1 + w) ** n - 1)
    capex_ann  = net_capex * 1e6 * crf
    energy_ann = pc["annual_grid_cost_musd"] * 1e6
    fixed_om   = p.fixed_opex_annual_musd * 1e6
    # Variable OPEX: ocean freight + insurance, only for CIF tier
    var_om     = nh3_tpa * p.freight_insurance_per_t if include_freight else 0.0
    stack_int  = p.stack_life_hours / (8_760 * p.plant_availability)
    stack_ann  = capex["electrolyser"] * 1e6 * p.stack_replacement_pct * (n / stack_int) / n
    total      = capex_ann + energy_ann + fixed_om + var_om + stack_ann
    return total / nh3_tpa


def compute_lcoa_breakdown(p: ProjectParams, capex: Dict, prod: pd.DataFrame) -> Dict:
    pc   = compute_process_chain(p)
    disc = (prod.nh3_production_kt*1_000 / (1+p.wacc)**prod.op_year).sum()
    if disc == 0: return {}
    ann    = lambda m: m / disc * 1e6
    yrs    = p.project_life_years
    pv_sum = sum(1 / (1+p.wacc)**yr for yr in range(1, yrs+1))
    return {
        "Solar CAPEX":        ann(capex["solar_plant"]),
        "Electrolyser CAPEX": ann(capex["electrolyser"]),
        "Haber-Bosch CAPEX":  ann(capex["haber_bosch"]),
        "ASU CAPEX":          ann(capex["asu"]),
        "H2 storage CAPEX":   ann(capex["h2_storage"]),
        "NH3 storage CAPEX":  ann(capex.get("nh3_storage", 0)),
        "Pipeline CAPEX":     ann(capex["pipeline"]),
        "Peripheral CAPEX":   ann(capex["peripheral_total"]),
        "Grid energy OPEX":   pc["annual_grid_cost_musd"] * pv_sum / disc * 1e6,
        "Solar O&M OPEX":     p.solar_mwac * p.solar_opex_per_mwac / 1e6 * pv_sum / disc * 1e6,
        "Fixed O&M OPEX":     p.fixed_opex_annual_musd * pv_sum / disc * 1e6,
        "VarOpEx (freight)":  p.freight_insurance_per_t * pv_sum / disc * 1e6 * 1e-3,
    }


def sensitivity_analysis(p: ProjectParams, variables: Dict) -> pd.DataFrame:
    base_c  = compute_capex(p)
    base_pr = compute_production_profile(p, p.project_life_years)
    _, bm   = compute_dcf(p, base_pr, compute_revenue(p, base_pr, "base"),
                          compute_opex(p, base_pr, base_c), base_c)
    b_lcoa, b_irr = bm["lcoa_usd_t"], bm["project_irr_pct"] or 0
    rows = []
    for var, (lo, hi) in variables.items():
        for case, val in [("Low", lo), ("High", hi)]:
            kw = {k: v for k, v in p.__dict__.items()}
            kw[var] = val
            try:
                pt = ProjectParams(**kw)
                c  = compute_capex(pt)
                pr = compute_production_profile(pt, pt.project_life_years)
                rv = compute_revenue(pt, pr, "base")
                op = compute_opex(pt, pr, c)
                _, m = compute_dcf(pt, pr, rv, op, c)
                rows.append({"variable": var, "case": case, "value": val,
                              "lcoa_usd_t": m["lcoa_usd_t"], "lcoa_delta": m["lcoa_usd_t"]-b_lcoa,
                              "irr_pct": m["project_irr_pct"],
                              "irr_delta": (m["project_irr_pct"] or 0) - b_irr})
            except Exception:
                pass
    return pd.DataFrame(rows)


def _irr(cashflows, guess=0.10):
    cf = np.array(cashflows, dtype=float)
    rate = guess
    for _ in range(500):
        t    = np.arange(len(cf), dtype=float)
        safe = np.where(np.abs(1+rate)<1e-12, 1e-12, (1+rate)**t)
        npv  = np.sum(cf/safe)
        dnpv = -np.sum(t*cf/(safe*(1+rate)))
        if abs(dnpv)<1e-12: break
        rate -= npv/dnpv
        if not np.isfinite(rate) or rate<=-0.999: return None
    return rate if np.isfinite(npv) and abs(npv)<1.0 else None


def _payback(equity, fcfs):
    cum = 0.0
    for i, cf in enumerate(fcfs):
        cum += cf
        if cum >= equity: return i+1
    return None


DEFAULT_SENSITIVITY = {
    "solar_capacity_factor":      [0.20,    0.28],
    "electrolyser_sec":           [45.0,    55.0],
    "solar_capex_per_mwac":       [600_000, 1_000_000],
    "electrolyser_capex_all_in_mw": [500_000, 750_000],
    "nh3_price_base":             [700.0,   1_100.0],
    "plant_availability":         [0.90,    0.98],
    "debt_interest_rate":         [0.025,   0.060],
    "wacc":                       [0.060,   0.100],
}


# =============================================================================
# v3.2 — SCENARIO PARAMETER PACKS
# =============================================================================
# Three named scenarios. Each is a dict of parameter overrides applied to
# ProjectParams defaults. Fichtner peripheral CAPEX is INCLUDED in all three
# scenarios for scope completeness.
#
# Usage:
#   from model_engine_v32 import ProjectParams, SCENARIOS
#   p = ProjectParams(**SCENARIOS["feasibility"])
# =============================================================================

SCENARIOS = {
    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO A — FEASIBILITY (Arup + Fichtner)
    # Source: Arup Resumen Ejecutivo Nov 2025, Tabla 6 + Fichtner Jan 2025
    # This is the "as documented in the feasibility study" view.
    # ─────────────────────────────────────────────────────────────────────────
    "feasibility": {
        # Plant configuration (Arup-optimized)
        "solar_mwac":                   250.0,    # ~300 MWp DC at 1.2 DC:AC
        "electrolyser_mw":              195.0,    # Arup recommended optimum

        # Solar — Arup Tabla 6
        "solar_capex_per_mwac":         700_000,  # Arup Tabla 6
        "solar_opex_per_mwac":          13_000,   # Arup Tabla 6

        # Electrolyser — Arup ($350k stack + $108.5k auxiliaries = $458.5k all-in)
        "electrolyser_capex_all_in_mw": 458_500,  # Arup Tabla 6 (stack + aux)
        "electrolyser_sec":             50.0,     # Arup implicit
        "stack_replacement_pct":        0.15,     # Arup: 15% of initial CAPEX
        "stack_life_hours":             90_000,   # Arup Tabla 6

        # Haber-Bosch — Arup (notably lower than EPI legacy: $62k vs $137.5k per tpd)
        "hb_capex_per_kgd":             62.0,     # Arup Tabla 6
        "asu_capex_per_kgd_n2":         63.264,   # Arup Tabla 6

        # Pipeline — Fichtner correction (14.1 km vs original 10 km)
        "pipeline_km":                  14.1,     # Fichtner Jan 2025

        # HB BoP — Arup embeds in line items, no separate contingency
        "hb_bop_pct":                   0.15,     # conservative reduction

        # Energy — Feasibility default: Arup-published industrial tariff ($78/MWh).
        # This preserves the audit chain — Arup did NOT model a hydro PPA in the
        # Resumen Ejecutivo, so the headline LCOA must use $78/MWh to reconcile
        # to the published $812/t ex-works benchmark.
        # Hydro PPA ($55/MWh) is available as an optional toggle in the sidebar
        # for sensitivity / upside view, but it is NOT the Feasibility default.
        "grid_price_day_kwh":           0.078,
        "grid_price_night_kwh":         0.078,
        "grid_price_hb_kwh":            0.078,

        # Fixed OPEX — preserves Arup/EPI default
        "fixed_opex_annual_musd":       13.72,

        # Project life — Arup uses 30 yrs but we keep 25 for comparability
        "project_life_years":           25,

        # Financing & tax — consistent across scenarios for apples-to-apples
        "income_tax_rate":              0.30,
        "debt_tenor_years":             15,
    },

    # ─────────────────────────────────────────────────────────────────────────
    # SCENARIO B — EPI OPTIMIZED (Electryon's view of 2026 procurement reality)
    # ─────────────────────────────────────────────────────────────────────────
    # CAPEX reflects current commercial pricing as of Q1 2026:
    #   • Chinese AWE electrolyser (Longi, Sungrow): $400k/MW vs Arup $458.5k
    #   • LATAM utility-scale solar EPC: $620k/MWac vs $700k
    #   • Casale 2026 HB indicative pricing: $80k/tpd vs Arup $62k (actually higher,
    #     but Arup's $62k is implausibly low — $80k aligned with current Casale quotes)
    #   • Optimized SEC of 47 kWh/kg (current 2026 commercial best)
    #
    # OPEX scales with CAPEX reduction (Option B per reconciliation):
    # lower-CAPEX equipment has lower scheduled maintenance, spare parts, insurance.
    # Solar O&M reduced to $11k/MW (LATAM 2026 benchmark).
    # Fixed OPEX scaled proportionally based on observed CAPEX delta.
    #
    # Fichtner peripheral CAPEX kept as published — Tier-1 engineering firm,
    # IDB-commissioned, peer-reviewed. Any peripheral optimization is FID upside.
    # ─────────────────────────────────────────────────────────────────────────
    "epi_optimized": {
        # Plant configuration
        "solar_mwac":                   250.0,
        "electrolyser_mw":              195.0,    # Arup-optimal sizing

        # Solar — 2026 LATAM utility-scale benchmark
        "solar_capex_per_mwac":         620_000,  # IRENA 2025; Colombian UPME 2024 clearings
        "solar_opex_per_mwac":          11_000,   # 2026 LATAM benchmark

        # Electrolyser — Chinese AWE (Longi Hi1 Plus, Sungrow)
        "electrolyser_capex_all_in_mw": 400_000,  # Sungrow EPC Q1 2026; Sinopec Kuqa
        "electrolyser_sec":             46.0,     # AC+BoP wall-plug, 2028 procurement frontier:
                                                  # Longi Hi1 Plus stack 45.6 kWh/kg (4.1 kWh/Nm³) + minimal BoP.
                                                  # COD 2030 implies orders placed 2028 — Longi 15 MW units
                                                  # standard by then with lower BoP losses than 2026 5 MW kit.
                                                  # 45 kWh/kg achievable but requires 2500 A/m² operating point —
                                                  # left as post-FEED upside not baked into base case.
        "stack_replacement_pct":        0.15,
        "stack_life_hours":             90_000,

        # Haber-Bosch — match Arup feasibility (audit-validated reference)
        # Principle: EPI Optimized only diverges from Arup on procurement levers
        # where we have direct supplier basis (Chinese AWE pricing, LATAM solar EPC,
        # hydro PPA). HB pricing has no EPI-specific supplier basis, so we adopt
        # Arup's $62/kgday number — audit-defensible, and 2028 Casale pricing is
        # if anything more likely to come down than up.
        "hb_capex_per_kgd":             62.0,     # Arup Tabla 6
        "asu_capex_per_kgd_n2":         60.0,     # market pricing (~5% below Arup)

        # Pipeline — Fichtner-corrected 14.1 km
        "pipeline_km":                  14.1,

        # HB BoP — match Arup (15%). Same principle as above: no EPI-specific
        # basis to be more conservative than the audit-validated reference.
        "hb_bop_pct":                   0.15,

        # Energy — long-term hydro PPA (default; toggle to industrial via sidebar)
        "grid_price_day_kwh":           0.055,
        "grid_price_night_kwh":         0.055,
        "grid_price_hb_kwh":            0.055,

        # Fixed OPEX — scaled with CAPEX reduction (Option B)
        # Arup gross core CAPEX ~$382M; EPI Optimized gross core ~$337M (-12%)
        # Apply same 12% reduction to fixed OPEX: $13.72M × 0.88 = $12.07M/yr
        "fixed_opex_annual_musd":       12.07,

        "project_life_years":           25,
        "income_tax_rate":              0.30,
        "debt_tenor_years":             15,
    },
}

# Human-readable labels for the UI
SCENARIO_LABELS = {
    "feasibility":   "Feasibility (Arup + Fichtner)",
    "epi_optimized": "EPI Optimized (2026 procurement)",
}

SCENARIO_DESCRIPTIONS = {
    "feasibility": (
        "Per Arup Resumen Ejecutivo Nov 2025, Tabla 6. Peripheral infrastructure "
        "from Fichtner Jan 2025. The IDB-commissioned feasibility study — preserved "
        "as the audit-validated reference. Electrolyser at Arup's $458.5k/MW; "
        "HB at $62k/tpd; SEC 50 kWh/kg."
    ),
    "epi_optimized": (
        "Electryon's view of what 2026 procurement actually delivers. "
        "Chinese AWE electrolyser ($400k/MW — Longi, Sungrow EPC); LATAM solar at "
        "$620k/MWac (IRENA 2025 benchmark); Casale 2026 HB pricing ($80k/tpd); "
        "SEC 47 kWh/kg (2026 commercial best). Fixed OPEX scaled with CAPEX. "
        "Fichtner peripheral preserved as published (Tier-1 engineering reference)."
    ),
}

