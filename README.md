# Cartagena H2 — Investment Model v3.3

**Electryon Power Inc. | Green Ammonia Export Project**
*CONFIDENTIAL*

---

## v3.3 — Single-stream revenue, proper Ke methodology, two scenarios

### What changed from v3.2

| Change | Rationale |
|---|---|
| **Single-stream revenue** (was: H2Global + Reficar + Spot + O₂) | Cartagena did not win H2Global Window 1; Reficar offtake not committed; O₂ market thin. Single stream = NH₃ export × USD FOB price. |
| **NH₃ price $920/t USD FOB** base (was: $900/t with EUR mixing) | Defensible vs H2Global Window 1 FOB Egypt $868/t. All currency in USD; EUR conversion shown only in reference notes. |
| **Equity NPV at Ke = 15%** (was: discounted at WACC) | Methodologically correct. Project NPV uses WACC (unlevered FCF); Equity NPV uses Ke (levered FCF). |
| **Energy default is scenario-aware** | Feasibility defaults to $78/MWh industrial tariff (Arup-published, audit chain intact, reconciles to published $812/t ex-works). EPI Optimized defaults to $55/MWh long-term hydro PPA (EPM/ISAGEN/Celsia execution basis). Sidebar toggle lets either scenario flip energy basis. |
| **Two scenarios** (was: three: Feasibility + EPI Internal + FEED Base) | Cleaner pitch story: Arup audit reference + EPI execution case. FEED Base dropped. |
| **EPI Optimized scenario** (was: "EPI Internal" with conservative Western pricing) | Reflects 2026 procurement reality: Chinese AWE electrolyser, LATAM solar, Casale 2026 HB. OPEX scaled with CAPEX (Option B). |
| **Default scenario: Feasibility** (was: EPI Optimized) | Pitch posture — lead with the audit-validated number. EPI Optimized is the internal execution case. |
| **No "Father's review" references** | Professional language throughout. |

### Engine corrections retained from v3.2

| Bug fix | What it does |
|---|---|
| Project NPV nets total CAPEX | Was netting equity only — overstated by ~$331M |
| Income tax 30% FNCER with NOL carryforward | Was hardcoded to 0% |
| Colombian 5-yr straight-line depreciation | Was U.S. MACRS |
| Project FCF uses unlevered tax; equity gets debt tax shield | Was mixing tax treatment |
| Debt tenor 15 years default | Was 7 years |
| Default leverage 63/37 (ATOME Villeta cleared structure) | Was aspirational 75/25 |
| Three-tier LCOA framework (ex-works / FOB Cartagena / CIF Europe) | Was ambiguous single LCOA |

---

## Two scenarios

| Scenario | Story | Source |
|---|---|---|
| **Feasibility (Arup + Fichtner)** *(default)* | What the IDB-commissioned study says. Audit-validated reference — the pitch number. | Arup Resumen Ejecutivo Nov 2025, Tabla 6 + Fichtner FIS0001954MRP001 Jan 2025 |
| **EPI Optimized (2026 procurement)** | What 2026 procurement actually delivers. The internal execution case. | Chinese AWE tender data, LATAM solar EPC benchmarks, Casale 2026 indicative pricing |

### Headline numbers (Feasibility base case @ $78/MWh industrial tariff)

| Metric | Value |
|---|---|
| Net CAPEX | $379M (after Ley 1715 incentives $109M) |
| **Ex-works LCOA** | **$761/t** (Arup published: $812/t pre-incentive) |
| **FOB Cartagena LCOA** | **$832/t** |
| **CIF Europe LCOA** | **$892/t** |
| Project NPV @ 10% WACC | reconciliation in progress |
| Equity NPV @ 15% Ke | reconciliation in progress |
| Project IRR | reconciliation in progress |
| Equity IRR | reconciliation in progress |
| Min DSCR | reconciliation in progress |

### Benchmark comparisons (FOB to producer)

