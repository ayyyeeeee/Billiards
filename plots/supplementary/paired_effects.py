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
from plots.supplementary.style import save_figure, interval, format_axes, match_row_limits

def draw_estimation(paired, table, out):
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.subplots_adjust(left=.13, right=.97, bottom=.13, top=.86, wspace=.40, hspace=.52)
    rng = np.random.default_rng(42)
    for i, ((task, ch, title, unit), ax) in enumerate(zip(ENDPOINTS, axes.flat)):
        subset = table[(table.task == task) & (table.channel == ch)]
        labels = []
        for y, group in enumerate(GROUPS):
            row = subset[subset.group == group].iloc[0]
            vals = paired.loc[(paired.task == task) & (paired.channel == ch) & (paired.group == group), 'delta_mae'].dropna()
            ax.scatter(vals, y + rng.uniform(-.15, .15, len(vals)), s=24,
                       facecolors='none', edgecolors=COLORS[group], alpha=.65, zorder=3)
            interval(ax, row, y, COLORS[group])
            labels.append(f'{group.title()} (n={row.n})')
        ax.set_yticks(range(3), labels)
        format_axes(ax, f'{chr(65+i)}  {title}', f'MAE change: post - baseline ({unit})')
    match_row_limits(axes)
    fig.suptitle('Paired changes in observed performance', fontsize=17, fontweight='bold', y=.97)
    fig.text(.5, .91, 'Open circles: participants   |   Diamonds: group mean with 95% BCa bootstrap CI', ha='center')
    fig.text(.5, .035, 'Negative change = lower error. Pointwise exploratory intervals; not adjusted for multiple endpoints.', ha='center', fontsize=10)
    save_figure(fig, out, 'figure5_paired_effects',
                'Paired participant MAE changes in four measured task-channel endpoints. '
                'Participants are equally weighted. Open circles show individual paired changes; '
                'diamonds and lines show group means and participant-resampled 95% BCa confidence intervals. '
                'Negative changes indicate lower observed error. Intervals are pointwise, exploratory, '
                'not multiplicity-adjusted and not evidence of equivalence when crossing zero. '
                'Within-group changes do not establish between-group superiority.')

