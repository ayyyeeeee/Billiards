"""Identify documented score clipping; never infer censoring from large values alone.

The signed processed values retain the unsigned upstream ``*_uncapped`` and
``*_maximum`` columns. Only their joint evidence establishes clipping. These
helpers do not apply eligibility rules; callers retain independent channel masks.
"""
import numpy as np
import pandas as pd


def _numeric(df, column):
    if column not in df:
        return np.full(len(df), np.nan)
    return pd.to_numeric(df[column], errors="coerce").to_numpy(dtype=float)


def censor_codes(df, channel):
    """Return aligned -1/0/+1 codes for proven left/exact/right observations.

    Source strength scores are rounded to six decimals, angles to two. The
    tolerance only accommodates that rounding; uncapped values must exceed the
    limit beyond that tolerance. Missing evidence remains code 0, not proof
    that the observation was unbounded. Eligibility is the caller's concern.
    """
    if channel not in ("angle", "strength"):
        raise ValueError("channel must be angle or strength")
    value = _numeric(df, channel + "_value")
    maximum = _numeric(df, channel + "_maximum")
    uncapped = _numeric(df, channel + "_uncapped")
    tolerance = .005000001 if channel == "angle" else .000000500001
    proven = (np.isfinite(value) & np.isfinite(maximum) & np.isfinite(uncapped)
              & (maximum > 0)
              & (np.abs(np.abs(value) - maximum) <= tolerance)
              & (np.abs(uncapped) > maximum + tolerance))
    return np.where(proven, np.sign(value), 0).astype(np.int8)


def censor_values(df, channel):
    """Return likelihood values; replace proven caps by exact signed bounds.

    This returns new arrays only; the DataFrame and source data are untouched.
    """
    codes = censor_codes(df, channel)
    values = _numeric(df, channel + "_value")
    maximum = _numeric(df, channel + "_maximum")
    capped = codes != 0
    values[capped] = codes[capped] * maximum[capped]
    return values
