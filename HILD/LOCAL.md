# Billiards HILD local configuration

Current authorization: 2026-11-14. Researcher explicitly chose PUBLIC code/CSV publication and detailed Wiki. Videos stay local. Git, branches, Issues, PRs and Wiki edits are authorized; merges require researcher approval. Do not alter data or scientific methods during organization.

## Authorities
- Project rules: [AGENTS](../AGENTS.md).
- Overall progress: [TASK_STATE](../tools/outlier_batch/TASK_STATE.md), latest section. HILD/plan.md is only a pointer.
- Application history: [learning curve handoff](../learning_curve_tool/TASK_STATE.md).
- Process: [process.md](process.md), subject to explicit user instructions.
- Journal: journal/; proposed decisions: decisions/.
- Tracker: https://github.com/ayyyeeeee/Billiards/issues ; current organization scope #5, scientific-method decision #2.
- Review: https://github.com/ayyyeeeee/Billiards/pulls . No automatic merge.
- Wiki: https://github.com/ayyyeeeee/Billiards/wiki ; separate ignored local Git repository wiki/.

## Workflow
Record bounded scope and actual authorization, implement on a branch, verify, publish an explanatory PR. Explain each method and its inputs/outputs in Wiki. Mark branch-specific pages draft until merged and reviewed. Implementation, verification, scientific acceptance and researcher understanding are separate states. Only the researcher confirms understanding. Explicit existing chat authorization permits continuing this scope; it is not a claim that the researcher reviewed an unseen Issue or PR.

Preserve original Wiki Home and history. Pull fast-forward before editing. Preserve all CSVs, including historical/test fixtures; archive provenance rather than rerun past migrations. Original cleanup evidence is immutable historical evidence; relocation mappings resolve old paths.

## Installation
Seven pinned upstream skills and scripts are recorded in installation.json. Hooks and background monitors remain disabled. Do not rerun upstream --apply over the established workspace. Historical local-only/private configuration is preserved in Git and journals, not active rules.
