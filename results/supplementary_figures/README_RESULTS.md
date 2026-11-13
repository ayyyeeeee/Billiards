# 补充图：应该继续研究什么

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
BCa bootstrap 9999次，随机种子 20261108。先形成每人配对差值，再以人为单位重抽样；组间独立重抽样，绝不把击球当作独立受试者。
实现依据：[SciPy bootstrap 文档](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html)。
退化分布的区间算法明确写在 method 列。样本不足3人则区间不估计。

MSE = signed_mean² + population_variance，其中 population_variance = sample_SD² × (n−1)/n。
component_statistics.csv 同时给出有限样本敏感性分解：(signed_mean² − sample_SD²/n) + sample_SD²。
后者纠正均值平方的抽样偏差，但依赖阶段内独立同分布假设，可能出现负的平方偏差估计，不截断为零。

## 当前配对 MAE 结果（原始单位）
|任务/通道|组|人数|平均变化|95% BCa CI|
|---|---|---:|---:|---|
|both/strength|both|10|-0.101|[-0.196, 0.088]|
|both/strength|strength|10|-0.231|[-0.318, -0.158]|
|both/strength|angle|10|-0.134|[-0.211, -0.052]|
|strength/strength|both|10|-0.106|[-0.175, -0.031]|
|strength/strength|strength|10|-0.187|[-0.257, -0.116]|
|strength/strength|angle|10|-0.068|[-0.118, -0.032]|
|both/angle|both|10|-0.663|[-1.801, -0.015]|
|both/angle|strength|10|-1.020|[-2.047, -0.382]|
|both/angle|angle|10|-0.835|[-1.655, -0.239]|
|angle/angle|both|10|-0.887|[-1.844, -0.240]|
|angle/angle|strength|10|-1.492|[-2.558, -0.417]|
|angle/angle|angle|10|-0.784|[-3.261, 0.287]|

## 当前最值得继续检验的现象
Angle组在angle-only任务的经验方差变化为 6.84 deg²，95%区间 [-11.76, 52.48]。
该组平均偏差平方变化为 -7.86 deg²；合计MSE变化为 -1.02 deg²。
这提示“偏差减小”和“波动减小”未必同步，但区间很宽，不能据此断言方差增大已经被证实。
12项直接组间对比中，10项95%探索性区间跨过零。剩余未跨零的区间也没有校正多重比较，不能替代原Tukey结果或被选作确认性发现。
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
