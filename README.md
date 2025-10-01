# Delta-Hedged Portfolio Simulator

This repository contains a Streamlit dashboard and library to simulate delta-hedged option positions using real option chains from Yahoo Finance (`yfinance`).

Features
- Fetch option chains and underlying history via `yfinance`
- Black-Scholes pricing and Greeks for European options (vectorized)
- Pathwise delta-hedge simulator that rebalances at configurable frequency
- P&L decomposition: option value change, hedge trading P&L, financing carry
- Streamlit dashboard with interactive controls and Plotly charts

Run locally:
```bash
# unzip and enter folder if you downloaded a zip
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run src/dashboard/streamlit_app.py
