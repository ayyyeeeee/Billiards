> 2026-11-02 后续更新：当前主分析为 `run_robust_analysis.bat`（Student-t 似然、分别拟合均值/方差、真实截顶）。下面 OLS/Bonferroni 批处理说明作为历史异常标记工具继续适用，但新学习/迁移图不再硬删除这些标记。最新整体状态见 TASK_STATE.md，方法证据见 CENSOR_AUDIT.md 和 robust_validation.md。

# 台球运动学习实验——异常值批处理工具 (Outlier Batch Tool) 交接文档 (Handoff Document)

> **文档目的**：本文档供后续接手的工程师或大语言模型（如 GPT）快速理解本项目的设计背景、架构实现、数据流、统计学原理、已完成的验证工作及待扩展方向。

---

## 1. 项目概况与业务背景

本项目针对 **台球运动学习实验（140次击球/受试者）** 的连续时间序列数据进行统计异常值自动检测与标注。

- **根目录**：`D:\experiment`
- **受试者**：`01` 到 `30`，每个受试者对应一个独立编号文件夹。
- **训练模式（3种）**：
  1. `training_both_140shots`：角度与力度联合训练。
  2. `training_angle_140shots`：单纯角度训练。
  3. `training_strength_140shots`：单纯力度训练。
- **关联系统**：
  - 上游原始数据提取系统：已将清洗后的击球数据保存在各个受试者的 `processed_csv/` 目录中。
  - 下游可视化分析系统：`D:\experiment\learning_curve_tool\learning_curves.py`（其学习曲线绘制脚本会直接从本工具生成的 `outlier_results/labeled_csv/` 中读取标记后的 CSV，并在绘图计算时将标记为 `1` 的异常点置为 NaN 排除）。

---

## 2. 工具文件组织与运行方式

工具源码与批处理脚本位于：`D:\experiment\tools\outlier_batch\`

```text
D:\experiment\tools\outlier_batch\
├── run.bat              # Windows 双击启动脚本（自动检测/构建 venv 并运行）
├── outlier_batch.py     # 核心 Python 统计检测与批处理主程序
├── requirements.txt     # Python 依赖清单
├── README.md            # 工具说明文档（英文）
├── HANDOFF.md           # 本交接文档
└── logs\                # 批处理运行日志（自动按时间戳命名）
```

### 运行方式
1. 双击 `run.bat`，或在命令行运行：
   ```cmd
   cd D:\experiment\tools\outlier_batch
   python outlier_batch.py [受试者输入]
   ```
程序递归扫描每名受试者的 `processed_csv/`（包括 `processed_csv/csv/`），按训练模式关键字识别文件，允许文件名前缀；字段按列名读取。

2. 支持输入格式：
   - 单个受试者：`01` 或 `1`
   - 多个受试者：`01,02,05`
   - 连续范围：`01-30`
   - 全部受试者：`all`，或提示时直接回车（空输入/EOF 默认全部）

---

## 3. 核心统计学方法与算法流程

由于 140 次击球包含受试者的渐进学习过程（非平稳时间序列），不能直接采用基于均值/标准差的传统 3-sigma 检验。

### 详细步骤：
1. **通道独立拟合**：
   - 角度（`angle`）与力度（`strength`）严格独立建模，禁止混合数值。
   - 单一模式（如 `training_angle_140shots`）中未请求的力度通道自动跳过（0 eligible）。
2. **数据质量与参与检验条件（Eligibility Mask）**：
   - 仅对以下条件完全满足的点进行样条拟合：
     - 通道状态：`{channel}_status == 'scored'`
     - 评分完整：`score_complete == 1`
     - 通道有效性：`{channel}_valid == 1`
     - 留存数据已人工复核：忽略历史 `{channel}_needs_review` 和 `needs_review` 字段，不再因此排除观测。
     - 数值为有效有限浮点数（非 NaN/Inf；有效的 0 可以参与检验，未完成评分的占位值仍排除）。
   - **2026-11-02 新要求**：复核标志不影响检验，不直接决定异常。保留 scored、score_complete、valid 和有限数值条件。
3. **三次样条学习趋势拟合（Cubic B-Spline Regression）**：
   - 自变量为击球序号 `shot`。
   - 使用 `patsy.dmatrix("bs(x, df=df_spline, degree=3, include_intercept=True) - 1")` 构建三次 B 样条基底。
   - 默认自由度 $df = 6$（若有效观测数不足，动态调整为 $\min(6, n-2)$）。
   - 使用 `statsmodels.api.OLS` 估计趋势 $\hat{y}_i$，残差 $e_i = y_i - \hat{y}_i$。
4. **外部学生化残差（Externally Studentized Residuals）**：
   - 计算杠杆值（Hat matrix diagonal $h_{ii}$）。
   - 计算剔除第 $i$ 个观测后的残差方差：
     $$s_{(i)}^2 = \frac{\sum e^2 - \frac{e_i^2}{1 - h_{ii}}}{n - p - 1}$$
   - 计算外部学生化残差：
     $$t_i = \frac{e_i}{s_{(i)} \sqrt{1 - h_{ii}}}$$
5. **假设检验与多重比较校正**：
   - 基于自由度 $dof = n - p - 1$ 的 $t$ 分布计算双侧原始 $p$ 值：
     $$p_{\text{raw}} = 2 \times (1 - F_t(|t_i|, dof))$$
   - 采用 Bonferroni 方法校正（$m$ 为参与检验的有效点数）：
     $$p_{\text{adj}} = \min(p_{\text{raw}} \times m, 1.0)$$
   - 若 $p_{\text{adj}} < 0.05$，标记为统计异常候选（`1`）；否则标记为正常（`0`）。
6. **统计假设诊断**：
   - 残差正态性：Shapiro-Wilk 检验（$p < 0.05$ 时输出警告）。
   - 异方差性：Breusch-Pagan 检验。
   - 自相关性：Durbin-Watson 统计量（偏离 $1.5 \sim 2.5$ 时输出警告）。
   - 诊断结果完整记录在统计报告中。

---

## 4. 输出结构与文件规范

对受试者 `ID`，输出固定保存在：`D:\experiment\{ID}\outlier_results\`

```text
D:\experiment\{ID}\outlier_results\
├── labeled_csv\
│   └── {原文件名}_outlier_labeled.csv    # 增加了异常标记列的 CSV
├── reports\
│   ├── {原文件名}_report.txt             # 单文件详细检验报告与统计诊断
│   └── participant_{ID}_summary.txt       # 受试者所有文件的异常汇总
└── plots\
    ├── {原文件名}_angle_outliers.png      # 角度拟合曲线与异常标注散点图
    └── {原文件名}_strength_outliers.png   # 力度拟合曲线与异常标注散点图
