from pathlib import Path
import warnings
import numpy as np
import pandas as pd
from scipy.stats import bootstrap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import matplotlib.pyplot as plt
from common.publication_data import GROUPS, COLORS
from plots.supplementary.schema import ENDPOINTS, CONTRASTS

def paired_metrics(stages):
    """Compute exact empirical MSE partition, preserving participant pairing.

    Population variance (ddof=0), not sample variance, gives the exact identity.
    A finite-n sensitivity partition uses mean^2 - sample_variance/n and
    sample_variance. Its squared-bias estimate may legitimately be negative.
    """
    keys = ['participant', 'group', 'task', 'channel']
    if stages.duplicated(keys + ['stage']).any():
        raise ValueError('Duplicate participant/stage/endpoint summaries')
    if stages.groupby('participant')['group'].nunique().gt(1).any():
        raise ValueError('Participant assigned to multiple groups')
    d = stages.copy()
    measured = {(task, ch) for task, ch, _, _ in ENDPOINTS}
    d = d[[tuple(x) in measured for x in d[['task', 'channel']].to_numpy()]]
    d['bias_squared'] = d['mean'] ** 2
    d['variance'] = d['sd'] ** 2 * (d['n'] - 1) / d['n'].replace(0, np.nan)
    d['mse'] = d['bias_squared'] + d['variance']
    d['corrected_bias_squared'] = d['bias_squared'] - d['sd'] ** 2 / d['n'].replace(0, np.nan)
    d['sample_variance'] = d['sd'] ** 2
    metrics = ['mae', 'bias_squared', 'variance', 'mse', 'corrected_bias_squared', 'sample_variance']
    pre = d[d.stage.eq('baseline')].set_index(keys)
    post = d[d.stage.eq('test')].set_index(keys)
    paired = pre[['n'] + metrics].join(post[['n'] + metrics], lsuffix='_pre', rsuffix='_post', how='outer')
    paired['eligible_mae'] = (paired.n_pre >= 1) & (paired.n_post >= 1)
    paired['eligible_decomposition'] = (paired.n_pre >= 2) & (paired.n_post >= 2)
    for m in metrics:
        eligible = paired.eligible_mae if m == 'mae' else paired.eligible_decomposition
        paired['delta_' + m] = (paired[m + '_post'] - paired[m + '_pre']).where(eligible)
    return paired.reset_index().sort_values(keys).reset_index(drop=True)

def bootstrap_mean(values, rng, resamples=9999, other=None):
    """BCa interval for a mean, or independent-group difference of paired means."""
    a = np.asarray(values, float)
    a = a[np.isfinite(a)]
    b = None if other is None else np.asarray(other, float)
    if b is not None:
        b = b[np.isfinite(b)]
    if len(a) < 3 or (b is not None and len(b) < 3):
        return dict(estimate=np.nan, low=np.nan, high=np.nan, method='insufficient_n', n=len(a), n_other=0 if b is None else len(b))
    estimate = a.mean() if b is None else a.mean() - b.mean()
    data = (a,) if b is None else (a, b)
    statistic = np.mean if b is None else lambda x, y, axis: np.mean(x, axis=axis) - np.mean(y, axis=axis)
    if all(np.ptp(x) == 0 for x in data):
        low = high = float(estimate)
        method = 'constant_sample'
    else:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', RuntimeWarning)
            result = bootstrap(data, statistic, vectorized=True, paired=False,
                               n_resamples=resamples, method='BCa', random_state=rng)
        low, high = map(float, result.confidence_interval)
        method = 'BCa'
        if not np.isfinite([low, high]).all():
            # Explicitly recorded fallback for degenerate jackknife distributions.
            low, high = np.quantile(result.bootstrap_distribution, [.025, .975])
            method = 'percentile_fallback'
    return dict(estimate=float(estimate), low=float(low), high=float(high), method=method,
                n=len(a), n_other=0 if b is None else len(b))

def summarize(paired, seed=20261108, resamples=9999):
    rng = np.random.default_rng(seed)
    within, contrasts, components = [], [], []
    for task, channel, _, _ in ENDPOINTS:
        d = paired[(paired.task == task) & (paired.channel == channel)]
        arrays = {}
        for group in GROUPS:
            g = d[d.group == group]
            arrays[group] = g.delta_mae.to_numpy()
            within.append(dict(task=task, channel=channel, group=group,
                               **bootstrap_mean(arrays[group], rng, resamples)))
            for metric in ('bias_squared', 'variance', 'mse', 'corrected_bias_squared', 'sample_variance'):
                components.append(dict(task=task, channel=channel, group=group, component=metric,
                                       **bootstrap_mean(g['delta_' + metric], rng, resamples)))
        for a, b in CONTRASTS:
            contrasts.append(dict(task=task, channel=channel, group_a=a, group_b=b,
                                  **bootstrap_mean(arrays[a], rng, resamples, arrays[b])))
    return pd.DataFrame(within), pd.DataFrame(contrasts), pd.DataFrame(components)

