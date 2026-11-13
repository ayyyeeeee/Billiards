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

def draw_contrasts(table, out):
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.subplots_adjust(left=.14, right=.97, bottom=.13, top=.86, wspace=.42, hspace=.52)
    for i, ((task, ch, title, unit), ax) in enumerate(zip(ENDPOINTS, axes.flat)):
        subset = table[(table.task == task) & (table.channel == ch)]
        labels = []
        for y, (a, b) in enumerate(CONTRASTS):
            row = subset[(subset.group_a == a) & (subset.group_b == b)].iloc[0]
            interval(ax, row, y, '#333333')
            labels.append(f'{a.title()} - {b.title()}')
        ax.set_yticks(range(3), labels)
        format_axes(ax, f'{chr(65+i)}  {title}', f'Difference in MAE change ({unit})')
    match_row_limits(axes)
    fig.suptitle('Between-group differences in paired change', fontsize=17, fontweight='bold', y=.97)
    fig.text(.5, .91, 'Mean contrasts with 95% BCa bootstrap CI; participants resampled independently within groups', ha='center')
    fig.text(.5, .035, 'Negative contrast favors the first group. Pointwise exploratory CIs; use Figure 3 for adjusted hypothesis tests.', ha='center', fontsize=10)
    save_figure(fig, out, 'figure7_group_contrasts',
                'Difference between group means of paired participant MAE changes. '
                'Negative values favor the first named group. Independent participant resampling '
                'within each group preserves baseline/post pairing through the change scores. '
                '95% BCa intervals are exploratory and pointwise, not Tukey-adjusted intervals. '
                'These estimates complement, and do not replace, the earlier ANOVA/Tukey analysis. '
                'Crossing zero cannot demonstrate equal efficacy; absence of a no-training group '
                'also limits causal interpretation of pre/post improvement.')

