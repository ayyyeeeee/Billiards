---
name: hild-digest
description: Audit repo understandability, stale material, duplicated rules, neglected decisions and understanding-map freshness, and propose a bounded cleanup. Use for periodic repo reviews and requests to inspect hygiene.
---

# Digest

The aim is a project the human researcher can readily understand. Authoritative criteria come from the host's established `AGENTS.md` and [HILD process](../../../HILD/process.md). **Do not duplicate a separate hygiene rulebook in this skill.**

1. **Understanding map:** when configured, pull fast-forward and check code pages for staleness using `HILD/scripts/wiki_status.py` if installed; record missing pages and open understanding-debt issues. Create/update issues and wiki status only as authorized by the project's agreed scope. Report missing tooling rather than pretending this check ran.
2. **Review the repository:** examine tracked files (`git ls-files`), plan, decisions, code, relevant wiki pages, PRs and tests. Look for obsolete or unused files, the same rule written in multiple places, confusing names, missing test evidence, conflicting claims and changes awaiting review. Judge them against the project's own rules.
3. **Report before making changes:** say whether the repository is getting easier or harder to understand. For each important problem, give its location, the relevant rule and a specific suggested fix. Identify things that can be simplified or removed.
4. **Follow up by agreement:** do not repair nontrivial issues merely because they were identified. Each approved fix gets a scope issue or joins an existing agreed scope. Record the audit milestone using `hild-journal`.

The original [digest procedure](https://github.com/opherdonchin/MotorAdpatationSBI/blob/main/.github/skills/digest/SKILL.md) and this HILD adaptation describe the same review process; the process file, not this skill, remains the rule authority.
