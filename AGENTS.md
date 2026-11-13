# Workspace instructions

- Participant folders are source data. Do not edit CSVs during plotting work.
- The learning-curve application is `learning_curve_tool/learning_curves.py`.
- Its single authoritative handoff is `learning_curve_tool/TASK_STATE.md`.
- Keep English academic figures, a–f captions, participant-ID filenames and the existing desktop launcher.
- On 2026-11-13 the user authorized Git, code/CSV uploads, Issues, PRs and Wiki for the now-public `ayyyeeeee/Billiards` repository. Work on branches and present PRs; do not merge without researcher approval. Never reset source data. Videos remain local and must not be deleted or uploaded.

2026-10-20 user-authorized one-time regular→both filename/metadata migration is complete. IDs, group membership, numeric scores and video bytes are preserved. Plotting remains read-only. Legacy names in backups/provenance are historical; do not rerun migration or randomize assignments.

Robust learning/transfer task handoff: `tools/outlier_batch/TASK_STATE.md` (latest section); learning-curve application history remains in its own handoff. Root `plot_baseline_vs_transfer.py` produces group comparisons. Shared Student-t/censor helpers are under `tools/outlier_batch/`.

New three-figure entry: `plot_publication_figures.py` with `publication_raincloud.py` and `publication_phase_space.py`; output `publication_figures/`. Its training filter is strictly scored AND outlier!=1 (2026-11-08 request). Overall handoff remains `tools/outlier_batch/TASK_STATE.md`, latest section.

Supplementary estimation/decomposition entry: `plot_supplementary_analyses.py` / `run_supplementary_analyses.bat`; output `supplementary_figures/`. Reuses the publication loader; Figures5-7 concern baseline/test, participant-paired MAE changes, observed MSE decomposition and direct between-group contrasts. Bootstrap CIs are exploratory, pointwise, not Tukey-adjusted. Overall handoff remains `tools/outlier_batch/TASK_STATE.md`.

## HILD progress management

Use [HILD local configuration](HILD/LOCAL.md) and the [HILD process](HILD/process.md), subject to project rules and explicit user authorization. Git/Issues/PRs and the separate Wiki Git repository are now authorized. Wiki website availability is verified separately; hooks remain disabled. Never change visibility or upload video without new authorization.

At session start, read the latest overall [TASK_STATE](tools/outlier_batch/TASK_STATE.md), the newest dated file in [HILD journal](HILD/journal/), and use [.agents/skills/hild-orient/SKILL.md](.agents/skills/hild-orient/SKILL.md). Use `hild-journal` at milestones; keep the existing TASK_STATE as the sole overall progress authority. `HILD/plan.md` is only a pointer. Record implementation, verification, scientific acceptance, and researcher understanding separately. Only the researcher may confirm understanding or accept proposed scientific decisions.

## 2026-11-14 physical module organization (current)
User explicitly confirmed PUBLIC GitHub publication. Scope #5 authorizes physical organization, method-level Wiki and obsolete tracker cleanup. No merge without researcher approval.
Data live in data/participants/01..30; group configuration in data/group_assignments.json. Do not rewrite CSVs or upload/delete videos. Historical audit paths resolve via docs/maintenance/relocation_verification.json.
Implementations live in processing/, analysis/robust/, plots/, common/. Original entry filenames are compatibility launchers, not independent implementations. Derived figure outputs live in results/. Tests live in tests/; preserved historical test CSVs in data/fixtures/.
Overall authority remains tools/outlier_batch/TASK_STATE.md, latest section. App history remains learning_curve_tool/TASK_STATE.md; these are deliberately retained for continuity. Runtime dependencies remain local in learning_curve_tool/.deps and .tcl.
Different eligibility/statistical methods are preserved, not silently unified by this refactor. Issue #2 remains unresolved. Wiki pages describe the refactor branch as draft; only researcher may mark understood.
