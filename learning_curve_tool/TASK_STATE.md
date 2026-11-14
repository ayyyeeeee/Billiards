# Current state — 2026-11-08 (supersedes history below)

## Original Goal
Apply user's authoritative training outlier labels and improve publication readability, layout, legends and caption delivery.

## Requirements / Constraints
Training uses labeled_csv only; outlier=1 is discarded per channel, all other finite labeled training values included. Baseline/test retain processed_csv routing. Preserve original shot positions, actual row counts, missing values and all source bytes. No Git repository, commits or reset. Existing desktop entry remains.

## Architecture / Important Decisions
load_series recognizes authoritative training label columns and masks flags regardless of optional exclude_outliers argument; historical status/valid/review do not override user-reviewed non-flagged training values. Missing measurements still cannot be fitted. Processed-data routes now fail clearly if labeled training is absent rather than fall back. Component figure uses an axis-exterior red rug (x=data, y=axes fraction -0.018), never a zero-error point. If all included training components have no confirmed censoring, top row is a/b across full width; c omitted, d/e/f identifiers preserved. For both with some censoring, c remains component-specific. Censor bars use same confirmed-censor evidence as likelihood. Canvas 12 x 8.5 inches; long captions external ID_caption.md and JSON. Legend explicitly identifies model mean +/- trial SD, not a confidence interval. Full-stage t comparisons unchanged.

## Completed Work / Files Changed
learning_curves.py, component_figures.py, test_learning_curves.py, test_signed_outliers.py; added this directory's AGENTS.md. All 30 learning_curves PNG/SVG and statistics JSON regenerated; 30 Markdown captions exported. JSON schema 4 contains captions, censor_panel_visible and exact fit n_obs. Source audit at ../tools/outlier_batch/logs/training_source_audit_20261108.csv.

## Tests / Verification Performed
27 regression tests passed including GUI generation, new mask counts/rug coordinates/SD legend, source routing and variable counts. All 40 actual training fits succeeded with n_obs matching finite nonflagged observations. All 10 angle-only participants omit c. 240 processed/labeled CSV SHA-256 hashes unchanged versus pre-edit manifest. Visually checked 04 and mixed/censored layouts. Total source trials: 01=251,02=253,03=259,07=256,09=258,19=259; others260. No padding to260.

## Known Issues / Remaining Work
No remaining learning-app implementation work. Fixed-nu model and SD interpretation limitations persist; this is not a treatment-effect significance analysis. Historic validation reports that included flagged observations are historical and cannot be cited as validation of this changed selection.

## Recommended Next Step / Important Context for Next Session
Use existing desktop launcher or --all; inspect Markdown captions beside figures. Overall group-figure revision is documented in ../tools/outlier_batch/TASK_STATE.md and publication report. Do not restore the old retained-outlier or y=0 mark behavior from the history below.

---
# Historical handoff (superseded where conflicting)

# Original Goal

Maintain the existing desktop participant-ID batch plotter with English six-panel academic figures and independent strength/angle components.
2026-10-20: rename the current condition to both, support legacy regular input, synchronize renamed source paths and refresh existing figures.
2026-10-21: improve acquisition panel readability. The user explicitly chose to enlarge the main point cloud and label high values separately rather than forcing every observation onto the same large y range.
2026-11-02: support signed directional performance data (positive/negative values, zero target line) and route data sources to `processed_csv` for baseline/test and `outlier_results/labeled_csv` for training, filtering marked outliers (`angle_outlier=1` / `strength_outlier=1`) while preserving shot coordinates and trial alignment.
2026-11-02 (follow-up): plot red dots on the x-axis (`y=0`) at outlier positions in panel a to visibly mark excluded outlier trials; explain the red dot cue in the top figure legend and bottom panel (a) caption.

# Requirements

Both training and both baseline/test show strength and angle independently. Keep a–f panels, participant-ID outputs, variable actual trial counts and original desktop launcher. Missing/invalid/outlier components are not zero and do not remove the other component or trial alignment.

Data sources:
- Baseline (3 conditions: both, strength, angle; 10 shots each) and Test (3 conditions: both, strength, angle; 30 shots each) load from `{ID}/processed_csv/*.csv`.
- Training (140 shots or variable actual trials, e.g. 136, 138, 139) loads from `{ID}/outlier_results/labeled_csv/*_outlier_labeled.csv`.
- Legacy `MOLT4_results_v3/csv` and `MOLT4_results/csv` remain supported as a fallback when `processed_csv` is absent.

