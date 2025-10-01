# src/dashboard/streamlit_app.py
import sys, os
# Make repo root discoverable so `import src...` works when running streamlit from project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import streamlit as st
import pandas as pd
import plotly.graph_objs as go
from src.data.fetch_options import get_underlying_history, list_option_expiries, fetch_option_chain
from src.simulator.delta_hedge_simulator import DeltaHedgeSimulator
from src.analytics.pnl_decomposition import compute_cumulative_pnl
import numpy as np

st.set_page_config(layout='wide', page_title='Delta-Hedged Portfolio Simulator')
st.title('Delta-Hedged Portfolio Simulator')

with st.sidebar:
    ticker = st.text_input('Ticker', value='AAPL')
    period = st.selectbox('Price history period', ['1y','6mo','3mo','1mo'], index=0)
    interval = st.selectbox('Interval', ['1d','1wk'], index=0)
    option_type = st.selectbox('Option type', ['call','put'], index=0)
    strike_input = st.number_input('Strike (leave 0 to pick from chain)', value=0.0, step=1.0)
    option_qty = st.number_input('Option quantity (positive = long)', value=1.0)
    hedge_freq = st.number_input('Hedge frequency (days)', value=1, step=1)
    vol_input = st.number_input('Implied vol (annual, e.g. 0.25)', value=0.25, step=0.01, format="%.2f")
    rf = st.number_input('Risk free rate (annual decimal)', value=0.01, step=0.001, format="%.3f")
    txn_cost = st.number_input('Transaction cost per share (USD)', value=0.0, step=0.01, format="%.2f")
    apply_slippage = st.checkbox('Apply 0.1% slippage on trades', value=False)

# Fetch expiries button
if st.button('Fetch option expiries'):
    try:
        exps = list_option_expiries(ticker)
        st.session_state['expiries'] = exps
        st.success(f'Found {len(exps)} expiries. Select one below.')
    except Exception as e:
        st.error(f'Could not fetch expiries: {e}')

expiry = st.selectbox('Expiry', options=st.session_state.get('expiries', []))

if st.button('Fetch option chain'):
    if not expiry:
        st.error('Select an expiry first.')
    else:
        try:
            calls, puts = fetch_option_chain(ticker, expiry)
            st.session_state['calls'] = calls
            st.session_state['puts'] = puts
            st.success('Fetched option chain.')
        except Exception as e:
            st.error(str(e))

# If chain present show preview and let user select strike
if 'calls' in st.session_state:
    df_chain = st.session_state['calls'] if option_type == 'call' else st.session_state['puts']

    # Pick columns safely (some fields can be missing depending on yfinance version)
    cols = [c for c in ['contractSymbol','strike','lastPrice','bid','ask','impliedVolatility'] if c in df_chain.columns]
    st.write('Option chain preview (first 10 rows)')
    st.dataframe(df_chain[cols].head(10))

    # strike selection
    if strike_input == 0.0:
        strikes = sorted(df_chain['strike'].dropna().unique())
        if len(strikes) == 0:
            st.error('No strikes available in option chain.')
            strike = None
        else:
            strike = st.selectbox('Strike', options=strikes, index=len(strikes)//2)
    else:
        strike = strike_input

    # find implied vol from chain (if exists) for selected strike/option type
    implied_vol_from_chain = None
    if strike is not None:
        # try to read the chain row for that strike
        try:
            # choose calls or puts DataFrame previously
            chain_df = df_chain.copy()
            # find first matching strike
            row = chain_df[chain_df['strike'] == strike]
            if not row.empty and 'impliedVolatility' in row.columns:
                # take mean if multiple expiries / multiple rows
                iv = float(row['impliedVolatility'].dropna().mean())
                # sometimes yfinance returns tiny numbers like 1e-5 when not available; filter them out
                if iv and iv > 1e-4:
                    implied_vol_from_chain = iv
        except Exception:
            implied_vol_from_chain = None

    st.markdown(f"**Using implied vol:** chain value = `{implied_vol_from_chain}`  — sidebar override = `{vol_input}`")

    if st.button('Run simulation'):
        if strike is None:
            st.error('Select a strike first.')
        else:
            try:
                hist_df = get_underlying_history(ticker, period=period, interval=interval)
                hist = hist_df['Close']
            except Exception as e:
                st.error(f'Failed to fetch underlying history: {e}')
                hist = None

            if hist is not None and not hist.empty:
                # choose vol: chain if available and reasonable, else use user input
                vol_to_use = implied_vol_from_chain if (implied_vol_from_chain is not None) else vol_input

                sim = DeltaHedgeSimulator(hist, strike, expiry, option_type=option_type,
                                          option_qty=option_qty, rf=rf, vol=vol_to_use,
                                          txn_cost_per_share=float(txn_cost),
                                          slippage_pct=(0.001 if apply_slippage else 0.0))
                df = sim.run(hedge_freq_days=int(hedge_freq))
                df = compute_cumulative_pnl(df)
                st.success('Simulation complete.')

                # plots
                fig1 = go.Figure()
                fig1.add_trace(go.Scatter(x=df.index, y=df['S'], name='Underlying Price', mode='lines'))
                fig1.add_trace(go.Scatter(x=df.index, y=df['option_price'], name='Option Price', mode='lines'))
                fig1.update_layout(title='Underlying & Option Price', xaxis_title='Date')
                st.plotly_chart(fig1, use_container_width=True)

                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(x=df.index, y=df['delta'], name='Option Delta', mode='lines'))
                fig2.add_trace(go.Bar(x=df.index, y=df['hedge_shares'], name='Hedge Shares', yaxis='y2', opacity=0.6))
                fig2.update_layout(title='Delta vs Hedge Shares', yaxis2=dict(overlaying='y', side='right', title='Hedge Shares'))
                st.plotly_chart(fig2, use_container_width=True)

                fig3 = go.Figure()
                fig3.add_trace(go.Scatter(x=df.index, y=df['cum_option_pnl'], name='Cumulative Option PnL'))
                fig3.add_trace(go.Scatter(x=df.index, y=df['cum_hedge_pnl'], name='Cumulative Hedge PnL'))
                fig3.add_trace(go.Scatter(x=df.index, y=df['cum_cash'], name='Cumulative Cash (financing+trades)'))
                fig3.add_trace(go.Scatter(x=df.index, y=df['cum_total_pnl'], name='Total PnL', line=dict(width=3)))
                fig3.update_layout(title='PnL Decomposition', xaxis_title='Date', yaxis_title='USD')
                st.plotly_chart(fig3, use_container_width=True)

                st.subheader('Simulation table (tail)')
                st.dataframe(df[['S','option_price','delta','hedge_shares','trade_shares','option_pnl','hedge_pnl','cash','total_pnl']].tail(30))
            else:
                st.error('No underlying history to run simulation.')
