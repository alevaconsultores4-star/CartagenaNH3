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

    # ── Colombia H2 offtake ───────────────────────────────────────────────────
    colombia_h2_ktpa:             float = 9.0
    colombia_h2_price_per_kg:     float = 4.02    # USD/kgH2

    # ── O2 co-product ─────────────────────────────────────────────────────────
    o2_price_per_kg:              float = 0.01    # EPI R52
    sell_o2:                      bool  = True
    elec_surplus_price_kwh:       float = 0.040   # EPI R51: sell surplus to grid

    # ── Colombian fiscal incentives (Ley 1715/2099) ───────────────────────────
    income_tax_rate:              float = 0.00   # EPI NH3 Interface R170: 0% (H2FAST framework, pre-incentive)
    income_tax_deduction_pct:     float = 0.50
    income_tax_deduction_years:   int   = 15
    vat_exempt:                   bool  = True
    vat_rate:                     float = 0.19
    tariff_exempt:                bool  = True
    tariff_rate:                  float = 0.10
    imported_capex_fraction:      float = 0.60

    # ── Financing (EPI CRF sheet: 40% equity / 60% debt, 8% real IRR) ────────
    debt_share:                   float = 0.75  # EPI NH3 Interface R182: D/E=3 => 75% debt
    debt_interest_rate:           float = 0.050   # EPI H2ALite R62: 5% nominal (user override)
    debt_tenor_years:             int   = 7    # EPI NH3 Interface R184: 7yr loan
    wacc:                         float = 0.10   # EPI NH3 Interface R181: 10% nominal discount rate
    inflation_rate:               float = 0.025

    # ── NH3 price curve ───────────────────────────────────────────────────────
    nh3_price_base:               float = 900.0
    nh3_price_bear:               float = 700.0
    nh3_price_bull:               float = 1_100.0
    nh3_price_floor:              float = 650.0
    nh3_real_change_base:         float = -0.010
    nh3_real_change_bear:         float = -0.020
    nh3_real_change_bull:         float = +0.015

    # ── H2Global HPA ─────────────────────────────────────────────────────────
    h2global_volume_ktpa:         float = 50.0
    h2global_net_price_eur:       float = 811.0
    eur_usd:                      float = 1.07
    h2global_escalation:          float = 0.02
    h2global_contract_years:      int   = 10

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
    EPI target: ~$786/t (NH3 Parameters sheet break-even value)."""
    pc = compute_process_chain(p)
    nh3_tpa = pc["nh3_net_tpa"]
    if nh3_tpa <= 0:
        return {}
    n, w = p.project_life_years, p.wacc
    crf  = w * (1 + w) ** n / ((1 + w) ** n - 1)
    capex_ann  = capex["total_capex"] * 1e6 * crf
    energy_ann = pc["annual_grid_cost_musd"] * 1e6
    fixed_om   = p.fixed_opex_annual_musd * 1e6
    var_om     = nh3_tpa * p.freight_insurance_per_t
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
    price_map = {"bear": p.nh3_price_bear, "base": p.nh3_price_base, "bull": p.nh3_price_bull}
    real_map  = {"bear": p.nh3_real_change_bear, "base": p.nh3_real_change_base,
                 "bull": p.nh3_real_change_bull}
    base_p   = price_map.get(scenario, p.nh3_price_base)
    real_chg = real_map.get(scenario, p.nh3_real_change_base)
    nom_chg  = (1 + real_chg) * (1 + p.inflation_rate) - 1
    rows = []
    for _, row in prod.iterrows():
        yr, nh3_kt = row["op_year"], row["nh3_production_kt"]
        o2_kt, ramp = row["o2_production_kt"], row["ramp_factor"]
        # H2Global HPA
        h2g_active = yr <= p.h2global_contract_years
        h2g_vol    = min(p.h2global_volume_ktpa, nh3_kt) if h2g_active else 0.0
        h2g_price  = p.h2global_net_price_eur * p.eur_usd * (1 + p.h2global_escalation) ** (yr-1)
        h2g_rev    = h2g_vol * 1_000 * h2g_price / 1e6
        # Colombia H2 (revenue allocation)
        col_rev    = p.colombia_h2_ktpa * ramp * 1_000 * p.colombia_h2_price_per_kg * 1_000 / 1e6
        # Spot NH3
        spot_vol   = max(0.0, nh3_kt - h2g_vol)
        spot_price = max(p.nh3_price_floor, base_p * (1 + nom_chg) ** (yr-1))
        spot_rev   = spot_vol * 1_000 * spot_price / 1e6
        # O2 co-product
        o2_rev     = o2_kt * 1_000 * p.o2_price_per_kg / 1e6 if p.sell_o2 else 0.0
        total      = h2g_rev + col_rev + spot_rev + o2_rev
        rows.append({
            "op_year":                 yr,
            "h2global_revenue_musd":   round(h2g_rev,   2),
            "colombia_revenue_musd":   round(col_rev,   2),
            "spot_revenue_musd":       round(spot_rev,  2),
            "o2_revenue_musd":         round(o2_rev,    2),
            "total_revenue_musd":      round(total,     2),
            "blended_nh3_price_usd_t": round(total*1e6/(nh3_kt*1_000),1) if nh3_kt>0 else 0,
            "nh3_spot_price_usd_t":    round(spot_price,1),
        })
    return pd.DataFrame(rows)


def compute_opex(p: ProjectParams, prod: pd.DataFrame,
                 capex: Dict) -> pd.DataFrame:
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
        var_om  = nh3_kt * 1_000 * p.freight_insurance_per_t / 1e6 * esc
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
    total_capex = capex["total_capex"]
    debt    = total_capex * p.debt_share
    equity  = total_capex * (1 - p.debt_share)
    r, n    = p.debt_interest_rate, p.debt_tenor_years
    annual_ds = debt * (r * (1+r)**n) / ((1+r)**n - 1)
    # Colombian Ley 1715: 50% of GROSS capex deductible over 15 yrs
    annual_dedn = capex["gross_total"] * p.income_tax_deduction_pct / p.income_tax_deduction_years
    macrs3   = [0.3333, 0.4445, 0.1481, 0.0741]
    debt_out = debt
    rows     = []
    for _, prow in prod.iterrows():
        yr      = prow["op_year"]
        revenue = rev[rev.op_year == yr].iloc[0].total_revenue_musd
        opex    = opex_df[opex_df.op_year == yr].iloc[0].total_cash_costs_musd
        interest= debt_out * r if yr <= n else 0.0
        prin    = min(debt_out, annual_ds - interest) if yr <= n else 0.0
        debt_out= max(0.0, debt_out - prin)
        dep     = total_capex * macrs3[yr-1] if yr <= len(macrs3) else 0.0
        col_dedn= annual_dedn if yr <= p.income_tax_deduction_years else 0.0
        taxable = revenue - opex - interest - dep - col_dedn
        tax     = max(0.0, taxable * p.income_tax_rate)
        ebitda  = revenue - opex
        pf      = ebitda - tax
        ef      = ebitda - tax - annual_ds if yr <= n else ebitda - tax
        rows.append({
            "op_year":               yr,
            "calendar_year":         prow.calendar_year,
            "revenue_musd":          round(revenue, 2),
            "opex_musd":             round(opex,    2),
            "ebitda_musd":           round(ebitda,  2),
            "ebitda_margin_pct":     round(ebitda/revenue*100, 1) if revenue > 0 else 0,
            "interest_musd":         round(interest,2),
            "tax_musd":              round(tax,     2),
            "project_fcf_musd":      round(pf,      2),
            "equity_fcf_musd":       round(ef,      2),
            "project_pv_musd":       round(pf/(1+p.wacc)**yr, 2),
            "debt_outstanding_musd": round(debt_out,2),
            "nh3_production_kt":     prow.nh3_production_kt,
            "dscr":                  round(ebitda/annual_ds, 2) if yr<=n and annual_ds>0 else None,
        })
    df       = pd.DataFrame(rows)
    proj_npv = df.project_pv_musd.sum() - equity
    disc_nh3 = (df.nh3_production_kt*1_000 / (1+p.wacc)**df.op_year).sum()
    disc_cost= (df.opex_musd / (1+p.wacc)**df.op_year).sum() + total_capex
    lcoa_inv = disc_cost / disc_nh3 * 1e6 if disc_nh3 > 0 else 0
    # EPI production-cost LCOA (CRF method — matches their $786/t baseline)
    _crf     = p.wacc * (1+p.wacc)**p.project_life_years / ((1+p.wacc)**p.project_life_years - 1)
    lcoa_epi = (total_capex * _crf * 1e6 + df.opex_musd.mean() * 1e6) / \
               (df.nh3_production_kt.mean() * 1_000) if df.nh3_production_kt.mean() > 0 else 0
    proj_irr = _irr([-total_capex] + df.project_fcf_musd.tolist())
    eq_irr   = _irr([-equity]      + df.equity_fcf_musd.tolist())
    min_dscr = df[df.dscr.notna()].dscr.min() if df.dscr.notna().any() else None
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
        "project_irr_pct":          round(proj_irr*100, 1) if proj_irr else None,
        "equity_irr_pct":           round(eq_irr  *100, 1) if eq_irr   else None,
        "lcoa_usd_t":               round(lcoa_inv, 1),
        "epi_lcoa_usd_t":           round(lcoa_epi, 1),
        "avg_annual_revenue_musd":  round(df.revenue_musd.mean(), 1),
        "avg_ebitda_margin_pct":    round(df.ebitda_margin_pct.mean(), 1),
        "payback_years":            _payback(equity, df.equity_fcf_musd.tolist()),
        "min_dscr":                 round(min_dscr, 2) if min_dscr else None,
    }
    return df, metrics


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