Signed performance & outlier handling:
- Values can be negative and positive. 0 represents on-target performance.
- A horizontal reference zero-line (`y=0`, dashed) is included in performance panels (a, and d–f).
- Subtitle dynamically states "Values closer to zero indicate better performance" for signed datasets.
- Rows labeled `angle_outlier=1` or `strength_outlier=1` in training CSVs are excluded from calculation (treated as NaN for that component) while preserving shot positions.
- Outlier trials are marked with a distinct red dot (`#d62728`, s=18) on the x-axis (`y=0`) in acquisition panel a.
- The red dot marker is clearly explained in the top figure legend ("Outlier on x-axis (excluded)") and in the panel a caption ("Red dots on the x-axis (y = 0) mark outlier trials excluded from calculation.").
- Rows with unresolved/invalid status (e.g. unconfirmed stops) do not trigger false conflicts and remain excluded from scored means.
- Variable actual shot counts across training and test stages are handled dynamically from CSV data rows without requiring 140/30/10 shots.

# Constraints

Plotting reads source CSVs only. Do not edit, rescore, or delete CSVs from plotting code. No Git commits or resets.

# Architecture / Important Decisions

- `learning_curves.py`:
  - `Series`: includes `outlier: np.ndarray` (boolean array) to record which shots were flagged as outliers.
  - `discover_ids`: checks for numeric participant folders with `processed_csv` or legacy `MOLT4_results`.
  - `_collect_participant_files`: routes baseline and test files to `processed_csv` and training to `outlier_results/labeled_csv`.
  - `load_series`: parses signed values, checks component-specific outlier flags (`strength_outlier`, `angle_outlier`) as well as `status in ('unresolved', 'invalid', 'not_requested')`, marking them as missing (`NaN`). Capping checks absolute tolerance against absolute limits (`abs(abs(value) - abs(maximum)) <= tolerance`).
  - `load_participant`: loads all 7 files per participant; accepts optional `legacy=True` for historical regressions.
  - `bounds`: accommodates negative and positive values with proportional padding around `[min(0., min_val), max(0., max_val)]`.
  - Figure subtitle: dynamically toggles between "Values closer to zero indicate better performance" and "Lower values indicate better performance".
  - Zero reference line: adds dashed `y=0` line in error panels (a, d, e, f).
  - Outlier red dots: plots red dots on the horizontal x-axis line (`y=0`) for outlier shots in panel a.
- `component_figures.py`:
  - Implements the signed error zero-line, outlier red dots on `y=0`, top legend entry, and caption explanation for component figures.
- `axis_views.py`:
  - Preserves broken-axis separation logic on positive tails; cleanly declines split on signed negative observations (`np.any(y < 0)`), ensuring complete honest views without distorted dual regions.

# Completed Work

2026-11-02 milestone:
- Migrated data routing: baseline & test to `processed_csv`, training to `outlier_results/labeled_csv`.
- Implemented outlier exclusion for `angle_outlier=1` and `strength_outlier=1`.
- Added red dots on the x-axis (`y=0`) at outlier trial positions in acquisition panel a.
- Added red dot explanation in the top figure legend ("Outlier on x-axis (excluded)") and caption ("Red dots on the x-axis (y = 0) mark outlier trials excluded from calculation.").
- Supported signed values throughout plotting, bounds calculation, zero-line display, and dynamic subtitle.
- Verified all 30 participants (10 both, 10 angle, 10 strength) across all 7 stages.
- Created `test_signed_outliers.py` verifying data loading, outlier masking, red dot legend/caption cues, signed values, variable trial counts, and 30-participant coverage.
- All 27 regression and new unit tests PASS.

# Files Changed

- `learning_curves.py`
- `component_figures.py`
- `test_axis_views.py`
- `test_signed_outliers.py`
- `使用说明.md`
- `TASK_STATE.md` (this handoff)

# Tests / Verification Performed

- 27 tests PASS in test suite (`test_learning_curves.py`, `test_axis_views.py`, `test_both_alias.py`, `test_signed_outliers.py`).
- Participant 01 (both), 04 (angle), 05 (strength) verified via `process_one` and CLI.
- Verified that outlier shots are marked with red dots on the x-axis (`y=0`): 01 angle has red dots at shots 64 and 136; 04 angle has a red dot at shot 116; 05 strength has a red dot at shot 18.
- Checked outlier exclusions: 01 angle training excludes shots 64 and 136 (138/140 scored), keeping strength scored at shot 64 (139/140 scored).
- Checked variable counts: 07 (136 shots), 09 (138 shots), 19 (139 shots) correctly handled.

# Recommended Next Step

Run `绘制学习曲线.cmd` or `python learning_curves.py --all` to generate all 30 participant figures to `learning_curves/`.

# 2026-11-02 superseding robust-analysis update
Earlier outlier-exclusion/ten-trial display descriptions are historical. Current authoritative overall task handoff: ../tools/outlier_batch/TASK_STATE.md (latest section). Current component figures use Student-t location/log-scale spline training fits, retained valid historical outliers, true evidence-based censor likelihood, separate variance panel, and full-stage Student-t baseline/test summaries. Source loading now respects per-channel validity independently. Historical raw blocks remain in JSON; schema_version=3. All 30 participant figures regenerated; 27 app regression tests pass including GUI generation. start.cmd prefers a complete installed scientific Python stack (bundled runtime lacks scipy). No source CSV edited. Limitations and shared model verification are documented in the authoritative overall handoff.
