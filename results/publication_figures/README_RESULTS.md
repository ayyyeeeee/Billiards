# 三张核心图：运行与结果说明

运行：在 D:/experiment 双击 run_publication_figures.bat，或执行：

```powershell
python plot_publication_figures.py --root D:/experiment --out D:/experiment/publication_figures
```

依赖安装（其他计算机）：`python -m pip install -r requirements_publication.txt`。主入口调用同目录 publication_raincloud.py 和 publication_phase_space.py；保持这三个文件放在一起。只读取输入数据，输出默认 publication_figures。代码没有写回源CSV的路径。

## 已核实的限制及处理
- group_assignments.json 含01–60，本任务只取01–30，三组各10人。
- 训练严格status=scored且outlier!=1；顺序按原shot的10球窗口分14块，不把剔除后的点重新拼块，部分块按实际人数计算SEM。
- 三组训练不同指标，不能把角度(deg)和力度直接平均。因此Figure2是按各人对应任务基线RMS归一化的训练指标，Both等权平均两个归一化通道。它比较各自训练任务的相对变化，不是同一原始终点的组间疗效比较。所有原单位逐通道值另存CSV。
- Figure3中Angle-only任务没有Strength记录，Strength-only任务没有Angle记录；两格明确标为Not measured，绝不填零或编造10个点。
- Figure4使用每人both-task共同有效试次的signed mean，双轴除以全体基线参与者均值的SD(不减均值，靶心保持0)。椭圆为参与者均值分布的95%正态参照协方差轮廓，不是组均值95%CI，不是单人试次噪声。基线10球、后测约30球造成均值精度不同，也可影响面积变化。

## 实际结果
四个可测迁移面板的Tukey HSD共12项比较均为n.s.，不能宣称组间迁移特异性已得到证明。ANOVA的4项Holm校正p值为0.661、0.247、1、1。原始统计及Levene诊断见figure3_statistics.csv。

Figure2的Strength和Angle组SD衰减速率不能在14块观察范围内可靠识别，图例明确标注，不把数值优化器返回的极端tau当作学习率。全部拟合参数及数值诊断见figure2_decay_fits.csv。

以下为Figure4实际描述统计；方差比=Post/Pre，<1为减小，>1为增大。

|组|椭圆面积变化|角度方差比|力度方差比|基线中心距靶心|后测中心距靶心|
|---|---:|---:|---:|---:|---:|
|both|-48.35%|0.209|0.944|0.288|0.311|
|strength|-77.21%|0.462|0.115|0.804|0.148|
|angle|-55.47%|0.177|0.291|0.609|0.499|

三组面积都减小，但Both力度方向几乎未收缩，Angle组两方向均缩小，不能把图解释为“Both双向、Strength仅Y、Angle仅X”的机制已被证明。所有中心/面积计算均使用真实数据，不强制满足假说。

## 验证
10项测试通过；30名受试者，40个训练通道，420个受试者×block摘要；Figure3每个可测面板各组10个独立个体差值。PNG分别3600×1500、4500×2700、4500×1500，300DPI；PDF分别12×5、15×9、15×5英寸，包含嵌入字体且没有栅格图片对象。211个读取的输入文件(180baseline/test CSV、30training labeled CSV、分组JSON)SHA-256运行前后不变。源数据未复制为备份，也未修改。

图注与公式解释见METHODS.md、figure3_caption.txt、fig4_phase_space_caption.txt。投稿时仍需遵循目标期刊物理版式和统计报告要求；发表级导出不等于假说被证实。
