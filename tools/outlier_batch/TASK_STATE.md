# Original Goal
Remove Needs review exclusion/display from the outlier batch tool because retained data have already been reviewed. Both outlier columns must always be 0 or 1.

## Requirements
Read-only processed_csv; no source backups; no Git operations. Preserve original cells, rows, UTF-8 BOM and adjacent strength_outlier/angle_outlier columns.

## Constraints
Keep channels independent and existing cubic spline, externally studentized residuals and Bonferroni thresholds. Keep scored, score_complete, valid and finite-value eligibility checks.

## Current Plan
Complete: implementation, regression checks, all-participant regeneration and integrity verification.

## Architecture / Important Decisions
Historical channel-specific and generic review flags are ignored. They are preserved unchanged in exported original columns. Eligible reviewed observations now participate in fitting. Only statistically significant results get 1; all other rows get 0, including skipped/undefined tests. Reports document that 0 does not imply successful testing. Plot ineligible category remains for other eligibility failures; Needs review category is removed. Original cell text is read separately for export to avoid numeric reformatting.

## Completed Work
Changed eligibility, binary output defaults, plotting and reporting. Regenerated CSVs, reports and plots for participants 01–30 on 2026-11-02. No source backups created.

## Files Changed
outlier_batch.py, README.md, HANDOFF.md; added test_outlier_batch.py, AGENTS.md, TASK_STATE.md. Derived files refreshed under each participant's outlier_results. Verification evidence under logs.

## Tests / Verification Performed
- Three unittest cases passed: review-flag invariance and known injected outlier detection; invalid/skipped channel binary defaults; CSV preservation, BOM, adjacency and absence of review legend.
- All-participant batch: 30 successes, 0 errors (logs/outlier_batch_20261102_154739.log; logs/binary_flags_rerun.txt).
- All 210 processed_csv SHA-256 hashes unchanged (logs/source_integrity_before.json contains hashes only, no source copies).
- 30 output CSVs, 4193 rows, 28 flags equal to 1 across both channels. Verified every original cell and row against sources, both flag columns strictly 0/1 and adjacent, BOM present (logs/binary_flags_verification.txt).
- Visually inspected regenerated participant 03 strength figure: review category absent, trend and remaining ineligible category rendered correctly.

## Known Issues
Unrequested/invalid/unscored rows remain untested and receive 0 by the requested binary convention. Reports retain eligibility counts and skipped reasons. Old detection counts in HANDOFF section 5 are explicitly historical.

## Remaining Work
None for this request.

## Recommended Next Step
Use run.bat as before for subsequent batches. Do not rerun unrelated filename/data migrations.

## Important Context for Next Session
This workspace is not a Git repository. Verify actual files and source hashes directly. HANDOFF.md holds architecture; this file is the sole current task-state document for outlier_batch. The learning-curve application's handoff is separate and was not changed.

## Follow-up: launcher input and nested discovery (2026-11-02)
- User reported `No input provided. Exiting.`. Code inspection confirmed this was the blank-input branch, before file discovery.
- Empty input or EOF now selects all participants; explicit participant selections remain supported. run.bat continues calling the same Python entry point unchanged.
- Discovery now recurses under processed_csv, supporting nested csv directories and prefixed filenames.
- Read all 30 actual training CSV schemas before the change: three training modes, 60–90 columns. Current sources are directly under processed_csv; field lookup is by name.
- Five unittest cases passed, including new nested discovery and blank/EOF default tests; existing reviewed-data/binary-output tests still pass.
- No actual desktop double-click verification performed. Input dispatch tested with mocks; no need to regenerate unchanged statistical results for this discovery/input-only change.
- Follow-up complete; original completed goal remains intact.

## New Original Goal: supervisor feedback / robust learning and transfer (2026-11-02)
Implement Student-t observation likelihood, separate smooth mean/variance, evidence-based true censor likelihood, and readable baseline/post-test plots; diagnose old noisy ten-trial summaries without altering sources or deleting observations to create effects.

## Requirements / Constraints
Retain signed values, original 210 processed CSVs, row counts and independent channels. Historical binary flags remain 0/1 and unchanged but are no longer automatic deletions in the new robust analysis. Fixed nu=5 and smoothing penalty=1 are disclosed assumptions, not effect-driven tuning. Unresolved/invalid channels excluded independently; generic score_complete is only fallback if channel status absent.

