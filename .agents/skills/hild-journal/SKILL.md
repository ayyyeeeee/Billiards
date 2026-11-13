---
name: hild-journal
description: Record a development milestone in the durable journal and update the living plan. Use after pushes, PR state changes, results, decisions, or compaction, or on a request to log progress.
---

# Journal

Rules: [HILD process](../../../HILD/process.md), *Durable state files*.
Formats: [journal entry](../../../HILD/templates/journal-entry.md) and
[decision record](../../../HILD/templates/decision-record.md).

1. **Check what's missing.** Compare the latest journal, Git history, open PRs and work completed since the last update. Find the project's actual plan, journal and decisions; by default they live in `HILD/`.
2. **Record facts plainly** in `YYYY-MM-DD.md` at the configured journal location. Append within the current session; a second session on the same date gets another session heading. Keep the goal, completed work, and next steps clear; include results, findings and permission points only when applicable. Link material results to the command, source, notebook or commit that produced them.
3. **Record important decisions separately** in the project's decision directory, through a reviewed PR. A draft is not an accepted decision. Mention smaller choices directly in the journal.
4. **Update the plan** in place with current goals, actual state and ordered next steps; git history preserves older versions.
5. **Commit and push** the milestone within the agreed branch/scope, or on `main` after merge where allowed by the process.

Do not invent outcomes, backdate unverified events, or create separate report files that duplicate the plan and journal.
