#!/usr/bin/env bash
# Print the facts an orientation needs. Used by the session-start hook, whose output is
# added to the agent's context. Every section tolerates failure: a missing tool or no
# network must never break the start of a session.

root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$root" || exit 0

echo "=== Session orientation data (see the 'hild-orient' skill) ==="
echo "When the reviewer sends their first message, begin with an orientation built from"
echo "this data, following .agents/skills/hild-orient/SKILL.md."
echo

echo "--- Git ---"
echo "Branch: $(git branch --show-current)"
git status --short | head -20
echo

echo "--- Plan (HILD/plan.md) ---"
cat HILD/plan.md 2>/dev/null || echo "(no plan file)"
echo

latest_journal="$(ls HILD/journal/*.md 2>/dev/null | sort | tail -1)"
echo "--- Latest journal entry: ${latest_journal:-none} ---"
if [ -n "$latest_journal" ]; then
    cat "$latest_journal"
    echo
    echo "--- Commits since the journal was last updated ---"
    last_journal_commit="$(git log -1 --format=%H -- docs/journal 2>/dev/null)"
    if [ -n "$last_journal_commit" ]; then
        git log --oneline "${last_journal_commit}..HEAD" | head -30
        git log --oneline "${last_journal_commit}..origin/main" 2>/dev/null | head -30
    fi
fi
echo

if command -v gh >/dev/null 2>&1; then
    echo "--- Open pull requests ---"
    timeout 10 gh pr list --limit 20 \
        --json number,title,isDraft,headRefName \
        --template '{{range .}}#{{.number}} {{.title}} [{{.headRefName}}]{{if .isDraft}} (draft){{end}}{{"\n"}}{{end}}' \
        2>/dev/null || echo "(could not reach GitHub)"
    echo
    echo "--- Open issues ---"
    timeout 10 gh issue list --limit 30 \
        --json number,title,labels \
        --template '{{range .}}#{{.number}} {{.title}}{{range .labels}} [{{.name}}]{{end}}{{"\n"}}{{end}}' \
        2>/dev/null || echo "(could not reach GitHub)"
    echo
fi

if [ -d wiki/.git ]; then
    echo "--- Understanding map (wiki) ---"
    # Pick up pages the reviewer edited in the browser.
    timeout 10 git -C wiki pull --ff-only --quiet 2>/dev/null \
        || echo "(could not update the wiki clone)"
    unpushed="$(git -C wiki status --short; git -C wiki log --oneline '@{u}..' 2>/dev/null)"
    if [ -n "$unpushed" ]; then
        echo "Wiki changes not yet committed or pushed:"
        echo "$unpushed"
    fi
    echo "Last wiki changes:"
    git -C wiki log -5 --format='%ad %an: %s' --date=short
    python3 HILD/scripts/wiki_status.py 2>&1 | head -40
fi
exit 0