## Current Plan / Completed Work
New robust_model.py implements penalized Student-t mean/log-scale splines and constant stage fits; censoring.py uses value/maximum/uncapped evidence and exact signed bounds. learning_curve_tool now renders spline mean, separately modelled variance, full-stage t baseline/test mean +/- model SD. Old arithmetic block summaries retained in JSON. Root plot_baseline_vs_transfer.py uses consistent t stage fits and zero-safe log variance axes, retains raw moments in CSV. Historical outlier flags remain visible but valid extremes participate in robust likelihood. New run_robust_analysis.bat regenerates both output sets. No reset-card operation was performed; no such tool is available in this session.

## Architecture / Important Decisions
Shared model and censor helpers live here. Statistical fitting uses all valid scored observations, including old flagged points. The historical OLS/Bonferroni outlier_batch.py remains available as a diagnostic comparison and its binary CSV contract is unchanged; it does not implement the new primary analysis. Nu=5 gives finite variance scale^2*5/3. Censored strength values come from capped motion-model predictions, not measured final stops; interpretation concerns recorded scores. Mean uncertainty is not the plotted model SD. These are descriptive participant fits, not confirmatory treatment-effect inference.

## Files Changed
Added robust_model.py, censoring.py, their tests, validate_robust_model.py, CENSOR_AUDIT.md, robust_validation.json/md, run_robust_analysis.bat. Updated learning_curve_tool/learning_curves.py, component_figures.py, start.cmd and regression tests; plot_baseline_vs_transfer.py and root test_baseline_vs_transfer.py. Documentation updated. Outputs learning_curves/01..30.png/svg/statistics, baseline_vs_transfer_robust/PNG/PDF/CSV. No Git repository; no commits/reset or source copies.

## Tests / Verification Performed
27 learning regression tests, 12 outlier/model/censor tests and 3 transfer tests pass. Real batch: 30/30 figures, 40/40 training fits and 240/240 phase fits successful; training censor count 158. Entire source manifest (210 CSVs) unchanged by SHA-256, verified logs/final_robust_verification.txt. Inspected regenerated 04 learning plot and group primary plot. Scientific dependency mismatch resolved by preferring installed complete stack; start.cmd retains GUI entry and prefers system Python with scipy/pandas/matplotlib, because bundled desktop Python lacks scipy. GUI generation is covered by regression test; literal desktop shortcut double-click not manually exercised.

## Known Issues / Remaining Work
No remaining implementation work for current request. Inference limitations: fixed nu/smoothing sensitivity; baseline samples around 10; no propagation of stage-fit uncertainty to group SEM or exploratory CSV paired tests; residual serial dependence not explicitly modelled. Statistical outlier labels in old batch are historical diagnostics, not new model-tail p-values. Do not equate smoother curves or improved predictive fit with proven learning effects. See robust_validation.md for final sensitivity/holdout evidence.

## Recommended Next Step / Important Context
Use run_robust_analysis.bat for all robust figures; existing learning launcher also produces new component figures. Read this latest section before older completed tasks. This file is the sole overall handoff for the robust-analysis task; learning_curve_tool/TASK_STATE.md keeps its application-specific history and links here. Source truth is code/results/tests, not earlier outdated flag-removal descriptions.

Final holdout verification now uses independent channel eligibility consistent with figures: interleaved 200/200 comparisons; blocked 199/200 (one failed comparison excluded and disclosed). Overall report: ROBUST_ANALYSIS_REPORT.md. Obsolete automation-4 removed after completion.

## 2026-11-08 publication and authoritative-label revision (supersedes earlier retention rule)
Original Goal: improve group journal layout and participant plots; exclude user-authoritative training outlier=1 from all statistics and fits. Requirements: source CSV read-only, actual trial counts, labeled training only, no y=0 fabricated outlier positions, no empty censor panel, external captions and precise SD label.
Completed: learning app updated and all30 regenerated; group plot split into two180x170mm2x2 figures plus MAE with insets, signed symmetric shared limits, external three-rule statistics. Core change excerpts and full evidence: ../../baseline_vs_transfer_robust/CORE_CHANGES.md and REVISION_REPORT.md. Source code plot_baseline_vs_transfer.py, test_baseline_vs_transfer.py, learning_curve_tool/learning_curves.py/component_figures.py/verify_outputs.py and tests. Shared statistical model unchanged.
Verification: 27learning+5group tests pass; all40 training fits successful with correct retained counts; independent verification280 source metrics; all240CSV hashes unchanged vs logs/plot_revision_20261108_sources.json. Source audit CSV logs/training_source_audit_20261108.csv. PNG/PDF physically sized and inspected, captions exported. No Git repository.
Remaining: none for this request. Prior robust validation used different inclusion rules and is historical. Existing inference limitations persist. App-specific current handoff remains learning_curve_tool/TASK_STATE.md. Do not restore earlier flagged-data retention policy. Use new fig1a/fig1b outputs rather than preserved tall historical plots.