| Reference | $/t NH₃ | Cartagena Feasibility delta |
|---|---|---|
| **Feasibility FOB Cartagena** | **$832** | — |
| **Feasibility CIF Europe** | **$892** | — |
| Arup published ex-works (pre-incentive) | $812 | — (baseline) |
| H2Global Window 1 FOB Egypt | $868 (€811 × 1.07) | -$36 below |
| H2Global Window 1 CIF Rotterdam | $1,070 (€1,000 × 1.07) | **-$178 below** |
| Yara-ACME Oman (binding) | ~$650-700 | premium (RFNBO + Atlantic) |
| BNEF 2030 green NH₃ forecast | $700-900 | within range |

### EPI Optimized reference numbers (@ $55/MWh hydro PPA)

### EPI Optimized reference numbers (@ $55/MWh hydro PPA)

| Metric | Value |
|---|---|
| Net CAPEX | $365M |
| **Ex-works LCOA** | **$598/t** |
| **FOB Cartagena LCOA** | **$664/t** |
| **CIF Europe LCOA** | **$724/t** |
| Project NPV @ 10% WACC | $189M |
| Equity NPV @ 15% Ke | $148M |
| Project IRR | 16.5% |
| Equity IRR | 31.6% |
| Min DSCR | 2.54× |

---

## ATOME Villeta — the live comp

ATOME PLC reached FID on its Villeta CAN fertilizer project in Paraguay on **23 April 2026**:

| Component | Value |
|---|---|
| Total project | $665M |
| **Debt** | **$420M (63%)** |
| **Equity** | **$245M (37%)** |
| Debt tenor | 15 years |
| Debt providers | IDB Invest (coordinator), IFC, EIB ($135M), FMO, Green Climate Fund ($50M concessional) |
| Equity providers | Hy24 (lead), IFC, KfW DEG, IFDK, EFSD+, Sudameris, ATOME PLC |
| EPC | Casale ($465M fixed-price) |
| Offtake | Yara (10-yr take-or-pay, 260 ktpa CAN) |
| COD | October 2029 |

Our v3.3 defaults mirror ATOME's cleared structure: 63/37 leverage, 15-yr tenor.

---

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Two views

- **Executive view** — Hero header, 6 KPI cards including three-tier LCOA, cashflow + equity returns, CAPEX waterfall + cross-scenario comparison, single-stream revenue evolution, sensitivity
- **Analyst view** — 8 tabs: Scenarios, **Operating metrics** (plant config, energy balance, production, efficiency KPIs, ramp profile), CAPEX detail, OPEX detail, 25-yr cashflow, Revenue, LCOA build, Tax & Financing (with ATOME Villeta side-by-side comp)

## Sidebar controls

- **Scenario** (Feasibility — default / EPI Optimized)
- **View** (Executive / Analyst)
- **Macro overrides**: WACC, **cost of equity Ke**, leverage (default 0.63), tax rate, NH₃ price (default $920/t)
- **Energy supply** toggle (scenario-aware default): Industrial tariff $78/MWh (Feasibility default) / Long-term hydro PPA $55/MWh (EPI Optimized default)

---

## File structure

```
cartagena_h2_model_v33/
├── app.py              # Streamlit dashboard (~1,490 lines)
├── model_engine.py     # Financial engine (~1,110 lines)
├── requirements.txt    # Dependencies
└── README.md           # This file
```

## Deploy to Streamlit Community Cloud

1. Push this folder to a GitHub repo
2. Go to share.streamlit.io → New app → point to app.py
3. Share the URL

---

## Sources

| Source | Use |
|--------|-----|
| Arup Resumen Ejecutivo (Nov 2025, IDB-commissioned) | Core process plant CAPEX/OPEX |
| Fichtner FIS0001954MRP001 (Jan 2025, IDB-commissioned) | Peripheral infrastructure |
| **ATOME Villeta FID (April 2026)** | **Leverage / DFI structure comp** |
| H2Global Hintco Lot 1 award (July 2024) | €811/t FOB Egypt; €1,000/t CIF Rotterdam |
| IEA Electrolysers (2025) | 2026 commercial benchmarks |
| IRENA Green Hydrogen Cost (2024) | Cost trajectory |
| Hydrogen Insight / BNEF | Chinese AWE pricing |
| BNEF green NH₃ 2030 forecast | $700-900/t producer range |
| Intratec ammonia price index (April 2026) | Grey NH₃ spot CFR NW Europe |

---

*Prepared for Electryon Power Inc. internal use. May 13, 2026.*
