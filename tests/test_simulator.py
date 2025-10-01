import pandas as pd
from src.simulator.delta_hedge_simulator import DeltaHedgeSimulator
def test_simulator_runs():
    idx = pd.date_range('2024-01-01', periods=10, freq='B')
    prices = pd.Series([100 + i for i in range(len(idx))], index=idx)
    sim = DeltaHedgeSimulator(prices, strike=100, expiry='2025-01-01', option_type='call', option_qty=1, vol=0.2)
    df = sim.run(hedge_freq_days=1)
    assert not df.empty
    assert 'option_price' in df.columns
