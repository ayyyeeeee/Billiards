---
name: hild-scope
description: Work with the researcher to agree on a manageable scope before nontrivial development. Use when someone wants to plan work, scope a change, or begin HILD onboarding.
---

# Scope — develop an agreement together

Authority: [HILD process](../../../HILD/process.md), *Scope agreements*.
The completed agreement uses the
[scope issue template](../../../HILD/templates/scope-issue.md).
Locate the host project's real plan, decisions and process; `HILD/` is
the default, not a reason to duplicate files kept elsewhere.

## Begin with the researcher's goal, not a form

Read the project's current plan and relevant decisions, then discuss what
the researcher is trying to accomplish and why. Use goals they already
gave you rather than asking them to repeat themselves. Offer useful
expertise and explain recommendations in terms of their project.

The **newcomer-specific introduction**, including what to say after
the researcher agrees to begin their first scope, belongs in the
[onboarding companion](onboarding-scope.md), not here. **Read that file
when the researcher is new to HILD, requests guidance, or explicitly
wants an onboarding scope**. Do not load it for ordinary scoping by an
experienced researcher.

## Build shared understanding of the work

The agreement needs four things:

- **Goal:** what the researcher wants to accomplish, and why.
- **Boundaries:** what belongs in this work and what waits.
- **Evidence:** how the researcher and agent will recognize success.
- **Autonomy:** what the agent can decide or change within the scope,
  and what still needs explicit human agreement.

These describe **the finished scope**, not four questions to ask
in a fixed order. Develop them naturally, following the researcher's
responses. Summarize decisions periodically so the agreement becomes
visible. Don't rush to file an issue or proceed with development simply
because the researcher said "yes" to discussing a scope.

Contribute expertise: suggest a reasonable default and explain **why
it will serve the researcher**. Mention available alternatives briefly;
compare a few choices if the tradeoffs matter. Avoid a broad menu or
configuration questionnaire unless options materially affect the outcome.
When a blocker becomes relevant to the agreed work, help diagnose it
and propose a feasible next step instead of merely stopping.

## Record, show, and obtain approval of the actual scope

Once you have developed a coherent scope together, prepare a proposal using
the [canonical template](../../../HILD/templates/scope-issue.md).
Obtain agreement to **create the proposed issue**, then, if GitHub access
permits, create it labelled `scope`. Otherwise show the draft, explain the
access blocker and remain stopped.

**Immediately after creating the issue:** give the researcher its clickable
GitHub link; briefly explain what the **actual issue** allows and excludes,
and ask them to **review and approve that issue or suggest corrections**.
This is a genuine stopping point. Do not start a branch, run an installer,
apply changes, or treat an earlier conversational `OK` as approval of a
GitHub document the researcher has not reviewed.

When the researcher explicitly approves the completed issue, record that
approval **in the issue** before beginning implementation. They can approve
in an issue comment, or you can add an accurate, attributed summary of their
approval in chat. Link back to that record when starting work. If the issue
changes materially, show the updated issue and obtain fresh approval.

Approval to **discuss a scope**, permission to **create its issue**,
approval of the **issue's contents**, permission to **apply an installer
preview**, and **PR review/merge** are separate decisions. Keep the
conversation concise, but never silently combine these gates.

Do not merge a pull request or mark the researcher's understanding
confirmed on their behalf.