## 2026-11-08 new three-figure pipeline (separate from previous plotting revisions)
Original Goal: produce Figures2 learning/variability,3 transfer raincloud ANOVA/Tukey,4 joint phase-space for30 participants. Latest new-pipeline selection rule: status=scored AND outlier!=1; this supersedes the earlier all-finite rule for this new entry point. Existing earlier plotting programs were not rewritten in this task.
Requirements: group_assignments.json IDs01-30 authoritative,180baseline/test processed files and30labeled training files; no source writes; OkabeIto specified colors; requested physical dimensions and300DPI/vectorPDF.
Architecture: new root plot_publication_figures.py loads audited data and drawsFigure2; publication_raincloud.py drawsFigure3; publication_phase_space.py drawsFigure4. Different training units require matched-task baseline-RMS normalization andBoth equal component weighting. Missing cross-task modalities remain explicitly unmeasured. Figure4 uses jointly valid participant signed means normalized by pooled baseline participant SD, covariance distribution contours, not mean confidence intervals. Data do not get forced to confirm decoupling.
Completed Work / Files Changed: three new Python modules, three test modules, requirements_publication.txt, run_publication_figures.bat; outputs in publication_figures/ with input hashes,raw summaries,statistics,captions,METHODS.md andREADME_RESULTS.md. No existing source CSV modified. No Git repository.
Tests / Verification:10tests pass; actual full CLI completes;30participants(groups10each),40trainingchannels,420participant-block summaries. PNG dimensions/DPI andPDF physical sizes checked;PDF embedded-font objects present andno raster image objects. All211read-input hashes unchanged. All3plots visually checked.
Known Issues: twoFigure3cells not measured, all12Tukeypair testsn.s.; fixed single-exponential rate forStrength/Angle SDnot identifiable; normalized indices across different trained tasks aredescriptive. Across-participant mean ellipses cannot provewithin-person motor-noise decoupling;baseline/post averagingcounts differ. SeeREADME_RESULTS.mdforactual hypothesis check. Oldvalidation reports apply toolder rules.
Remaining Work: none for this implementation/export request. Recommended Next Step: run run_publication_figures.bat orpython plot_publication_figures.py; interpret withMETHODS.md. This issole overall task-state entry; existing app handoff still belongs tolearning_curve_tool/TASK_STATE.md.

## 2026-11-08 supplementary research figures (current completed request)

### Original Goal
Recommend scientifically useful additional figures based on existing results and implement a working batch program.

### Requirements / Constraints
Preserve all source CSVs, authoritative groups and existing outputs; no Git repository or Git operations. Use 01-30 and actual stage counts. Reuse the current publication data selection; no deleted valid extremes or manufactured significance. English figures, 300 DPI PNG and vector PDF; Chinese interpretation and one-click BAT.

### Current Plan
Implementation and verification complete. Supplement existing Figures2-4 with paired estimation, observed error decomposition, and direct group contrasts.

### Architecture / Important Decisions
Root plot_supplementary_analyses.py imports audited load_data from plot_publication_figures.py. The new statistics use baseline/test processed_csv only. Loader also audits training with scored AND outlier!=1; training does not contribute to these supplementary endpoints. Four measured task/channel combinations only. Participant pairing is by ID, never by row order. Each person has equal group weight. Figure5: individual MAE changes plus group mean 95% BCa CI. Figure6: exact empirical MSE = signed_mean^2 + population variance (ddof=0), with separate finite-n sensitivity partition (mean^2-s^2/n)+s^2 in CSV. Figure7: independent-group differences of participant paired MAE changes. Bootstrap uses9999resamples, seed20261108, sampling participants rather than trials. Pointwise exploratory intervals are explicitly not multiplicity/Tukey-adjusted; do not override earlier adjusted tests. Shared x limits within same-unit rows of Figures5/7; Figure6 panel scales explicitly differ.

