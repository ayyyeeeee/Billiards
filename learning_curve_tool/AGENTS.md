# Learning-curve application

- Application handoff: TASK_STATE.md. Overall learning/transfer revision entry: ../tools/outlier_batch/TASK_STATE.md (latest dated section).
- Source CSVs are read-only; do not back up, edit or regenerate labeled CSVs as part of plotting.
- Baseline/test read participant processed_csv; training must read outlier_results/labeled_csv when processed_csv is present. Never silently fall back to raw training.
- User instruction 2026-11-08 supersedes previous robust-retention policy: exclude training channel outlier=1 from every statistic and fit. Other finite labeled training values are included regardless of historical status/valid/review. Missing values stay missing; preserve shot alignment and actual row counts.
- Excluded trial marks use axis-exterior rug, never y=0. No invented measurement values.
- Omit empty censor panel and expand a/b; preserve d/e/f task identities. Export long captions to per-participant Markdown.
- Shading is model mean +/- trial SD, explicitly not 95% confidence interval.
- Test: python -m unittest discover -s learning_curve_tool -p test_*.py from workspace root.
