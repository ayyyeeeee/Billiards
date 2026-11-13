# Billiards — 台球运动学习实验

30名受试者，Both、Strength、Angle三组。此仓库包含数据预处理、异常标记、学习曲线、迁移分析、论文插图与HILD工作流程。

## 按功能使用

| 分类 | 程序与资料 | 运行入口 / 输出 |
|---|---|---|
| 实验数据 | [01](01/)–[30](30/)，各自的 processed_csv、outlier_results、测量来源 | 原始CSV只读；训练优先使用labeled_csv |
| 数据预处理 | [process_experiment_csv.py](process_experiment_csv.py)、[分组](group_assignments.json) | 修改前先检查当前参数与数据规则 |
| 异常标记与稳健模型 | [tools/outlier_batch](tools/outlier_batch/) | 历史异常标记器与Student-t/censor helpers，不能混同 |
| 单人学习曲线桌面应用 | [learning_curve_tool](learning_curve_tool/) | `learning_curve_tool/start.cmd`；输出 [learning_curves](learning_curves/) |
| 基线与迁移比较 | [plot_baseline_vs_transfer.py](plot_baseline_vs_transfer.py) | 输出 [baseline_vs_transfer_robust](baseline_vs_transfer_robust/) |
| 核心论文图2–4 | [plot_publication_figures.py](plot_publication_figures.py) | `run_publication_figures.bat`；[输出](publication_figures/) |
| 补充论文图5–7 | [plot_supplementary_analyses.py](plot_supplementary_analyses.py) | `run_supplementary_analyses.bat`；[输出](supplementary_figures/) |
| 测试与校验 | 根目录 `test_*.py`、`verify_*.py`，各模块内测试 | `python -m unittest discover`；专项测试见交接 |
| 整理与来源证据 | [docs/maintenance](docs/maintenance/)、[assignment_backups](assignment_backups/) | CSV与迁移证据保留，旧预览图和字节码缓存已清理 |
| HILD协作 | [HILD/LOCAL.md](HILD/LOCAL.md)、[当前进度](tools/outlier_batch/TASK_STATE.md) | [Issues](https://github.com/ayyyeeeee/Billiards/issues)、[PR](https://github.com/ayyyeeeee/Billiards/pulls)、[Wiki](https://github.com/ayyyeeeee/Billiards/wiki) |

按上述功能分区导航，保留已被脚本、桌面启动器和交接文档引用的真实路径，避免移动数据后破坏程序。历史CSV即使位于测试/旧备份目录也全部保留；不要按目录名批量删除。

## 运行环境

Python环境安装 `python -m pip install -r requirements_publication.txt`。桌面学习曲线需要可用的Tk。机器上的 `.deps`、`.tcl` 是当前桌面程序的本地兼容依赖，保留本地但不上传第三方运行库。命令从仓库根目录执行。

## 数据保护与上传范围

研究者于2026-11-13将仓库改为私有；代码和全部实验CSV上传至私有仓库。视频不上传，也不删除，见 [视频清单](docs/maintenance/videos.json)。日志保留本地；排除日志不代表删除。仓库不是原始视频备份。请勿在未获明确授权时改回公开。

清理前有2,523个CSV、210个视频。CSV逐文件SHA-256保护，视频路径/大小/修改时间保护，见 [保护清单](docs/maintenance/protected_files.json) 和 [清理报告](docs/maintenance/cleanup_report.json)。

## 科学方法的重要区别

单人稳健学习曲线使用Student-t均值/尺度样条与删失处理。核心Figure2使用10球分块的归一化MAE/SD和指数拟合；Figures3–7主要是观测分数统计、ANOVA/Tukey或Bootstrap。它们不是同一种分析。主分析的选择及不同入口的筛选规则仍需研究者确认，详见 [当前交接](tools/outlier_batch/TASK_STATE.md)。

## HILD流程

Issues记录目标与边界，PR提供实现和验证供审核，Wiki保存解释与理解状态。只有研究者可以确认“已理解”或批准合并；代码导出完成不等于科学结论已成立。
