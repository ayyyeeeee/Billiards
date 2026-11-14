# Setting up a new HILD understanding wiki

This procedure is used by [hild-understood](SKILL.md) **only when the project
has no existing wiki** and the researcher has agreed to create a new one.
It is not a procedure for integrating or replacing an established wiki.

## Why a separate wiki?

The wiki is a map of what the human reviewer understands. It links to the
authoritative code, decisions, and process, but is **not** another source of
rules. The agent can draft or correct pages; only the human reviewer can
confirm that a page is `understood`.

## Before making any changes

1. Check the repository's Wiki feature and whether a wiki repository
   already exists. If there is an existing wiki, **stop**: reconciling it
   is outside the first-install scope. Do not overwrite its Home page.
2. Explain that a wiki is a **separate Git repository** with a visible
   GitHub website. Creating or editing it has external effects. Obtain the
   human's specific agreement to create it.
3. Confirm the repository is reachable through GitHub and Git credentials
   will permit pushing wiki edits. If either cannot be established, report
   the blocker; don't claim that the wiki is installed.

## Create the new wiki

1. If necessary, enable **Wikis** in repository settings. On GitHub, a new
   wiki needs its **first page created through the website** before its Git
   clone URL is available. The first page can be a minimal Home page.
2. Clone the wiki Git repository into the project's configured local wiki
   directory (default `wiki/`). Ensure that directory is **ignored by the
   main code repository**; it has its own Git history.
3. Add a clear `Home.md` introducing the understanding map, and an
   `_Sidebar.md` with navigation for code, concepts, process, guides and
   resources. Link the generated `Status-board`. Do not create any code
   or `Process-HILD` page merely to fill the navigation.
4. Run `HILD/scripts/wiki_status.py --repo <host-root>
   --wiki <wiki-folder> --ref <main-ref> --write` after verifying those
   paths and the actual main ref. Inspect the status board that the script
   generates. A new wiki normally has no code pages yet.
5. Commit and push the wiki changes. Confirm the pages are visible on GitHub,
   and report the wiki URL and any incomplete checks.

## When onboarding reaches its first PR

Its explanation may **propose** a `Process-HILD` page explaining how this
particular repository uses HILD. If the reviewer agrees, draft that page
**after the PR merges**, so it describes the actual result. The page stays
`draft` until the researcher reviews and confirms their understanding.

## Failure handling

Do not treat a created folder as proof that the GitHub wiki exists. Do
not force-push or replace someone else's changes. If the remote is empty,
unreachable, already populated or can't be updated safely, report the
observed state and ask for the next decision. A missing wiki is a recorded
installation-verification failure or pending prerequisite, not a silent pass.