### Completed Work / Files Changed
Added plot_supplementary_analyses.py, run_supplementary_analyses.bat, test_supplementary_analyses.py, verify_supplementary_analyses.py. Root AGENTS.md points here. Outputs supplementary_figures/: Figures5-7 PNG/PDF/captions, participant_paired_metrics.csv, paired_effect_statistics.csv, component_statistics.csv, group_contrast_statistics.csv, README_RESULTS.md, source_hashes.json, run_manifest.json and verification.json. Dependencies use existing requirements_publication.txt; verifier uses Pillow already supplied with Matplotlib dependencies.

### Tests / Verification Performed
5new numerical/pairing/bootstrap tests plus10existing publication tests pass(15total). Real batch completes:30participants,120paired endpoints, all120eligible for both MAE/decomposition. Independent verifier reads actual source CSVs and checks240stage summaries against direct MAE/MSE/variance/squared-mean calculations; both decomposition identities checked across120pairs. All211input SHA256 hashes unchanged and equal previous publication-run manifest. All3PNG3600x2400 at300DPI; PDF font embedding found with no raster image objects; derivedCSVutf-8-sig. All3figures visually inspected; initial left-label crowding fixed and Figures5/7 re-inspected. BAT invokes tested CLI; no literal desktop double-click test.

### Known Issues
Exploratory uncertainty with10people/group, no simultaneous confidence coverage.12direct group contrasts:10pointwise intervals cross0; remaining2are unadjusted and cannot be promoted over previousTukeyresults. Angle group's angle-only observed variance change estimate+6.84deg^2 has wide95%CI[-11.76,52.48]; observed bias^2 decreases7.86, totalMSE decreases1.02. This is a hypothesis-generating dissociation, not established variance increase. Finite-n correction assumes independent identically distributed stage trials and can yield negative squared-bias estimates; retained without clipping. Observed capped scores remain capped, not inferred latent scores. Stage variance includes drift and measurement error; cannot label it pure motor noise. No untrained control or delayed retention conclusions.

### Remaining Work
None for this requested batch implementation and export. Mechanistic/mixed-model inference or collecting repeated baseline/retention measurements is future research, not an unimplemented requirement of this batch.

### Recommended Next Step / Important Context for Next Session
Run run_supplementary_analyses.bat; read supplementary_figures/README_RESULTS.md with the figures. Use verify_supplementary_analyses.py for independent source/artifact audit. This file remains the unique overall handoff; do not replace older source selections in other applications merely because this supplemental entry reuses the newest publication loader.

## 2026-11-12 — HILD adoption and current research progress (read first)

### Original Goal
The overarching scientific goal remains the supervisor's five steps: finish preliminary processing; retain signed angle/strength with separate mean and variance; decide on Student-t/outlier/true-censoring treatment; compare baseline and transfer; fit learning splines with separate mean and variance. The current user request is to install HILD and begin managing progress. It does not authorize a new statistical redesign in this session.

### Requirements / Constraints
Participant source CSVs are read-only, no source backup folders, no Git initialization/commit/reset, no repeat filename migration. Preserve prior outputs and established handoffs. Separate implemented code, verified results, scientific acceptance and researcher-confirmed understanding. Do not mark research complete just because figure exports or HILD installation are complete.

### Current Plan
HILD local installation is complete and in use for orientation/journaling. The next **proposed**, not yet authorized, scientific scope is to agree on the primary analysis and its eligibility/censoring rules, then identify precisely which figures are descriptive supplements. Existing authorized figure-production tasks remain completed; this broader interpretation question remains open.

### Architecture / Important Decisions
See [HILD local configuration](../../HILD/LOCAL.md). The existing file you are reading remains the sole overall plan/current-state authority; [HILD/plan.md](../../HILD/plan.md) only links here. Application-specific history remains in [learning-curve TASK_STATE](../../learning_curve_tool/TASK_STATE.md). HILD journals live under [HILD/journal](../../HILD/journal/2026-11-12.md). There is no wiki or GitHub tracker. Local setup was requested by the user, but no separate scope-issue review, decision acceptance or understanding confirmation is inferred.

