import pandas as pd
import numpy as np

def series_to_float(s):
    return float(np.atleast_1d(s)[0])

def ensure_series(x):
    if isinstance(x, pd.Series):
        return x
    return pd.Series(x)
