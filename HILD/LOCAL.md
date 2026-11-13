# HILD in the billiards-learning workspace

## Current configuration — 2026-11-13 (supersedes the historical configuration below)

The researcher explicitly authorized Git initialization, uploads, Issues, PRs and Wiki for [Billiards](https://github.com/ayyyeeeee/Billiards), then made it private. Work on branches and submit PRs for researcher-approved merging. Do not change visibility. All CSVs are preserved and uploaded byte-for-byte; all videos remain local and inventoried. Logs and locally required runtimes stay local. Do not reset source data or change scientific methods during organization.

Use [Issues](https://github.com/ayyyeeeee/Billiards/issues) for bounded work, [PRs](https://github.com/ayyyeeeee/Billiards/pulls) for review, and the [Wiki](https://github.com/ayyyeeeee/Billiards/wiki) for draft explanations. The separate Wiki clone is `wiki/`, ignored by the main repository. Only the researcher can confirm understanding or approve a merge. The existing TASK_STATE remains the sole overall plan. Hooks remain disabled; API Wiki web availability is checked separately from Git synchronization.

The following 2026-11-12 local-only configuration is retained as historical context. Its no-Git restrictions no longer apply to the authorized migration.

## Historical configuration — 2026-11-12

This was a **local, non-Git adaptation**, installed on 2026-11-12 at the researcher's request.

## Authority and preserved constraints

[Project instructions](../AGENTS.md) and the researcher's explicit requests take precedence over conflicting upstream defaults. This workspace is not a Git repository. Do not initialize Git, commit, reset, push, create remote issues/PRs, or publish a wiki as part of local progress tracking. Participant CSVs remain read-only; do not create source-data backup folders. The approved filename migration must not be repeated.

| Purpose | Authoritative location |
|---|---|
| Project rules and data protection | [AGENTS.md](../AGENTS.md) |
| Reusable HILD collaboration process | [process.md](process.md), subject to this local mapping and project instructions |
| Overall goals, progress, evidence, remaining work | [existing TASK_STATE.md](../tools/outlier_batch/TASK_STATE.md), latest section |
| Learning-curve application's own implementation history | [application TASK_STATE.md](../learning_curve_tool/TASK_STATE.md) |
| Milestone history from this installation onward | [journal](journal/2026-11-12.md) |
| Local bounded work records | [scopes](scopes/0001-adopt-hild.md) |
| Proposed consequential decisions | [decisions](decisions/README.md) |
| Researcher understanding | Pending review topics in the overall TASK_STATE; no wiki configured |

[plan.md](plan.md) is only a pointer to the existing authoritative handoff, not a second editable progress board. Upstream HILD's own development plans, decisions and journals were not imported as this experiment's history.

## How we use HILD here

1. At the start of work, use `hild-orient`: read the project instructions, current handoff and latest journal; inspect relevant actual files before reporting state. State what needs review, what is verified, and the next proposed step.
2. Use `hild-scope` to make nontrivial work bounded and reviewable. Record goal, included/excluded changes, acceptance checks and the actual user authorization. Respect already authorized work; do not fabricate approvals or retroactively claim that a scope document was reviewed. A new scientific decision outside an authorized task requires discussion before implementation.
3. Implement authorized work and verify it. Use `hild-explain` to distinguish purpose, essential method, evidence and remaining limitations. Local file links and recorded hashes replace unavailable Git permalinks; they are not remote backups or immutable version history.
4. Use `hild-journal` at milestones. Update the existing TASK_STATE rather than duplicating it. Do not follow upstream instructions to commit or push in this non-Git workspace.
5. Only the researcher can confirm understanding or accept a proposed scientific decision. An explanation being written, a test passing, or silence is not that confirmation. A future understanding wiki requires a separate request.

## Installation and capability status

- Seven upstream `hild-*` skills are under [.agents/skills](../.agents/skills), with reusable process, templates and scripts under this directory.
- Source revision and original file hashes: [installation.json](installation.json).
- Read-only structural verification: `python HILD/scripts/install_hild.py --target D:/experiment --verify`.
- The upstream `--apply` installer was **not** used: it requires a clean, minimally initialized Git repository and would conflict with this established workspace. Do not run it here to upgrade.
- Codex is the selected agent; hook templates are included as reference files only. No startup hook, background service, remote issue tracker or wiki is enabled.
- Skills are explicitly read and used in this session. Automatic discovery in a fresh session remains unverified; if needed, ask the agent to read `.agents/skills/hild-orient/SKILL.md` directly.
- The upstream verifier checks files and links, not adherence to the human review process or completion of GitHub onboarding.

Future updates must compare the pinned upstream version, installed hashes and local changes. Preserve local documents and user work instead of overwriting them.
