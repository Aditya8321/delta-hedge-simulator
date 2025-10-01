import pandas as pd

def compute_cumulative_pnl(df):
    """Given simulator output, compute cumulative PnL columns and simple metrics."""
    out = df.copy()
    out['cum_option_pnl'] = out['option_pnl'].cumsum()
    out['cum_hedge_pnl'] = out['hedge_pnl'].cumsum()
    # cash already accumulates via interest in simulator; track net cash change
    out['cum_cash'] = out['cash'] - out['cash'].iloc[0]
    out['cum_total_pnl'] = out['total_pnl']
    return out
