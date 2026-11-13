"""Report on the understanding-map wiki and flag code pages whose code has moved on.

A wiki page declares itself with a small table at the top (Kind, Status, and for code
pages Covers and As of). The format is defined by the page templates in
``HILD/templates/``; the statuses and their meaning by ``HILD/process.md``.

For every page of kind ``code``, this script counts the lines changed in the covered
files between the page's ``As of`` commit and a reference (``origin/main`` by default,
because pages describe ``main``). Pages whose code changed by more than a threshold are
reported as stale.

Usage (from the repo root):

    python HILD/scripts/wiki_status.py              # report only
    python HILD/scripts/wiki_status.py --write      # also update the wiki

Pages that do not exist but are linked from a page that does are reported as
``not-written``.

``--write`` sets the status of stale pages to ``stale`` and regenerates
``Status-board.md``. It never commits or pushes the wiki.

Standard library only, so it runs with any Python 3.10+.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Defined in HILD/process.md (Understanding map); listed here in board order.
STATUSES = ["stale", "needs-revision", "needs-review", "stub", "draft", "understood"]
HEADER_ROW = re.compile(r"^\|\s*\*\*(?P<key>[^*|]+)\*\*\s*\|\s*(?P<value>.*?)\s*\|\s*$")
# A wiki link, [[Page-name]] or [[shown text|Page-name]]; the group is the page name.
WIKI_LINK = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]|]+)\]\]")
BOARD_NAME = "Status-board.md"
# Pages that are not part of the map itself.
SKIPPED_PAGES = {"Home.md", "_Sidebar.md", "_Footer.md", BOARD_NAME}


def parse_header(text):
    """Return the header table of a wiki page as a dict with lowercase keys.

    Only rows before the first heading or blank-line-terminated table count, so a
    table further down the page cannot be mistaken for the header.
    """
    header = {}
    for line in text.splitlines():
        if line.startswith("#"):
            break
        match = HEADER_ROW.match(line)
        if match:
            header[match["key"].strip().lower()] = match["value"].strip()
        elif header and not line.startswith("|"):
            break
    return header


def covered_paths(covers):
    """Split a ``Covers`` value such as "`a.py`, `b/c.py`" into paths."""
    return [part.strip().strip("`") for part in covers.split(",") if part.strip()]


def git(repo, *args):
    """Run git in ``repo`` and return stdout; raise with git's message on failure."""
    # check=False: a failure is re-raised below with git's own message.
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def lines_changed(repo, commit, ref, paths):
    """Lines added plus deleted in ``paths`` between ``commit`` and ``ref``."""
    out = git(repo, "diff", "--numstat", commit, ref, "--", *paths)
    total = 0
    for line in out.splitlines():
        added, deleted, _ = line.split("\t", 2)
        # Binary files show "-" for both counts; count them as one changed line.
        total += 1 if added == "-" else int(added) + int(deleted)
    return total


def exists_at(repo, ref, path):
    """Whether ``path`` exists in the tree of ``ref``."""
    try:
        git(repo, "cat-file", "-e", f"{ref}:{path}")
    except RuntimeError:
        return False
    return True


def read_pages(repo, wiki, threshold, ref="HEAD"):
    """Describe every map page in the wiki, checking code pages against ``ref``.

    Returns a list of dicts with keys: name, kind, status, covers, as_of, changed
    (lines changed since ``as_of``, or None when not applicable), missing (covered
    paths that no longer exist), problem (a message when the page cannot be checked)
    and stale (True when a code page should be reviewed again).
    """
    pages = []
    for path in sorted(wiki.glob("*.md")):
        if path.name in SKIPPED_PAGES:
            continue
        header = parse_header(path.read_text(encoding="utf-8"))
        page = {
            "name": path.stem,
            "path": path,
            "kind": header.get("kind", ""),
            "status": header.get("status", ""),
            "covers": covered_paths(header.get("covers", "")),
            "as_of": header.get("as of", "").strip("`"),
            "changed": None,
            "missing": [],
            "problem": "",
            "stale": False,
        }
        if not header:
            page["problem"] = "no header table"
        elif page["status"] not in STATUSES:
            page["problem"] = f"unknown status {page['status']!r}"
        elif page["kind"] == "code":
            if not page["covers"] or not page["as_of"]:
                page["problem"] = "code page needs Covers and As of"
            else:
                page["missing"] = [
                    p for p in page["covers"] if not exists_at(repo, ref, p)
                ]
                try:
                    page["changed"] = lines_changed(
                        repo, page["as_of"], ref, page["covers"]
                    )
                except RuntimeError as error:
                    page["problem"] = str(error)
                else:
                    moved_on = page["changed"] > threshold or bool(page["missing"])
                    page["stale"] = moved_on and page["status"] != "stub"
        pages.append(page)
    return pages


