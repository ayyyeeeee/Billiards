---
name: hild-understood
description: Draft and maintain the reviewer's understanding-map pages, including post-merge code pages, explanations of concepts, guides, resources, and HILD process pages. Use after a merge, when understanding changes, or when a page is stale.
---

# Understood

Rules: [HILD process](../../../HILD/process.md), *Understanding map*.
Templates: [wiki code page](../../../HILD/templates/wiki-code-page.md) and
[general wiki page](../../../HILD/templates/wiki-page.md).

In the original project, the wiki is a separate Git repository copied into a local `wiki/` folder that the main repository ignores. The installed project's configuration should identify its actual wiki location. **Do not create or overwrite a wiki implicitly.** In particular, existing-wiki integration is outside the first-install scope.

**Creating a new wiki:** If there is no wiki and the researcher has approved creating one, read [new-wiki.md](new-wiki.md). This companion is for a *fresh* wiki only. If an existing wiki is found, stop and propose a separate integration scope; do not replace it.

1. **Find the wiki and get the latest pages.** Read its configured location and remote address. If it uses Git, pull only when Git can add the new changes without rewriting existing work (`--ff-only`). If that fails, stop and explain rather than overwrite anyone's edits.
2. **Draft from the actual code.** A code page should describe what is already on `main`, with the commit it describes. If a page might be out of date, compare that commit with the current code. Use a process, concept, guide or resource page for other subjects.
3. **Keep human confirmation meaningful.** The agent can mark a page as a draft, placeholder, needing revision or needing another review. **Only the researcher** can confirm it as `understood`. Link related pages; create placeholders only when the agreed work needs them.
4. **Keep navigation and status current.** Update Home and the sidebar. If the staleness checker exists, run `HILD/scripts/wiki_status.py --write` on the configured wiki and inspect what it changed. This script does not commit or publish anything.
5. **Publish promptly.** Commit and push the wiki after each approved update; report page links and those awaiting human review.

For onboarding, the scope/PR may propose a `Process-HILD` wiki page, but write the agreed draft **after** the onboarding PR has merged.
