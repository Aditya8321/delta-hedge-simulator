"""Utilities to fetch underlying history and option chains using yfinance."""
import yfinance as yf
import pandas as pd
from datetime import datetime

def get_underlying_history(ticker, period='1y', interval='1d'):
    t = yf.Ticker(ticker)
    df = t.history(period=period, interval=interval, auto_adjust=False)
    if df.empty:
        raise RuntimeError(f"No price history for {ticker}")
    df = df[['Open','High','Low','Close','Volume']].copy()
    df.index = pd.to_datetime(df.index)
    return df

def list_option_expiries(ticker):
    t = yf.Ticker(ticker)
    return t.options  # list of expiry strings 'YYYY-MM-DD'

def fetch_option_chain(ticker, expiry):
    t = yf.Ticker(ticker)
    chains = t.option_chain(expiry)
    # returns namedtuple (calls, puts)
    calls = chains.calls.copy()
    puts = chains.puts.copy()
    # ensure numeric types
    for df in (calls, puts):
        df['strike'] = pd.to_numeric(df['strike'], errors='coerce')
    return calls, puts
