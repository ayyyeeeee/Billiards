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

def draw_decomposition(table, out):
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.subplots_adjust(left=.10, right=.97, bottom=.14, top=.83, wspace=.28, hspace=.52)
    for i, ((task, ch, title, unit), ax) in enumerate(zip(ENDPOINTS, axes.flat)):
        d = table[(table.task == task) & (table.channel == ch)]
        for x, group in enumerate(GROUPS):
            g = d[d.group == group].set_index('component')
            for metric, offset, hatch, alpha in (('bias_squared', -.20, '///', .40), ('variance', 0, None, .8)):
                row = g.loc[metric]
                ax.bar(x+offset, row.estimate, width=.17, color=COLORS[group], alpha=alpha,
                       hatch=hatch, edgecolor=COLORS[group], linewidth=.8, zorder=3)
            total = g.loc['mse']
            ax.vlines(x+.20, total.low, total.high, color='#222222', lw=1.5, zorder=5)
            ax.plot(x+.20, total.estimate, 'D', color='#222222', ms=5, zorder=6)
        ax.axhline(0, color='#666666', lw=1, zorder=1)
        ax.set_xticks(range(3), [g.title() for g in GROUPS])
        ax.set_ylabel(f'Post - baseline ({unit}$^2$)')
        ax.set_title(f'{chr(65+i)}  {title}', loc='left', fontweight='bold')
        ax.grid(axis='y', color='#e6e6e6', zorder=0)
        ax.set_axisbelow(True)
    fig.suptitle('Separating observed bias and trial variability', fontsize=17, fontweight='bold', y=.97)
    handles = [Patch(facecolor='#bbbbbb', edgecolor='#555555', hatch='///', label='Change in squared signed mean'),
               Patch(facecolor='#777777', label='Change in within-person variance (ddof=0)'),
               Line2D([0], [0], color='#222222', marker='D', label='Total MSE change with 95% CI')]
    fig.legend(handles=handles, loc='upper center', bbox_to_anchor=(.5, .915), ncol=3, frameon=False, fontsize=9)
    fig.text(.5, .035, 'MSE = squared signed mean + within-person variance. Bars sum to the diamond; negative values are reductions.\nPanel scales differ. Observed scores, not latent motor noise. Finite-sample sensitivity estimates are in the table.', ha='center', fontsize=10)
    save_figure(fig, out, 'figure6_error_decomposition',
                'Descriptive decomposition of observed mean squared error (MSE), with target zero. '
                'For each participant and stage, MSE = mean(value)^2 + variance(value, ddof=0). '
                'Paired changes in the two terms sum exactly to the paired MSE change. '
                'Bars show equally weighted participant means; diamonds show total MSE change '
                'and participant-resampled 95% BCa CI. Component intervals are in the CSV table. '
                'Small baseline sample size increases sampling error of the empirical signed mean. '
                'A sensitivity table therefore also partitions MSE as (mean^2 - s^2/n) + s^2; '
                'this bias correction assumes identically distributed, independent trials and may '
                'produce negative squared-bias estimates. Neither partition isolates intrinsic motor noise. '
                'Capped recorded scores remain capped, so these are observed-score moments.')

