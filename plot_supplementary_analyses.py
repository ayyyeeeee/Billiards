"""Additional paired estimation and error decomposition figures; sources read-only.

Run python plot_supplementary_analyses.py. Reuses the audited publication loader.
All uncertainty resamples participants, never treats shots as independent people.
"""
from pathlib import Path
import argparse
import hashlib
import json
import warnings

import numpy as np
import pandas as pd
from scipy.stats import bootstrap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from plot_publication_figures import load_data, GROUPS, COLORS
import matplotlib.pyplot as plt

ENDPOINTS = (
    ('both', 'strength', 'Both task: strength', 'strength units'),
    ('strength', 'strength', 'Strength-only task', 'strength units'),
    ('both', 'angle', 'Both task: angle', 'degrees'),
    ('angle', 'angle', 'Angle-only task', 'degrees'),
)
CONTRASTS = (('both', 'strength'), ('both', 'angle'), ('strength', 'angle'))


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


def write_readme(out, within, contrasts, components, seed, resamples):
    rows = []
    for _, r in within.iterrows():
        rows.append(f'|{r.task}/{r.channel}|{r.group}|{r.n}|{r.estimate:.3f}|[{r.low:.3f}, {r.high:.3f}]|')
    angle = components[(components.task=='angle') & (components.channel=='angle') & (components.group=='angle')].set_index('component')
    variance = angle.loc['variance']
    contrast_crossing = int(((contrasts.low <= 0) & (contrasts.high >= 0)).sum())
    text = f'''# 补充图：应该继续研究什么

运行根目录 `run_supplementary_analyses.bat`，或 `python plot_supplementary_analyses.py`。
可指定 `--root`、`--out`、`--seed` 和 `--resamples`。依赖沿用 `requirements_publication.txt`。

## 三个值得回答的问题
1. Figure 5：各组改变多大、个体是否一致、估计有多精确？展示每人 MAE 差值与组均值95%区间，补充原雨云图的显著性检验。
2. Figure 6：改善来自平均瞄准偏差减小，还是试次波动减小？使用同一人的观测 MSE 精确分解；不把两种机制混在 MAE 中。
3. Figure 7：联合训练是否比单项训练带来更大迁移？直接估计组间变化量之差。不能用“一组显著、另一组不显著”代替组间比较。

## 数据和方法
复用 plot_publication_figures.py 的真实来源读取器，01–30三组各10人。
本次新图只分析 processed_csv 中 baseline/test；训练资料读取与校验沿用严格 scored 且 outlier!=1 规则，但不进入这三张新图的统计。
各通道仅有限且 scored 的观测参与；如有 outlier 字段，1 排除。未测通道不填零。每人每阶段按实际行数计算，每人在组内等权。
所有表用 utf-8-sig 写入独立输出目录；不修改任何来源 CSV 或标记。
BCa bootstrap {resamples}次，随机种子 {seed}。先形成每人配对差值，再以人为单位重抽样；组间独立重抽样，绝不把击球当作独立受试者。
实现依据：[SciPy bootstrap 文档](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html)。
退化分布的区间算法明确写在 method 列。样本不足3人则区间不估计。

MSE = signed_mean² + population_variance，其中 population_variance = sample_SD² × (n−1)/n。
component_statistics.csv 同时给出有限样本敏感性分解：(signed_mean² − sample_SD²/n) + sample_SD²。
后者纠正均值平方的抽样偏差，但依赖阶段内独立同分布假设，可能出现负的平方偏差估计，不截断为零。

## 当前配对 MAE 结果（原始单位）
|任务/通道|组|人数|平均变化|95% BCa CI|
|---|---|---:|---:|---|
{chr(10).join(rows)}

## 当前最值得继续检验的现象
Angle组在angle-only任务的经验方差变化为 {variance.estimate:.2f} deg²，95%区间 [{variance.low:.2f}, {variance.high:.2f}]。
该组平均偏差平方变化为 {angle.loc['bias_squared','estimate']:.2f} deg²；合计MSE变化为 {angle.loc['mse','estimate']:.2f} deg²。
这提示“偏差减小”和“波动减小”未必同步，但区间很宽，不能据此断言方差增大已经被证实。
12项直接组间对比中，{contrast_crossing}项95%探索性区间跨过零。剩余未跨零的区间也没有校正多重比较，不能替代原Tukey结果或被选作确认性发现。
具体数值见 group_contrast_statistics.csv 与 component_statistics.csv。

## 解释边界
- 区间为探索性逐项区间，没有多重比较校正；不能取代原Figure3的Tukey检验，不能据其挑选显著发现。
- 区间跨零表示方向/幅度仍有不确定性，不等于已证明无差异或等效。
- 各组仅10人；bootstrap不能创造信息，极端参与者会影响MSE与区间。不删除合法极值来使图平滑。
- 基线约10次、后测约30次，均值估计精度不同；请同时看有限样本敏感性表，不能将经验偏差平方的降低全解释为偏差学习。
- 力度存在截顶；这些图描述记录分数，不恢复未观测尾部，也不替代已有Student-t/真实截顶模型。
- 阶段内方差还可能含系统性漂移、疲劳和测量误差，不能直接命名为“纯内部运动噪声”。
- 实验没有未训练对照，组内前后变化本身不能排除重复测验等影响。

后续机制研究优先考虑统一终点的组别×阶段模型，以及重复基线/延迟保持测试。
当前数据不能凭协方差椭圆收缩直接证明力量与角度控制解耦；也不宜用基线值对变化值作简单相关来证明学习潜力。
'''
    (out/'README_RESULTS.md').write_text(text, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--seed', type=int, default=20261108)
    parser.add_argument('--resamples', type=int, default=9999)
    args = parser.parse_args()
    if args.resamples < 1000:
        parser.error('--resamples must be at least 1000')
    root = args.root.resolve()
    out = (args.out or root/'supplementary_figures').resolve()
    # Derived output must not enter participant source trees.
    if any(out == root/f'{i:02d}' or root/f'{i:02d}' in out.parents for i in range(1,31)):
        parser.error('Output must be outside participant folders')
    stages, _, _, _, hashes = load_data(root)
    paired = paired_metrics(stages)
    within, contrasts, components = summarize(paired, args.seed, args.resamples)
    out.mkdir(parents=True, exist_ok=True)
    for name, table in [('participant_paired_metrics', paired), ('paired_effect_statistics', within),
                        ('group_contrast_statistics', contrasts), ('component_statistics', components)]:
        table.to_csv(out/(name+'.csv'), index=False, encoding='utf-8-sig', na_rep='')
    plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':10, 'pdf.fonttype':42,
                         'axes.spines.top':False, 'axes.spines.right':False, 'savefig.dpi':300})
    draw_estimation(paired, within, out)
    draw_decomposition(components, out)
    draw_contrasts(contrasts, out)
    write_readme(out, within, contrasts, components, args.seed, args.resamples)
    changed = [p for p, digest in hashes.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest() != digest]
    if changed:
        raise RuntimeError(f'Inputs changed during execution: {changed}')
    (out/'source_hashes.json').write_text(json.dumps(hashes, indent=2), encoding='utf-8')
    manifest = dict(seed=args.seed, resamples=args.resamples, confidence_level=.95,
                    input_files_unchanged=len(hashes), participants=int(paired.participant.nunique()),
                    paired_endpoints=len(paired), eligible_mae=int(paired.eligible_mae.sum()),
                    eligible_decomposition=int(paired.eligible_decomposition.sum()))
    (out/'run_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest, indent=2))
    print(f'Figures and tables saved: {out}')


if __name__ == '__main__':
    main()
