# Billiards — motor learning research

30 participants; Both / Strength / Angle training groups. Source measurements and manual labels are preserved. Videos remain local and are excluded from Git. This repository is public by explicit researcher authorization (2026-11-14).

## Functional layout
| Location | Contents |
|---|---|
| data/participants/01..30/ | Participant source CSVs, authoritative labeled training, local videos |
| data/group_assignments.json | Original group assignments; analyses select IDs 01–30 |
| data/provenance/, data/fixtures/ | Preserved migration records and historical test CSVs |
| processing/preprocess/ | Historical signed-value preprocessing (writes data; do not rerun on protected sources) |
| processing/outlier_labeling/ | Historical OLS spline / Bonferroni diagnostic labeling |
| analysis/robust/ | Student-t location/scale splines and evidence-based censoring likelihood |
| common/ | Shared paths and publication data selection |
| plots/participant_learning/ | Per-participant robust mean/variance figures and desktop GUI |
| plots/baseline_transfer/ | Robust baseline–transfer comparisons |
| plots/publication/ | Figures 2–4: block dynamics, raincloud, participant covariance contours |
| plots/supplementary/ | Figures 5–7: paired effects, MSE decomposition, group contrasts |
| results/ | Existing figure sets, derived summaries and captions |
| tests/ | Tests separated by workflow |
| docs/maintenance/ | Original preservation evidence and old→new path mapping |
| HILD/ | Process, journal, scope and proposed decisions |

Root Python files are compatibility entry points; implementations reside in the packages above. Existing desktop and BAT launchers remain available. Run commands from this repository root:

```powershell
python -m plots.publication.dynamics
python -m plots.supplementary.batch
python -m plots.baseline_transfer.robust_comparison --help
python -m plots.participant_learning.app --help
```

## Methods and review
[Wiki](https://github.com/ayyyeeeee/Billiards/wiki) documents algorithms, filtering, input/output, captions and limitations by method. The Student-t likelihood pipeline differs from the descriptive normalized 10-shot blocks in Figure 2; a smooth fitted line is not evidence of identical models. SEM, trial SD, bootstrap confidence intervals and covariance contours represent different quantities. Scientific primary-method agreement remains [Issue #2](https://github.com/ayyyeeeee/Billiards/issues/2).

Current refactor scope: [Issue #5](https://github.com/ayyyeeeee/Billiards/issues/5). Work is proposed on a branch and is not merged automatically. Wiki explanations remain drafts pending researcher review. Overall progress authority: [TASK_STATE](tools/outlier_batch/TASK_STATE.md). Original audit paths in historical reports resolve through [relocation mapping](docs/maintenance/relocation_verification.json); historical reports are not silently rewritten as new results.

Regression suite: `python -m unittest discover -s tests -t . -p "test_*.py"`. Use the project import root.
