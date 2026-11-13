# Outlier batch tool

- Read HANDOFF.md for architecture and constraints.
- TASK_STATE.md in this directory is the sole current task-state entry for this tool; learning_curve_tool/TASK_STATE.md belongs to the separate learning-curve application.
- Never modify, delete or back up participant processed_csv source files. No Git repository or commits.
- Retained data are manually reviewed: ignore historical review flags in eligibility and plotting. The historical batch keeps its spline/Bonferroni diagnostic; the new robust pipeline uses Student-t likelihood and independent channel validity, as documented in the latest TASK_STATE section.
- Output flags must be adjacent to their measurement columns and contain only integer 0 or 1, never blanks. Zero means not flagged, including untested rows; explain this in reports.
- Preserve original CSV cell text, row count and UTF-8 BOM. Write derived files only to outlier_results.
- Regression checks: python -m unittest discover -s tools/outlier_batch -p test_outlier_batch.py (from workspace root).

- The robust learning/transfer analysis is the current primary pipeline. User update 2026-11-08: training outlier=1 MUST be excluded from every statistic and fit; other finite labeled training values are authoritative. Only evidence-based score clipping is censoring.
