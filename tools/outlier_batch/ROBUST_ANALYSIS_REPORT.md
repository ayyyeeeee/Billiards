# 导师反馈排查与修正（2026-11-02）

## 发现的问题
1. 前三张图来自 learning_curve_tool/component_figures.py，旧版仍连接10球均值和样本SD。异常工具的OLS样条没有接入学习图。
2. 外部学生化残差的t检验不等于用Student-t作为逐球观测似然。旧方法也没分别拟合随练习变化的均值和方差。
3. 第四步实际脚本为根目录 plot_baseline_vs_transfer.py。旧版纳入了部分未解决状态的数值，与学习图资格条件不同。
4. 角度方差容易被短基线样本中的极值影响。旧angle-only基线样本方差：05为281.49、02为110.87、19为96.49 deg²；线性大范围压缩主体点群。
5. 有269个有效力度值存在明确评分截顶证据：训练158、基线50、后测61。角度未发现符合证据的截顶。不能把截顶值当作精确上限观测。

## 已实施
- 使用Student-t似然，nu固定5；训练均值使用5维样条，log-scale使用3维样条，二阶差分平滑惩罚1。
- 单独显示方差 scale²×5/3。蓝色阴影和阶段误差线是模型SD，不是均值置信区间。
- 历史异常标记保持原样，但新稳健模型保留所有有效极端观测，由重尾似然减弱其对趋势的影响；未评分/无效测量依通道排除，复核标志不再排除。
- 评分截顶由value、maximum、uncapped共同证实，似然使用精确边界及CDF/生存概率。uncapped是运动模型预测停点，不能冒充实测真实停点。
- 基线/后测各使用全阶段常数Student-t均值/方差，不再把30球切成三个高波动的10球摘要。
- 群体方差图使用保留零值的对数坐标，显示所有点；角度学习图必要时用标明的symlog坐标保留正负极值和主体。
- 原始样本矩和区块描述统计保留在CSV/JSON，可核对；旧OLS异常批处理仍是历史诊断，不是新主分析。

## 验证与证据
- 30名受试者全部重绘；40个训练通道、240个基线/后测通道拟合成功。
- 42项测试通过（学习图27、模型/异常/censor12、群体图3）。210个源CSV的SHA-256与修改前一致。
- 留出插值检验：交错200折平均负对数似然，新模型1.054，对照同均值样条的常方差Gaussian为1.413；连续块199个成功比较折，新模型1.102，对照1.504。连续块有1折比较未成功，未计入平均。数值越低越好；折与观测并非独立，不是未来预测或显著性检验。
- 比较同时改变重尾、变方差和惩罚，不能把全部改善归功于t分布。nu=4/5/8与惩罚0.3/1/3敏感性结果保存在robust_validation.json；默认参数未按组间效果调优。

## 输出与使用
- learning_curves/01.png 到 30.png（SVG及statistics JSON并存）。
- baseline_vs_transfer_robust/fig1_primary_measures_baseline_vs_transfer.png/pdf。
- tools/outlier_batch/run_robust_analysis.bat 一次重绘两套结果。原学习曲线桌面入口仍可使用。

## 解释边界
更平滑不代表原始噪声已被删除，也不证明训练效果。固定nu、短基线、截顶模型及残差相关都会影响结果。群体SEM未传播阶段拟合不确定性；CSV探索性配对检验未做多重比较校正，不应当作确认性结论。正式效果推断需另行设计层级/重复测量模型与不确定性分析。

## 方法来源
- Student-t稳健观测模型：https://mc-stan.org/docs/2_20/stan-users-guide/robust-noise-models.html
- 真删失CDF/尾概率似然：https://mc-stan.org/docs/stan-users-guide/censored-data.html
- Student-t密度、CDF和尺度：https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.t.html