### Completed Work / Files Changed
Installed seven upstream skills under `.agents/skills/hild-*/` using the skill-installer helper. Installed reusable HILD process, templates and scripts pinned to [ab419eed1b50b0ea4fc639890edced0f5f4a01c9](https://github.com/Motor-Learning-Lab/HILD/tree/ab419eed1b50b0ea4fc639890edced0f5f4a01c9); [installation.json](../../HILD/installation.json) records original hashes. Added [LOCAL.md](../../HILD/LOCAL.md), a plan pointer, [local installation scope](../../HILD/scopes/0001-adopt-hild.md), decision-directory guidance and first journal. Appended a HILD pointer to root [AGENTS.md](../../AGENTS.md); preserved its prior rules. HILD README has one local-adaptation notice. No scientific program or data changed.

### Tests / Verification Performed
Upstream read-only verifier: `python HILD/scripts/install_hild.py --target D:/experiment --verify` verifies all27recorded upstream files. The README notice is an intentional local change against its preserved upstream hash. All seven skill files and required links are present.211analysis input hashes match the prior publication/supplementary manifest; no source change detected. `.git` remains absent. Scientific test suites were not rerun for a documentation/skill installation; previous test counts above remain dated historical evidence. `hild-integrate`, `hild-orient` and `hild-journal` were explicitly read and used. Automatic fresh-session skill discovery and hook behavior are unverified; no hooks were installed or claimed to run.

### Current Scientific Progress

| Workstream | Implementation / evidence | What remains unresolved |
|---|---|---|
| Preliminary processing and provenance | Actual source directories, flexible filenames, counts and groups audited; source hashes retained | Full upstream measurement validity is not newly established by plotting audits |
| Signed mean and variance | Present in [robust_model.py](robust_model.py), [component_figures.py](../../learning_curve_tool/component_figures.py), and [group comparison script](../../plot_baseline_vs_transfer.py) | Researcher confirmation of interpretation has not been recorded |
| Student-t and true censoring | Location/scale likelihood and censor helpers implemented; see [censor audit](CENSOR_AUDIT.md) | Final primary strategy and consistent selection across entry points still need explicit agreement |
| Baseline vs transfer | Robust group figures and descriptive Figures3-7 generated; historical verification above | Descriptive MAE/bootstrap outputs and robust latent/model summaries must not be presented as one uniform method |
| Learning curves | Per-participant Student-t mean/log-scale splines implemented; Figure2 separately uses10-shot normalized block summaries plus exponential least-squares fitting | Figure2 is not the supervisor's requested trial-level Student-t spline analysis; final primary figure choice remains open |

### Known Issues / Understanding Debt
1. The researcher asked which method was actually used. [Publication METHODS](../../publication_figures/METHODS.md) and [supplementary README](../../supplementary_figures/README_RESULTS.md) describe observed-score arithmetic summaries/Bootstrap, while the earlier robust app uses Student-t likelihood. Treat explaining this distinction as pending researcher review, not established understanding.
2. Current entry points do not have identical training eligibility: the robust learning app's labeled-training path uses finite nonflagged data, while the new publication loader additionally requires channel status=scored. Do not silently change either policy during HILD setup. A future unification needs a bounded scientific decision and matching validation.
3. SD, SEM, confidence intervals and participant covariance ellipses describe different quantities. Figures and captions have explicit labels; understanding has not been confirmed.
4. Recorded censoring, baseline/post sample-size differences, small groups and exploratory multiple comparisons constrain interpretation. Existing smoothness or ellipse contraction cannot prove motor-noise reduction or decoupling.
5. This is a manual local adaptation, not an upstream-supported automatic installation into a clean Git repository. Remote issue/PR review, wiki publication, hooks and Git-backed history are absent. There is no background monitoring service.

### Remaining Work
No remaining installation work for the user's HILD request. Scientific acceptance and pending understanding topics above are not complete and are not automatically authorized for implementation. A fresh session may verify automatic skill discovery; until then use explicit skill paths.

### Recommended Next Step
Present a concise HILD orientation and propose one bounded review: decide which analysis is primary for the supervisor's requirements, using the actual differences above. Before any scientific edits, record the user's intended scope; preserve already authorized routine autonomy.

### Important Context for Next Session
Read root AGENTS, [LOCAL.md](../../HILD/LOCAL.md), this latest section and the latest HILD journal. Use `hild-orient` / `hild-journal`; do not restart installation or rerun outlier labeling. Skills should be available on a subsequent turn, but actual automatic discovery must be observed rather than assumed. Only the researcher can confirm understanding or accept a proposed scientific decision.

## 2026-11-13 — Workspace cleanup and private Billiards migration (current)

### Original Goal / Requirements
Organize the multi-function experiment workspace, remove unnecessary old outputs, preserve every CSV and video, upload code and all CSVs, and manage work through HILD Issues/PR/Wiki. User chose video-local-only and subsequently changed Billiards from public to private. Keep it private. This request explicitly supersedes the earlier no-Git rule; source-data protection remains unchanged.

### Constraints / Important Decisions
No statistical-method changes, no rewritten CSV bytes, no video deletion/upload, no paid storage, no force/reset, no unapproved merge. Keep runtime/provenance dependencies and existing working paths. Functional classification is through existing module/output folders and the new README navigation, not arbitrary moves that break imports, launchers or historical links. Preserve all test/historical CSVs, including 1,437CSV files under `.test_runs`.

### Architecture / Current Plan
Repository: [ayyyeeeee/Billiards](https://github.com/ayyyeeeee/Billiards). Initial main commit555e295 contains overview/templates. Full migration branch `maintenance/organize-workspace`; a PR will present the full content for researcher review. [Issue1](https://github.com/ayyyeeeee/Billiards/issues/1) records the authorized scope. [Issue2](https://github.com/ayyyeeeee/Billiards/issues/2) tracks primary-method agreement, which is not implemented by this migration. [Issue3](https://github.com/ayyyeeeee/Billiards/issues/3) tracks Wiki web availability.

### Completed Work / Files Changed
Inventory:10,033files/42.772GiB, including2,523CSV and210MKV. Removed1,380 superseded preview/bytecode files,74,597,303bytes; specific paths/reasons in [cleanup_report](../../docs/maintenance/cleanup_report.json). Preserved every CSV and video, old migration/checkpoint evidence, logs, and needed `.deps`/`.tcl` locally. Added root README functional categories, ignore rules, CSV byte-preserving attributes, Issue/PR templates, source/video inventory and reproducible conservative cleanup script. Updated AGENTS/HILD configuration for authorized GitHub workflow. Wiki original Home preserved; draft Process-HILD/Guide-Functions/status/sidebar pushed as9230557.

### Tests / Verification Performed
15publication/supplementary unit tests pass. Original2,523CSV SHA256 and210video path/size/mtime checks pass after cleanup. Videos were not re-encoded or rewritten. Git-stage CSV-byte verification runs before commit; result recorded in [migration_verification](../../docs/maintenance/migration_verification.json). CSVs are explicitly force-added even under ignored runtime directories. No video is staged. Original bootstrap main pushed successfully; final migration remote verification is recorded below when complete.

### Known Issues
GitHub API reports private=true and has_wiki=false, despite successful Wiki Git clone/push. Wiki synchronization is verified; web UI feature availability is not. Do not change visibility or buy an account upgrade to bypass this. Browser control failed URL-policy verification during the earlier session; no further browser workaround was used. Scientific method/selection and understanding issues in prior entries remain open. Upstream HILD README/config local modifications are intentional.

### Remaining Work / Recommended Next Step
Migration uploaded and [PR4](https://github.com/ayyyeeeee/Billiards/pull/4) opened for researcher review; no merge performed. Remote recursive tree at commit dfe712f70b0ec0eab703e64d99e23e0c99723f76 is not truncated and contains4,708files, exactly2,523CSV and0videos. This was checked against the GitHub API after successful push. The original data-bearing commit remains available; final bookkeeping commits only update documentation. Wiki remote head92305577c353d1678a9c630ebbe27e2b8e737d71 was pushed successfully, preserving the original Home greeting. Local main/Wiki working trees were clean after their respective data commits. Researcher review/merge remains pending; Wiki website availability requires the account/settings check under Issue3, not further data uploads. Scientific Issue2 is not implemented by this task.

### Important Context for Next Session
Read this section before older no-Git entries. `wiki/` is its own ignored Git clone. No automatic hooks or background monitors are enabled. Never rerun `workspace_cleanup.py --apply` merely to regenerate its historical audit; preserve the original protection manifest and cleanup report. Do not delete any CSV just because it is under a test/backup path.


### 2026-11-14 recovery milestone
The 2026-11-13 final documentation push was prevented by automatic approval-review quota exhaustion; it did not execute. Recovery inspected both unstaged documentation edits and the clean index/Wiki worktree. Remote repository remains private and PR4 open/unmerged. Issue1 now reflects private visibility and completed data upload. This recovery commits the prepared verification record plus the new dated journal; no data or scientific program changed. Remaining external actions are researcher PR review/merge and Wiki web enablement under Issue3.
