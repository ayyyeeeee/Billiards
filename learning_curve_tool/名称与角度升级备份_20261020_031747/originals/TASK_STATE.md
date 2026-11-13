# Original Goal
Maintain an easy desktop batch plotter: enter participant IDs, detect training condition and variable trial counts, output English academic figures named by ID.

# Requirements
Regular CSVs now contain strength_value and angle_value, with value intentionally blank. Show BOTH components in regular training and regular baseline/test; retain separate strength/angle conditions. Preserve six lettered panels and captions, no review-point marks or bottom disclaimer paragraph.

# Constraints
Read-only source CSVs. Do not pool distance and degrees. Missing component values are not zeros and must not delete the other component. Keep trial/block alignment and report finite n.

# Current Plan
Completed: component-aware loading, aligned blocks, stacked regular subplots, compatibility tests, full batch regeneration and visual verification.

# Architecture / Important Decisions
Main application retains Tk UI/CLI and legacy plotting. New `component_figures.py` handles component-aware six-panel figures. `Series.components` retains strength/angle with aligned original shot arrays; unavailable scores are NaN internally and null in exported block statistics. New outputs use JSON schema_version=2, training_components and per-condition/per-metric comparisons. Components have separate axes, units, maxima, n, means and SD. Recorded trials are counted once, not once per component. Old scalar regular remains supported; mixed scalar/split baseline-test schemas are rejected.

# Completed Work
2026-10-13 recovery: inspected current files and 42 CSVs for participants 01–06. Old 8 regression tests pass, but old loader rejects current regular CSVs because value is blank. No AGENTS.md/TASK_STATE.md existed. Git status/diff unavailable because workspace is not a Git repository.

Implementation, verification and requested goal are complete. Regular training a–c and regular baseline/test d each show both components. Independent strength/angle conditions stay in e/f. No review marks or sensitivity lines were reintroduced. Desktop ID input, variable trial counts and ID-named outputs retained. All 01–06 PNG/SVG/statistics updated from current CSVs. Manual updated.

# Files Changed
Modified learning_curves.py, test_learning_curves.py, 使用说明.md. Added component_figures.py, verify_outputs.py, this handoff, workspace AGENTS.md. Updated ../learning_curves/01–06.png and .svg, statistics/01–06.json, batch_report.json. Pre-edit code/test/manual copies in checkpoints/20261013_before_components (small reference snapshot, not full backup). Launcher unchanged.

# Tests / Verification Performed
2026-10-13: 12 tests pass, including old schema, variable counts/singleton tails, rounded caps, GUI generation with new split schema, aligned component blocks, all-missing block, independent angle/strength units, malformed partial schema rejection and serialized nulls.

Batch --all completed 6/6: 01 regular 278 trials; 02 regular 271; 03 regular 356; 04 angle 290; 05 strength 286; 06 strength 267. All six final PNGs visually inspected. Axis labels wrapped to prevent collisions within stacked plots.

Independent verify_outputs.py passed for 6 participants, 57 source metrics: checks all source SHA256 hashes against output records, total/scored counts, baseline/test means, training/test block boundaries, means and sample SD via standard-library statistics. Each source file's hash is in output statistics JSON.

Verification command: bundled Python at C:/Users/LHW/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe with test_learning_curves.py -q, learning_curves.py --all, and verify_outputs.py.

Code SHA256: learning_curves.py 9A8A1868BBDC2CEE491CB53A7BCC1E840CB9CB4F295AE984C3D843B8126960A4; component_figures.py F785273FE3F87A768C81B7578C0B31574217A0A529CB9191A15C99987E047E7A.

# Known Issues
No known blocking implementation issue. Unresolved scores exist in source data and are represented by scored/recorded n; no imputation is performed. Figures remain descriptive, not significance/retention tests. Distance units remain recorded units. Legacy demo/component_preview files are prior previews, not current deliverables. No Git repository or full workspace backup exists.

# Remaining Work
None for this request.

# Recommended Next Step
Use existing root 绘制学习曲线.cmd and enter IDs. For future changes, verify current source CSVs and this implementation before editing; rerun relevant regression and output checks.

# Important Context for Next Session
Original UI/start.cmd and local .deps/.tcl must keep working. Default root is parent of tool directory. Source of truth is files/tests, not previous chat. No Git backup exists.
