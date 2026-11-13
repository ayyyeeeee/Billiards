"""Paired both-task participant means in angle/strength phase space.

Ellipses describe across-participant distributions, not confidence intervals for
the mean or trial-level motor noise. No observations are trimmed to fit axes.
"""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Ellipse
import numpy as np
import pandas as pd
from scipy.stats import chi2


GROUPS = ('both', 'strength', 'angle')
COLORS = {'both': '#0072B2', 'strength': '#D55E00', 'angle': '#009E73'}
LABELS = {'both': 'Both training', 'strength': 'Strength training', 'angle': 'Angle training'}
Q95 = float(chi2.ppf(.95, 2))


def ellipse_geometry(points):
    """Return sample-covariance 95% normal-reference distribution ellipse."""
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2 or len(points) < 3:
        raise ValueError('An ellipse requires at least three two-dimensional points.')
    if not np.isfinite(points).all():
        raise ValueError('Ellipse points must be finite.')
    center = points.mean(axis=0)
    covariance = np.cov(points, rowvar=False, ddof=1)
    values, vectors = np.linalg.eigh(covariance)
    values = np.maximum(values, 0.)
    order = np.argsort(values)[::-1]
    values, vectors = values[order], vectors[:, order]
    radii = np.sqrt(Q95*values)
    angle = np.degrees(np.arctan2(vectors[1, 0], vectors[0, 0]))
    # Exact coordinate extrema of rotated ellipse, unlike its principal radii.
    extent = np.sqrt(Q95*np.maximum(np.diag(covariance), 0.))
    return dict(center=center, covariance=covariance, width=2*radii[0],
                height=2*radii[1], angle=angle,
                area=float(np.pi*np.prod(radii)), extent=extent)


def _ratio(numerator, denominator):
    return float(numerator/denominator) if denominator > 0 else np.nan


