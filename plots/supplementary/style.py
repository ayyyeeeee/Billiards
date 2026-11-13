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

def save_figure(fig, out, stem, caption):
    fig.savefig(out / (stem + '.png'), dpi=300)
    fig.savefig(out / (stem + '.pdf'))
    (out / (stem + '_caption.txt')).write_text(caption, encoding='utf-8')
    plt.close(fig)

def interval(ax, row, y, color, marker='D'):
    if np.isfinite([row.estimate, row.low, row.high]).all():
        ax.hlines(y, row.low, row.high, color=color, lw=2.4, zorder=5)
        ax.plot([row.low, row.high], [y, y], '|', color=color, ms=8, zorder=5)
        ax.plot(row.estimate, y, marker, color=color, ms=7, mec='white', mew=.7, zorder=6)

def format_axes(ax, title, xlabel):
    ax.axvline(0, color='#666666', ls='--', lw=1, zorder=0)
    ax.grid(axis='x', color='#e6e6e6', lw=.7)
    ax.set_axisbelow(True)
    ax.set_title(title, loc='left', fontweight='bold', pad=11)
    ax.set_xlabel(xlabel)
    ax.set_ylim(2.65, -.65)
    ax.tick_params(axis='y', length=0)

def match_row_limits(axes):
    """Same units within a row: retain every point/interval on a shared scale."""
    for row in axes:
        limits = [a.get_xlim() for a in row]
        lo, hi = min(x[0] for x in limits), max(x[1] for x in limits)
        for ax in row:
            ax.set_xlim(lo, hi)

