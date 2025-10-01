from src.greeks.black_scholes import bs_price_and_greeks
import math
def test_bs_call_delta_close_to_1_when_deep_ITM():
    r = 0.01
    S = 200.0
    K = 50.0
    T = 30/252.0
    sigma = 0.2
    res = bs_price_and_greeks(S,K,T,r,sigma,'call')
    assert 0.99 < res['delta'] <= 1.0

def test_bs_put_delta_close_to_minus_one_deep_OTM():
    r = 0.01
    S = 50.0
    K = 200.0
    T = 30/252.0
    sigma = 0.2
    res = bs_price_and_greeks(S,K,T,r,sigma,'put')
    assert -1.0 <= res['delta'] < -0.99