def not_written(wiki):
    """Find the pages that are linked from the wiki but do not exist.

    Every page is searched for wiki links, ``Home`` and the sidebar included; only the
    generated status board is left out. Returns a dict from the name of each missing
    page to the sorted names of the pages that link to it.
    """
    existing = {path.stem for path in wiki.glob("*.md")}
    missing = {}
    for path in sorted(wiki.glob("*.md")):
        if path.name == BOARD_NAME:
            continue
        for target in WIKI_LINK.findall(path.read_text(encoding="utf-8")):
            name = target.strip().replace(" ", "-")
            if name not in existing:
                missing.setdefault(name, set()).add(path.stem)
    return {name: sorted(sources) for name, sources in sorted(missing.items())}


def set_status(path, status):
    """Rewrite the ``Status`` row of a page's header table."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    for index, line in enumerate(lines):
        match = HEADER_ROW.match(line.rstrip("\n"))
        if match and match["key"].strip().lower() == "status":
            lines[index] = f"| **Status** | {status} |\n"
            path.write_text("".join(lines), encoding="utf-8")
            return
    raise ValueError(f"{path.name}: no Status row to update")


def render_board(pages, ref, commit, missing):
    """Markdown for the Status-board wiki page.

    ``missing`` is the result of `not_written`: pages linked but not written.
    """
    out = [
        "Generated by `wiki_status.py`; do not edit by hand.",
        "",
        f"Checked against `{ref}` at `{commit}`.",
        "",
    ]
    for status in STATUSES:
        group = [p for p in pages if p["status"] == status]
        if not group:
            continue
        out += [f"## {status} ({len(group)})", ""]
        out += [
            "| Page | Kind | Covers | As of | Lines changed since |",
            "|---|---|---|---|---|",
        ]
        for page in group:
            covers = ", ".join(f"`{p}`" for p in page["covers"]) or "—"
            as_of = f"`{page['as_of']}`" if page["as_of"] else "—"
            changed = "—" if page["changed"] is None else str(page["changed"])
            out.append(
                f"| [[{page['name']}]] | {page['kind']} | {covers} | {as_of} | {changed} |"
            )
        out.append("")
    if missing:
        out += [f"## not-written ({len(missing)})", ""]
        out += ["| Page | Linked from |", "|---|---|"]
        for name, sources in missing.items():
            linked_from = ", ".join(f"[[{source}]]" for source in sources)
            out.append(f"| `{name}` | {linked_from} |")
        out.append("")
    problems = [p for p in pages if p["problem"]]
    if problems:
        out += ["## Pages with problems", ""]
        out += [f"- [[{p['name']}]]: {p['problem']}" for p in problems]
        out.append("")
    return "\n".join(out)


def render_report(pages, missing):
    """Plain-text report for the terminal.

    ``missing`` is the result of `not_written`: pages linked but not written.
    """
    if not pages and not missing:
        return "No map pages in the wiki yet."
    lines = []
    for page in pages:
        if page["problem"]:
            note = f"PROBLEM: {page['problem']}"
        elif page["stale"]:
            note = f"STALE: {page['changed']} lines changed since {page['as_of']}"
            if page["missing"]:
                note += f"; missing: {', '.join(page['missing'])}"
        elif page["changed"] is not None:
            note = f"{page['changed']} lines changed since {page['as_of']}"
        else:
            note = ""
        lines.append(
            f"{page['status'] or '?':14} {page['kind'] or '?':8} {page['name']}  {note}"
        )
    for name, sources in missing.items():
        lines.append(
            f"{'not-written':14} {'?':8} {name}  linked from {', '.join(sources)}"
        )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="code repo root")
    parser.add_argument("--wiki", type=Path, help="wiki clone (default: <repo>/wiki)")
    parser.add_argument(
        "--ref",
        default="origin/main",
        help="what to compare pages against (default origin/main)",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=10,
        help="lines changed above which a code page is stale (default 10)",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="mark stale pages and regenerate Status-board.md in the wiki clone",
    )
    args = parser.parse_args(argv)

    repo = args.repo.resolve()
    wiki = (args.wiki or repo / "wiki").resolve()
    if not wiki.is_dir():
        sys.exit(f"wiki clone not found at {wiki}")

    pages = read_pages(repo, wiki, args.threshold, args.ref)
    missing = not_written(wiki)
    if args.write:
        for page in pages:
            if page["stale"] and page["status"] != "stale":
                set_status(page["path"], "stale")
                page["status"] = "stale"
        commit = git(repo, "rev-parse", "--short", args.ref).strip()
        board = render_board(pages, args.ref, commit, missing)
        (wiki / BOARD_NAME).write_text(board, encoding="utf-8")

    print(render_report(pages, missing))
    return 1 if any(p["problem"] for p in pages) else 0


if __name__ == "__main__":
    sys.exit(main())
