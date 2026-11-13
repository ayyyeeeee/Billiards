# Agent startup integrations

HILD has **one copy of its rules and skills**. The researcher's choice of agent
controls which platform-specific discovery files and startup hooks the installer
will offer. The default choice is all supported agents.

This page explains **what the adapter templates can do**. The installer that
will select and install these adapters is **not implemented yet**. Nothing
described here proves that a real agent has used the skills.

| Agent | Shared skills | Optional startup file | Current evidence |
|---|---|---|---|
| Codex | `.agents/skills/hild-*/SKILL.md` | `.codex/hooks.json` from [template](templates/codex-hooks.json) | Supported locations documented; not tested in a live Codex session |
| GitHub Copilot CLI/cloud | `.agents/skills/hild-*/SKILL.md` | `.github/hooks/hild.json` from [template](templates/copilot-hooks.json) | Supported locations documented; not tested in a live Copilot session |
| Claude Code | `.claude/skills/` pointing to the **same** shared skills | `.claude/settings.json` from [template](templates/claude-settings.json) | The original project used a relative symlink; its behavior has not been tested here |

The Claude skill path should refer to the shared directory rather than
copying files into a second source of truth. In a fresh checkout the
installer can **propose** the relative symlink `.claude/skills ->
../.agents/skills`, but must check that the path is unoccupied and that
the user's OS and Git checkout actually preserve symlinks. If not, offer
explicit skill-file access instead of claiming automatic discovery.

## What the startup scripts do

[The startup collector](scripts/session_context.sh) prints Git status, the
current plan, recent journal entries, issues and PRs, and information about a
local wiki clone when present. The [orientation skill](../.agents/skills/hild-orient/SKILL.md)
tells the agent how to present this information to the researcher.

- **Codex:** Project hooks use `.codex/hooks.json` in a *trusted* project.
  Codex may require the human to explicitly trust hooks. Copying a valid JSON
  file is not sufficient evidence that it ran. The hook invokes the shell
  collector from the Git root.
- **Claude Code:** Project hooks live in `.claude/settings.json` and can
  supply startup context and reminders during conversation compaction.
  The provided template must be **merged carefully** with existing settings,
  never overwrite them.
- **Copilot:** Repository hooks use `.github/hooks/*.json`; a
  `sessionStart` command can run the collector. GitHub's documentation says
  that hook stdout may be ignored by the Copilot CLI, so running this hook
  **does not guarantee** that the agent receives an orientation. Use the
  `hild-orient` skill or startup prompt as the reliable fallback.
  The template is for Unix shells; native Windows operation is untested.

If an agent has no working hook, open a chat with repository access and
explicitly request `hild-orient`. **No HILD procedure requires a hook to
function**; the hook only reduces the work of gathering facts.

## How to verify an installation

1. Check the selected platform configuration exists, parses, and points to
   the intended shared skills/scripts; unselected configurations should not
   be installed by HILD.
2. In a fresh session with the selected agent, ask it to identify HILD,
   load `hild-scope` and `hild-orient`, and report what actually ran.
3. Observe whether an actual startup hook fired and whether the agent used
   its information. Record separately: **installed**, **discovered**,
   **executed**, and **used by the agent**.
4. Report skipped or unsupported behavior honestly. Do not count source
   documentation or mechanically valid JSON as a successful agent session.

## References

- [Claude Code skills](https://code.claude.com/docs/en/skills) and
  [hooks](https://code.claude.com/docs/en/hooks)
- [GitHub Copilot skills](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills)
  and [hooks](https://docs.github.com/en/copilot/concepts/agents/hooks)
- [Codex repository-local skills](https://developers.openai.com/blog/skills-agents-sdk)
  and [project hooks](https://developers.openai.com/docs/hooks)

Later installation work must preserve existing settings and explicitly report
which compatibility tests were actually performed.