```

### 严格格式规范（铁律）
1. **绝对保护原始文件**：
   - 严禁修改、覆盖、删除 `processed_csv/` 下的原始文件（程序内每次运行前后均通过 SHA-256 校验原始文件完整性）。
   - **禁止**在磁盘上擅自建立原始 CSV 的备份副本。
2. **列插入位置与命名**：
   - `strength_value` 紧邻后插入 `strength_outlier`。
   - `angle_value` 紧邻后插入 `angle_outlier`。
   - 不修改任何原列名和已有数值，不删除任何行。
3. **标记列取值规范**：
   - `1`：经 $t$ 检验并 Bonferroni 校正后 $p < 0.05$ 的统计异常候选。
   - `0`：未标记为统计异常，包括检验不显著、未请求通道、无有效测量、有效点不足或无法计算检验的情况；不能将 0 一概解释为已检验正常。
   - **标记列禁止空白**：`strength_outlier` 和 `angle_outlier` 每行必须为整数 `0` 或 `1`。跳过原因仍记录在报告中。
   - **Excel 与编码兼容**：CSV 采用 `utf-8-sig`（带 BOM）保存，避免 Excel 打开中文乱码；原始空单元格继续保留为空，不写入字符串 `"nan"`；标记列没有空值。原始列按文本读取并原样保留单元格内容。
4. **行数保留**：
   - 原始文件有多少行（通常为 140，部分受试者因硬件掉帧实际为 136、138、139），新 CSV 必须完全保留相同行数。

---

## 5. 旧版验证记录（修改前历史，非当前结果）

截至 2026-11-02，已对 `01` 到 `30` 共 30 个受试者完成全量运行与全面测试，状态为 **全部通过（30/30 Success，0 Errors）**。

### 检出异常分布现状（参考）：
- **角度异常**：在 13 名受试者中检测出 1~4 个异常击球（受试者 01, 02, 04, 07, 10, 11, 13, 17, 20, 21, 23, 26, 29）。
- **力度异常**：受试者 12 检出 1 个异常击球，其余受试者为 0。
- **未请求/不可检验通道**：单项训练（如 angle 模式）的 strength 通道正确识别为 0 eligible 并整列留空；受试者 19 因有效力度点仅 7 个（<15）正确跳过并留空。
- **自动化测试断言**：
  - 30 个受试者的新 CSV 行数与原 CSV 逐行一致。
  - 列位置紧邻校验通过。
  - 标记列值严格处于 `{'', '0', '1'}` 集合中。
  - 原始文件散列值前后完全无变化。

---

当前版本验证与工作状态见本目录唯一交接状态入口 `TASK_STATE.md`。上面的旧版异常数量及留空行为已被新要求替代。

## 6. 接手人（GPT）后续可修改/优化的任务清单

请根据科研需求选择以下方向进行后续改进：

### 任务方向 A：异常检测灵敏度与多重比较校正方法微调
- **现状**：目前采用非常保守的 Bonferroni 校正（$\alpha_{\text{Bonf}} = 0.05 / 140 \approx 0.000357$），因此力度通道仅检出 1 个异常点。
- **可选修改**：
  - 若需要提高检出灵敏度，可引入 **FDR（False Discovery Rate，Benjamini-Hochberg 过程）**：
    在 `_fit_channel()` 中增加 `method="fdr_bh"` 选项（可调用 `statsmodels.stats.multitest.multipletests`）。
  - 支持在命令行或配置文件中指定显著性水平 $\alpha$（如 $\alpha = 0.01, 0.05, 0.10$）。

### 任务方向 B：样条自由度（Spline df）与学习趋势拟合优化
- **现状**：目前使用固定的 6 自由度（$df = 6$）三次 B 样条。
- **可选修改**：
  - 增加基于 **AIC / BIC** 或 **交叉验证（Cross-Validation）** 的自适应自由度选择，自动在欠拟合与过拟合之间取得最佳平衡。
  - 在边界区域（第 1~5 次和最后 5 次击球）评估自然样条（Natural Cubic Spline）与 B 样条的边界杠杆值差异。

### 任务方向 C：可视化图表美化与定制
- **现状**：已生成 200 dpi PNG，包含灰点、蓝趋势线、红异常点、红色击球编号标注；已移除 Needs review 分类与橙菱形。
- **可选修改**：
  - 增加 $\pm 2$ 或 $\pm 3$ 倍标准差的置信带（Prediction Band / Confidence Envelope）。
  - 支持中英文图例或学术期刊投稿格式（如矢量图 PDF / SVG 导出）。

### 任务方向 D：生成全局汇总表（All-Participant Master Summary）
- **现状**：每个受试者在 `reports/participant_{ID}_summary.txt` 中有独立的汇总表。
- **可选修改**：
  - 在处理完全部受试者后，在 `D:\experiment\tools\outlier_batch\` 或指定路径下自动生成一个汇总全部 30 个受试者的 `all_participants_outliers_summary.xlsx` 或 `.csv`，统计每个受试者的异常击球总数、异常率及异常发生的阶段分布（前期、中期、后期）。

---

## 7. 给 GPT 的工作提示词（Prompt Template）

接手修改时，可将以下提示词直接发送给 GPT：

```text
你正在接手台球运动学习实验的异常值批处理工具（D:\experiment\tools\outlier_batch\）。
请仔细阅读 D:\experiment\tools\outlier_batch\HANDOFF.md 中的架构说明与约束条件。

核心铁律：
1. D:\experiment\{ID}\processed_csv\ 中的原始 CSV 文件属于只读源数据，严禁以任何方式修改、覆盖、删除，也不要建立备份副本文件夹。
2. 本工作区不是 Git 仓库，不要执行 git 提交或重置。
3. 异常标记列名必须为 strength_outlier 和 angle_outlier，紧邻原测量值列后插入，取值严格为 1 或 0，禁止空白，严禁写入 "nan"。
4. 保持 utf-8-sig 编码与完整的原始行数。

我的修改需求是：
[在此处输入具体修改需求，例如：将多重检验校正方法从 Bonferroni 改为 FDR-BH，或生成全局 30 个受试者汇总表格]
```
