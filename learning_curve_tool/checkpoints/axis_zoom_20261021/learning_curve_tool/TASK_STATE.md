# Original Goal

Maintain the existing desktop participant-ID batch plotter with English six-panel academic figures and independent strength/angle components.
2026-10-20: rename the current condition to both, support legacy regular input, synchronize renamed source paths and refresh existing figures.

# Requirements

Both training and both baseline/test show strength and angle independently. Keep a–f panels, participant-ID outputs, variable actual trial counts and original desktop launcher. Missing/invalid components are not zero and do not remove the other component or trial alignment.

# Constraints

Plotting reads source CSVs only. The separately authorized one-time name migration changed labels/links, not numeric values or score versions. Old v1/v2 angle data must not be presented as v3 rescoring. No Git, no automatic commits or resets.

# Current Plan

Implemented, deployed and verified. Six current participant figures/statistics were regenerated from the renamed existing v2 CSVs. No pending batch or migration.

# Architecture / Important Decisions

learning_curves.py normalizes both/regular as one condition and refuses duplicate aliases for a stage. Nonempty MOLT4_results_v3/csv has priority; legacy result layouts remain supported. Component_figures keeps separate units/scales and aligned blocks. Invalid/unresolved blank values remain missing. Historical scalar inputs stay supported without fabricating components.

# Completed Work

Both UI/figure captions and file matching; canonical source path/SHA references; v3 preference; partial invalid component handling. Existing .deps/.tcl and launchers retained. Current 01–06 PNG/SVG/statistics and batch_report updated with old output backup. Original 1748 source rows and their numerical scores retained; both labels do not imply new endpoint angles.

# Files Changed

learning_curves.py, component_figures.py, verify_outputs.py, test_learning_curves.py, added test_both_alias.py; manual and this handoff. Updated ../learning_curves/01–06.png/.svg, statistics/01–06.json, batch_report.json. Source deployment/plot backups and manifests are recorded in MOLT4/upgrade_v2/angle_both_20261020/learning_deployment.json and plot_deployment.json.

# Tests / Verification Performed

16 regression tests PASS in candidate and installed tool. Regeneration 6/6: 278/271/356/290/286/267 actual rows. Independent verification of 6 participants and 57 source metrics: SHA256, scored counts, block boundaries, means and sample SD. 01/04 final figure images visually checked for both/single condition layout and labels. Copied outputs verified by SHA.

# Known Issues

Current figures still use the original v2 values/caps because numerical scores were intentionally preserved during rename. New angle rules require separate v3 batch analysis, not a label edit. Missing source components stay unfilled. Figures are descriptive; no significance or retention claim. Demo/component_preview/checkpoints are historical previews and backups.

# Remaining Work

None for this request. Do not silently recalculate or edit experimental CSVs from plotting code.

# Recommended Next Step

Use the existing root 绘制学习曲线.cmd and enter IDs. New v3 CSV output, when available, is selected before the legacy folder.

# Important Context for Next Session

This file is the sole learning tool handoff; D:/experiment/AGENTS.md applies. Keep start.cmd and local .deps/.tcl. Numeric source files and actual test results are the source of truth. The main scoring project has its own MOLT4/TASK_STATE.md; recorder has its own formal TASK_STATE.md.
