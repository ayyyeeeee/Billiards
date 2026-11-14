---
name: hild-explain
description: Prepare a human-understandable pull-request explanation with code permalinks, evidence, consequences, wiki-page proposals and a review track. Use when a PR is ready for review or an implementation needs explanation.
---

# Explain

Rules: [HILD process](../../../HILD/process.md), *Presentations* and *Approval*.
Format: [PR explanation template](../../../HILD/templates/pr-explanation.md).
An approved squash merge should use the PR title and final description as its commit message.

## Write

1. Commit and push the work within the agreed scope; do not rewrite a pushed PR branch.
2. Record the exact head commit, and inspect the complete diff against the PR base (`git diff main...HEAD` where `main` is the base). Explain what **currently exists**, not the agent's original intention.
3. If the change cannot be explained in one sitting, propose splitting it.
4. Fill the template in conceptual order, not file order. Include mathematics **only if it helps explain this change**, load-bearing code permalinks, evidence, untested behavior and consequences. Add a **Surprises** section only when something unexpected happened; say whether follow-up work is needed. Omit sections that have nothing to say.
5. **Wiki pages:** inspect the configured understanding map when available; list relevant pages and their statuses, then propose new/updated pages. Essential concept explanations precede review; code pages describing the merge commit follow it. If no wiki is configured, say so plainly rather than inventing links or statuses.

## Check and publish

- Render math in GitHub markdown or report that rendering was not checked. Verify links and line references.
- Beware GitHub's closing keywords: write `Closes #N` only when this PR *finishes* issue N; otherwise write `Part of #N`.
- Update the PR description to describe the whole change as it stands. Mark ready for review when the explanation is accurate.

## After review

- Reply in the reviewer's original comment thread, with permalinks to fixes.
- After new commits, **rewrite the explanation in place**, updating permalinks to the new head. At its end append a dated *Changes after review* section; later rounds append, not prepend.
- **Full track:** compare the human's explain-back with the code, then clarify or change the code if they differ.
- **Fast track:** label the PR `understanding-debt`, create a follow-up issue, and set related wiki pages `needs-review` after merge.
- **After the human merges:** update the plan/journal using `hild-journal`, then prepare agreed wiki pages using `hild-understood`.

Never claim review approval, successful tests or a merge before the actual evidence exists.