def draw_phase_space(pairs: pd.DataFrame, out: Path) -> pd.DataFrame:
    """Draw 1x3 paired phase-space panels and return one summary row per group.

    Input: participant, group (both/strength/angle), stage (baseline/test), angle,
    strength. Each row is a signed both-task mean over jointly valid shots.
    Exactly one complete baseline/test pair per participant is required. The
    caller owns source filtering; this function never changes any source data.
    An out suffix selects the shared stem; otherwise out is an output directory.
    PNG/PDF, raw+normalized coordinates, summary CSV, and caption TXT are emitted.
    """
    required = ['participant', 'group', 'stage', 'angle', 'strength']
    if not set(required).issubset(pairs.columns):
        raise ValueError('Missing phase-space input columns: ' + ', '.join(sorted(set(required)-set(pairs.columns))))
    data = pairs[required].copy()
    data['participant'] = data['participant'].astype(str)
    data['group'] = data['group'].astype(str).str.lower()
    data['stage'] = data['stage'].astype(str).str.lower()
    if not data['group'].isin(GROUPS).all() or not data['stage'].isin(['baseline', 'test']).all():
        raise ValueError('Unknown group or stage.')
    for col in ('angle', 'strength'):
        data[col] = pd.to_numeric(data[col], errors='raise')
    if not np.isfinite(data[['angle', 'strength']].to_numpy()).all():
        raise ValueError('Phase-space pairs must have finite angle and strength means.')
    if data.duplicated(['participant', 'stage']).any():
        raise ValueError('Duplicate participant/stage pairs are ambiguous.')
    counts = data.groupby('participant').agg(n=('stage', 'size'), groups=('group', 'nunique'))
    if not ((counts['n'] == 2) & (counts['groups'] == 1)).all():
        raise ValueError('Each participant requires one baseline/test pair in one group.')
    baseline = data[data.stage == 'baseline']
    scales = baseline[['angle', 'strength']].std(ddof=1)
    if not (np.isfinite(scales).all() and (scales > 0).all()):
        raise ValueError('Pooled baseline participant SD must be positive on both axes.')
    for col in ('angle', 'strength'):
        data[col+'_normalized'] = data[col]/scales[col]

    geometry = {}
    records = []
    limit = float(np.abs(data[['angle_normalized', 'strength_normalized']].to_numpy()).max())
    for group in GROUPS:
        sub = data[data.group == group]
        n = sub.participant.nunique()
        if n < 3:
            raise ValueError(f'{group}: at least three paired participants are required.')
        for stage in ('baseline', 'test'):
            points = sub[sub.stage == stage][['angle_normalized', 'strength_normalized']].to_numpy()
            info = ellipse_geometry(points)
            geometry[group, stage] = info
            limit = max(limit, float(np.max(np.abs(info['center'])+info['extent'])))
        pre, post = geometry[group, 'baseline'], geometry[group, 'test']
        pc, tc = pre['covariance'], post['covariance']
        delta = post['center']-pre['center']
        records.append(dict(group=group, n_pairs=n,
            baseline_angle_sd_unit=float(scales.angle), baseline_strength_sd_unit=float(scales.strength),
            baseline_ellipse_area=pre['area'], test_ellipse_area=post['area'],
            area_change_pct=100*(_ratio(post['area'], pre['area'])-1),
            baseline_angle_center=pre['center'][0], baseline_strength_center=pre['center'][1],
            test_angle_center=post['center'][0], test_strength_center=post['center'][1],
            angle_center_change=delta[0], strength_center_change=delta[1],
            center_shift_distance=float(np.linalg.norm(delta)),
            baseline_target_distance=float(np.linalg.norm(pre['center'])),
            test_target_distance=float(np.linalg.norm(post['center'])),
            baseline_angle_strength_variance_ratio=_ratio(pc[0, 0], pc[1, 1]),
            test_angle_strength_variance_ratio=_ratio(tc[0, 0], tc[1, 1]),
            angle_variance_post_pre_ratio=_ratio(tc[0, 0], pc[0, 0]),
            strength_variance_post_pre_ratio=_ratio(tc[1, 1], pc[1, 1])))
    summary = pd.DataFrame(records)
    limit = max(limit*1.10, .1)

    with plt.rc_context({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'pdf.fonttype': 42, 'ps.fonttype': 42,
                         'axes.spines.top': False, 'axes.spines.right': False}):
        fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharex=True, sharey=True)
        fig.subplots_adjust(left=.065, right=.985, bottom=.15, top=.80, wspace=.18)
        for index, (ax, group) in enumerate(zip(axes, GROUPS)):
            sub = data[data.group == group]
            color = COLORS[group]
            for _, person in sub.groupby('participant', sort=True):
                pre = person[person.stage == 'baseline'].iloc[0]
                post = person[person.stage == 'test'].iloc[0]
                ax.plot([pre.angle_normalized, post.angle_normalized],
                        [pre.strength_normalized, post.strength_normalized],
                        color='#B3B3B3', linewidth=.65, alpha=.55, zorder=1)
            for stage in ('baseline', 'test'):
                cloud = sub[sub.stage == stage]
                is_pre = stage == 'baseline'
                ax.scatter(cloud.angle_normalized, cloud.strength_normalized, s=29,
                           facecolor='white' if is_pre else color,
                           edgecolor='#888888' if is_pre else 'white',
                           linewidth=.8, alpha=.95, zorder=4)
                info = geometry[group, stage]
                ax.add_patch(Ellipse(info['center'], info['width'], info['height'],
                    angle=info['angle'], facecolor='none', edgecolor='#777777' if is_pre else color,
                    linewidth=1.5, linestyle='--' if is_pre else '-', zorder=2))
                ax.scatter(*info['center'], marker='+', color='#555555' if is_pre else color,
                           s=100, linewidth=1.6, zorder=5)
            pre, post = geometry[group, 'baseline'], geometry[group, 'test']
            ax.annotate('', xy=post['center'], xytext=pre['center'],
                        arrowprops=dict(arrowstyle='->', color=color, lw=1.6), zorder=6)
            row = summary[summary.group == group].iloc[0]
            def f(value, precision=2):
                return f'{value:.{precision}f}' if np.isfinite(value) else 'undefined'
            change = f'{row.area_change_pct:+.1f}%' if np.isfinite(row.area_change_pct) else 'undefined'
            stats = (f'Area change: {change}  |  Center shift: {f(row.center_shift_distance)}\n'
                     f'Var(angle)/Var(strength): {f(row.baseline_angle_strength_variance_ratio)} '
                     f'→ {f(row.test_angle_strength_variance_ratio)}')
            ax.text(.5, 1.025, stats, transform=ax.transAxes, ha='center', va='bottom', fontsize=8.1)
            ax.set_title(f'({chr(97+index)}) {LABELS[group]}  ·  n = {int(row.n_pairs)}',
                         loc='left', pad=37, fontweight='bold', fontsize=11)
            ax.axhline(0, color='#C5C5C5', linewidth=.7, zorder=0)
            ax.axvline(0, color='#C5C5C5', linewidth=.7, zorder=0)
            ax.set(xlim=(-limit, limit), ylim=(-limit, limit),
                   xlabel='Normalized angle (baseline SD units)')
            ax.set_aspect('equal', adjustable='box')
            ax.tick_params(labelsize=9)
        axes[0].set_ylabel('Normalized strength (baseline SD units)')
        fig.text(.5, .025, '95% covariance contours of participant means; not mean-confidence intervals or within-person noise ellipses.',
                 ha='center', fontsize=8)
        handles = [Line2D([], [], marker='o', color='#888888', markerfacecolor='white',
                          linestyle='--', label='Baseline'),
                   Line2D([], [], marker='o', color='#333333', linestyle='-', label='Post-test (group color)'),
                   Line2D([], [], color='#999999', linewidth=.8, label='Paired participant'),
                   Line2D([], [], marker='+', color='#333333', linestyle='none', label='Group center')]
        fig.legend(handles=handles, loc='upper center', bbox_to_anchor=(.52, 1.005),
                   ncol=4, frameon=False, fontsize=9)
        out = Path(out)
        stem = out.with_suffix('') if out.suffix else out/'fig4_phase_space'
        stem.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(stem.with_suffix('.png'), dpi=300)
        fig.savefig(stem.with_suffix('.pdf'))
        plt.close(fig)
    data.to_csv(stem.parent/(stem.name+'_coordinates.csv'), index=False, encoding='utf-8-sig')
    summary.to_csv(stem.parent/(stem.name+'_summary.csv'), index=False, encoding='utf-8-sig')
    caption = (
        'Figure 4. Paired baseline and post-test angle–strength phase space in the both task. '
        'Each point is one participant’s mean signed angle and strength over the same jointly valid trials; '
        'gray segments connect that participant’s two stages. Baseline points and dashed ellipses are gray; '
        'post-test points and solid ellipses use the training-group color. Crosses mark group centers and '
        'arrows show baseline-to-post-test center displacement. Each coordinate is divided by the pooled '
        'baseline across-participant sample SD for that measure, without subtracting its mean, so the '
        'origin remains the zero-error target. Identical symmetric axes and equal aspect are used. '
        'Ellipses use sample covariance and the chi-square(2) 0.95 contour as a bivariate-normal '
        'reference distribution ellipse. They describe dispersion of participant means; they are not '
        '95% confidence regions for the group mean or within-person trial variability. Area change '
        'is 100 × (post-test area / baseline area − 1); positive values mean expansion. '
        'Variance ratios refer to normalized angle variance divided by normalized strength variance. '
        'Center shift is Euclidean distance in normalized coordinates. These descriptive changes do '
        'not by themselves establish learning, contraction, or angle–strength decoupling. '
        'All points and complete ellipse boundaries are included. Original-unit coordinates and '
        'normalization factors are supplied in the accompanying CSV files.\n')
    (stem.parent/(stem.name+'_caption.txt')).write_text(caption, encoding='utf-8')
    return summary
