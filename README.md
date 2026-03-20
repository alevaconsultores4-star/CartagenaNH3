# Cartagena H2 — Financial Model
**Electryon Power Inc. | Green Ammonia Export Project**
*CONFIDENTIAL*

## Overview
Interactive 30-year DCF financial model for Project Cartagena H2.
300 MWp Solar + 195 MW Alkaline Electrolyser + 111 ktpa NH₃ → Europe / Asia / Colombia.

## Data Sources
| Source | Content |
|--------|---------|
| Arup Feasibility (Nov 2025) | CAPEX, OPEX, LCOA, production config |
| Fichtner Peripheral (Jan 2025) | Export facility, pipeline, power, WTP, KOH |
| Electryon Deck (Mar 2026) | Revenue, off-takers, Colombian incentives |
| H2Global/Hintco Lot 1 | €811/t net price benchmark + CfD structure |
| IMARC Q3 2025 | Market prices ($840–$902/t) |
| IRENA 2022 | Cost trajectory forecasts |

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the dashboard
streamlit run app.py

# Opens at http://localhost:8501
```

## Share with the Team

### Option A — Streamlit Community Cloud (free, 5 min)
1. Push this folder to a GitHub repo
2. Go to share.streamlit.io → New app → point to app.py
3. Share the URL with anyone — no install needed

### Option B — Internal server
```bash
streamlit run app.py --server.port 8080 --server.address 0.0.0.0
```

### Option C — Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

## Model Structure
```
cartagena_h2_model/
├── app.py              # Streamlit dashboard (UI + charts)
├── model_engine.py     # Financial model logic (pure Python)
├── requirements.txt    # Dependencies
└── README.md
```

## Key Model Outputs
- **LCOA** (Levelized Cost of Ammonia) — $/t NH₃
- **Project IRR** — pre-financing returns
- **Equity IRR** — post-debt, post-tax returns
- **NPV** @ WACC
- **Revenue stack** — H2Global HPA + Ameropa spot + Colombia domestic
- **Sensitivity tornado** — LCOA and IRR vs 8 key variables
- **IRR heatmap** — NH₃ price × leverage matrix
- **30-year cashflow bridge** — annual EBITDA, tax, debt service

## Revenue Channels Modelled
1. **H2Global HPA (Hintco South America lot)** — €811/t net, up to 10-yr contract
2. **Ameropa MOU** — spot/long-term at market price
3. **Colombia domestic** — Reficar H₂ off-take at $4.02/kg

## Colombian Tax Incentives (Ley 1715/2099)
- 50% income tax deduction on investment × 15 years
- 100% VAT exemption on equipment/services
- Import tariff exemption on machinery
- 3–5yr accelerated depreciation

## Next Steps to Build On
- [ ] Add hourly generation simulation (8,760-hr solar profile for Arjona/Sincerín)
- [ ] Add financing tab (DSCR, debt sculpting, equity waterfall)
- [ ] Add GHG intensity calculator (gCO₂e/kgNH₃ vs RFNBO threshold)
- [ ] Export to Excel button
- [ ] Phase 2 expansion scenario (doubling electrolyser capacity)
