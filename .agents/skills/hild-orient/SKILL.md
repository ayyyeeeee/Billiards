---
name: hild-orient
description: Present a concise start-of-session orientation about project progress, pending human reviews, understanding debt, and next work. Use on session start or when asked where the project stands.
---

# Orient

Rules: [HILD process](../../../HILD/process.md), *Presentations* and *Durable state files*. Resolve any configured authoritative paths before acting.

1. **Find out what happened.** If a session-start hook has provided information, use it. Otherwise read the plan, latest journal, recent Git changes, open issues and PRs, and available wiki status. The reference `HILD/scripts/session_context.sh` (once installed) can supply these facts; do not assume it has run or exists.
2. **Check what is missing.** Note completed work that the journal doesn't mention and wiki edits that haven't been published. Explain any gaps, then use `hild-journal` or `hild-understood` when authorized to repair them.
3. **Present** in about fifteen lines, leading with what needs the human:
   - **Needs you:** PRs awaiting review and proposed approval tracks, scope issues awaiting agreement, questions, wiki pages to read.
   - **Where we are:** current goal and state.
   - **Since last time:** material changes, with links.
   - **Understanding debt:** code the human has not yet reviewed fully and wiki pages that may no longer match the code.
   - **Next:** the next plan step and what is proposed now.
4. **Wait.** Do not start nontrivial development before the reviewer responds unless an agreed scope explicitly covers continuing work.

A hook firing is not evidence that orientation was delivered or understood. If an information source is unavailable, say so rather than filling it in from memory.
