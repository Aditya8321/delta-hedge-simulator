# src/simulator/delta_hedge_simulator.py
import numpy as np
import pandas as pd
from datetime import datetime
from src.greeks.black_scholes import bs_price_and_greeks

class DeltaHedgeSimulator:
    def __init__(self, prices: pd.Series, strike: float, expiry: str,
                 option_type='call', option_qty=1, rf=0.01, vol=0.25,
                 txn_cost_per_share: float = 0.0, slippage_pct: float = 0.0):
        """
        prices: pd.Series indexed by date of underlying close prices.
        expiry: 'YYYY-MM-DD' string (option expiry).
        vol: implied vol used for pricing (annual) - can be a scalar or a pd.Series aligned with prices.
        rf: annual risk-free rate (decimal)
        txn_cost_per_share: fixed USD cost per share traded (round-trip applied on trades)
        slippage_pct: fraction of trade value as slippage (e.g., 0.001 = 0.1%)
        """
        self.prices = prices.sort_index().copy()
        self.strike = float(strike)
        self.expiry = pd.to_datetime(expiry)
        self.option_type = option_type
        self.option_qty = float(option_qty)
        self.rf = float(rf)
        self.vol = vol
        self.txn_cost_per_share = float(txn_cost_per_share)
        self.slippage_pct = float(slippage_pct)

    def time_to_expiry(self, current_date):
        days = (self.expiry.date() - pd.to_datetime(current_date).date()).days
        if days < 0:
            return 0.0
        return days / 252.0  # trading days approximation

    def _vol_for_date(self, date):
        # vol may be scalar or a series
        if isinstance(self.vol, pd.Series):
            if date in self.vol.index:
                return float(self.vol.loc[date])
            else:
                return float(self.vol.fillna(method='ffill').iloc[0]) if not self.vol.empty else float(self.vol.iloc[0])
        else:
            return float(self.vol)

    def run(self, hedge_freq_days=1, start_cash=0.0):
        dates = list(self.prices.index)
        records = []

        option_pos = self.option_qty
        hedge_shares = 0.0
        cash = float(start_cash)

        prev_option_price = None
        prev_S = None
        prev_hedge_shares = 0.0

        cum_option_pnl = 0.0
        cum_hedge_pnl = 0.0

        for i, d in enumerate(dates):
            S = float(self.prices.loc[d])
            T = self.time_to_expiry(d)
            vol_today = self._vol_for_date(d)
            bs = bs_price_and_greeks(S, self.strike, T, self.rf, vol_today, self.option_type)
            option_price = float(np.atleast_1d(bs['price'])[0])
            delta = float(np.atleast_1d(bs['delta'])[0])

            # Decide whether to rebalance today
            rebalance = (i % max(1, int(hedge_freq_days)) == 0)

            trade_shares = 0.0
            trade_value = 0.0
            trade_costs = 0.0

            if rebalance:
                target_hedge = -delta * option_pos
                trade_shares = target_hedge - hedge_shares
                # trade execution: assume executed at close price, with optional slippage and fixed txn cost
                trade_price = S * (1.0 + np.sign(trade_shares) * self.slippage_pct)
                trade_value = trade_shares * trade_price
                # transaction cost per share (applied absolute)
                trade_costs = abs(trade_shares) * self.txn_cost_per_share
                cash -= trade_value  # pay for shares (negative trade_value means we received cash)
                cash -= trade_costs
                hedge_shares = target_hedge

            # Compute PnL components
            if prev_option_price is not None:
                option_pnl = (option_price - prev_option_price) * option_pos
            else:
                option_pnl = 0.0

            # hedge pnl equals change in value of previously held hedge shares (before today's rebalance)
            if prev_S is not None:
                hedge_pnl = prev_hedge_shares * (S - prev_S)
            else:
                hedge_pnl = 0.0

            cum_option_pnl += option_pnl
            cum_hedge_pnl += hedge_pnl

            # accrue interest on cash (simple discrete per day)
            if i > 0:
                cash *= (1.0 + self.rf / 252.0)

            total_pnl = cum_option_pnl + cum_hedge_pnl + (cash - start_cash)

            records.append({
                'date': d,
                'S': S,
                'option_price': option_price,
                'delta': delta,
                'option_pos': option_pos,
                'hedge_shares': hedge_shares,
                'prev_hedge_shares': prev_hedge_shares,
                'trade_shares': trade_shares,
                'trade_value': trade_value,
                'trade_costs': trade_costs,
                'option_pnl': option_pnl,
                'hedge_pnl': hedge_pnl,
                'cum_option_pnl': cum_option_pnl,
                'cum_hedge_pnl': cum_hedge_pnl,
                'cash': cash,
                'total_pnl': total_pnl
            })

            # update prev values for next step
            prev_option_price = option_price
            prev_S = S
            prev_hedge_shares = hedge_shares

        df = pd.DataFrame.from_records(records).set_index('date')
        # Add some cumulative convenience columns (alias)
        df['cum_total_pnl'] = df['total_pnl']
        df['cum_cash'] = df['cash'] - start_cash
        return df
