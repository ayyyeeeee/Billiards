> 2026-11-02 后续更新：当前主分析为 `run_robust_analysis.bat`（Student-t 似然、分别拟合均值/方差、真实截顶）。下面 OLS/Bonferroni 批处理说明作为历史异常标记工具继续适用，但新学习/迁移图不再硬删除这些标记。最新整体状态见 TASK_STATE.md，方法证据见 CENSOR_AUDIT.md 和 robust_validation.md。

# Billiard Training — Outlier Detection Batch Tool

Detects statistical outliers in 140-shot billiard motor-learning training data
using externally studentized residuals with Bonferroni-corrected t-distribution
p-values.

## Quick start

Double-click **`run.bat`** and enter participant IDs when prompted:

| Input | Effect |
|---|---|
| `01` or `1` | Process participant 01 |
| `01,02,05` | Process multiple participants |
| `01-30` | Process a range |
| `all` or Enter without input | Process all 30 participants |

## Method

1. A cubic B-spline regression (df = 6) captures the learning trend across 140 shots.
2. Externally studentized residuals are computed for each observation.
3. Two-sided p-values from the t-distribution are Bonferroni-corrected.
4. Corrected p < 0.05 flags a shot as a statistical outlier candidate.
5. Angle and strength channels are fitted **independently**.

## Output

Results are saved to `D:\experiment\{ID}\outlier_results\`:

- **`labeled_csv\`** — Original data + `angle_outlier` / `strength_outlier` columns
- **`reports\`** — Per-file statistical reports and participant summary
- **`plots\`** — Outlier detection scatter plots (PNG, 200 dpi)

## Outlier column values

| Value | Meaning |
|---|---|
| `1` | Statistical outlier candidate (Bonferroni p < 0.05) |
| `0` | Not flagged, including untested rows or skipped channels |

Flags are always 0 or 1, never blank. A zero does not necessarily mean a
valid statistical test was performed; see reports for eligibility and skip reasons.

## Requirements

- Python 3.9+
- numpy, pandas, scipy, statsmodels, matplotlib, patsy

The batch file auto-installs dependencies into a local `.venv` on first run
if the system Python does not already have them.

## Notes

- Original CSVs are **never** modified. Integrity is verified via SHA-256.
- Retained data have been manually reviewed: historical `needs_review` and
  channel review flags are ignored. No Needs review plot category is generated.
- Scored status, score completion, channel validity and finite measurements
  are still required independently for each channel.
- Original cell text, row count and UTF-8 BOM encoding are preserved.
- Assumption diagnostics (normality, heteroscedasticity, autocorrelation)
  are reported; warnings are logged when assumptions are violated.

Training files are discovered recursively under each participant's `processed_csv/`
(including `processed_csv/csv/`). Filename prefixes are allowed; matching uses
`training_(angle|strength|both)_140shots`. Columns are accessed by name.
