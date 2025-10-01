"""Black-Scholes pricing and Greeks (vectorized) for European options."""
import numpy as np
from scipy.stats import norm

def _safe_sqrt(x):
    return np.sqrt(np.maximum(x, 0.0))

def bs_price_and_greeks(S, K, T, r, sigma, option_type='call'):
    """Return dict with price, delta, gamma, vega, theta for European call/put.
    Inputs are numpy arrays or floats. T is time to expiry in years.
    sigma is annual vol (decimal).
    r is risk-free rate (annual decimal).
    """
    S = np.array(S, dtype=float)
    K = np.array(K, dtype=float)
    T = np.array(T, dtype=float)
    sigma = np.array(sigma, dtype=float)
    r = float(r)
    # handle zero time-to-expiry and avoid divide-by-zero
    eps = 1e-12
    sqrtT = _safe_sqrt(T)
    sigma_sqrtT = sigma * sqrtT + eps
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / sigma_sqrtT
    d2 = d1 - sigma_sqrtT
    Nd1 = norm.cdf(d1)
    Nd2 = norm.cdf(d2)
    nd1 = norm.pdf(d1)
    df = np.exp(-r * T)
    if option_type.lower().startswith('c'):
        price = S * Nd1 - K * df * Nd2
        delta = Nd1
    else:
        Nnd1 = norm.cdf(-d1)
        Nnd2 = norm.cdf(-d2)
        price = K * df * Nnd2 - S * Nnd1
        delta = Nd1 - 1.0  # put delta
    # gamma and vega
    gamma = nd1 / (S * sigma_sqrtT)
    vega = S * nd1 * sqrtT
    # Black-Scholes theta (annual). Return theta as annual per option.
    # Users can convert to per-day by dividing by 252 if desired.
    # Note: simplified; sign conventions follow typical derivatives texts.
    if option_type.lower().startswith('c'):
        theta = (-S * nd1 * sigma / (2 * sqrtT) - r * K * df * Nd2)
    else:
        theta = (-S * nd1 * sigma / (2 * sqrtT) + r * K * df * norm.cdf(-d2))
    return dict(price=price, delta=delta, gamma=gamma, vega=vega, theta=theta)
