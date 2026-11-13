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

from common.publication_data import load_data, GROUPS, COLORS
from common.paths import PARTICIPANT_ROOT, output_path
import matplotlib.pyplot as plt

from plots.supplementary.schema import ENDPOINTS, CONTRASTS
from plots.supplementary.statistics import paired_metrics, bootstrap_mean, summarize
from plots.supplementary.style import save_figure, interval, format_axes, match_row_limits
from plots.supplementary.paired_effects import draw_estimation
from plots.supplementary.group_contrasts import draw_contrasts
from plots.supplementary.decomposition import draw_decomposition




















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
    parser.add_argument('--root', type=Path, default=PARTICIPANT_ROOT)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--seed', type=int, default=20261108)
    parser.add_argument('--resamples', type=int, default=9999)
    args = parser.parse_args()
    if args.resamples < 1000:
        parser.error('--resamples must be at least 1000')
    root = args.root.resolve()
    out = (args.out or output_path(root, 'supplementary_figures')).resolve()
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
