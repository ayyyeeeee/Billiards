---
name: hild-integrate
description: Assess a repository read-only and help the researcher decide how to adopt, upgrade, reconcile or audit HILD. For newcomers, load the onboarding companion before presenting findings.
---

# HILD integration — assess first, then guide agreement

Authoritative rules: [HILD process](../../../HILD/process.md). If reading
this skill from an upstream URL before installing HILD, also read the upstream
process; links relative to this skill may not resolve in the target repository.

## Non-negotiable read-only first pass

**Assess first; do not install.** During the initial assessment, do **not**
change files, branches, issues, pull requests, settings, hooks or remote refs;
do not commit, fetch, pull, execute scripts or generate files. Read-only
operations such as `git status`, `git log`, `git ls-files`, `git show`
and GitHub GET requests are allowed. Avoid suspected secrets and untrusted
executables. Report access limitations rather than treating unseen work as
absent.

## Gather enough evidence to guide the conversation

1. **Identify the two repositories.** Check the target repository, branch,
   visible files and existing work; identify the upstream HILD commit and
   available access. Never confuse GitHub's committed state with an unexamined
   local working tree.
2. **Check what needs preserving.** Look for project instructions, process
   rules, skills/hooks, decisions, plan, journal, tests, wiki, repository
   settings and development conventions. Identify each authoritative home;
   don't assume HILD should replace an existing one.
3. **Recognize the installation state.** Distinguish no HILD, an installation
   with known upstream provenance, one with uncertain provenance, and partial
   adoption. For an existing installation, compare the recorded old upstream
   baseline (B), current local files (L) and proposed upstream (N), where
   possible. If the baseline is missing, say so; don't overwrite local changes.
4. **Identify the consequential choices and blockers.** Think through safe
   additions, collisions, prerequisites and feasible ways forward without
   changing anything.

These are **assessment tasks**, not a mandatory order of headings in the
conversation. Keep supporting paths, revisions, conflicts and evidence
available for questions and the eventual scope issue.

## New or guidance-seeking researchers

**Read and follow the [onboarding companion](../hild-scope/onboarding-scope.md)
as authoritative for the newcomer interaction.** If HILD is not installed,
read it from the same upstream repository and revision as this skill.

## The integration conversation after assessment

For a researcher already familiar with HILD, the first response should
support a decision about **this repository's adoption or update**. Give
them a short, evidence-based account of its relevant current state:
what HILD appears to have installed, what existing material must be
preserved, and what remains uncertain. Connect an initial recommendation
to their stated objective and explain the principal tradeoff, if there
is one. **End with the next consequential question or proposed agreement**,
not the complete file inventory.

Use your assessment to guide what happens after the reply:

- If the researcher corrects a fact or names an existing authority,
  revise the assessment before proposing to change that material.
- If they explain a new goal or constraint, shape the integration scope
  around it; use [hild-scope](../hild-scope/SKILL.md) for scope agreement.
- If they want an alternative, compare only the relevant paths, grounded
  in the repository and available tooling.
- If a missing checkout, authentication, permission or Git remote blocks
  the **agreed next action**, load the on-demand
  [GitHub-access companion](github-access.md) and diagnose the specific
  failure together. Report what was verified and what remains untested.
- If they agree to a final proposal, record the agreed scope through
  the normal issue workflow **before implementing**.

**For newcomers, the onboarding companion governs the interaction instead
of this section.** Keep repository-specific findings available to inform
it; do not restate its introduction or first-scope examples here.

The assessment itself remains read-only. A technical inventory, authority
map and source revision must be available when required by a decision
or for the final scope, even when the initial response is concise.
Neither an installed file nor a configured hook proves live agent behavior.

## Before agreement is complete

The eventual scope must capture the target and upstream revision, what
existing authority will be preserved, intended changes, conflicts and
deferrals, stopping points, and checks for success. It must also distinguish
what has been observed from what remains to be tested. Record the result in
the [scope-issue format](../../../HILD/templates/scope-issue.md) **after
developing the agreement**, not as an upfront form for the researcher.

**Stop before making changes.** A read-only assessment or agreement to
*discuss* scoping does not authorize an issue or installation. Use
[hild-scope](../hild-scope/SKILL.md) to record a **proposed** installation
scope issue after the researcher agrees to create it, and then obtain the
researcher's review and **recorded approval of that actual issue**.
Only after that approval should you read [first-install.md](first-install.md)
for a new repository. That separately approved preview-first procedure
does not implement existing-wiki integration or upgrade reconciliation.
