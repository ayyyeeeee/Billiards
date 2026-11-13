# GitHub access: diagnose the next blocked action

**Load this companion when GitHub or local checkout access needs checking
or repair** during HILD integration or onboarding. It can also support
an optional readiness check requested by the researcher. It is shared
by [hild-integrate](SKILL.md) and
[onboarding](../hild-scope/onboarding-scope.md); it does not replace
[HILD's approval rules](../../../HILD/process.md).

The goal is to help the researcher **continue their own project**.
Identify the next useful operation, establish what the agent can already
do, and work toward the smallest necessary remedy. Avoid a full
environment audit when one capability is all that is needed.

## First identify the action and environment

Find out what is failing, or what the researcher wants to verify:
- Read or edit files in the **working repository**
- Create or comment on **issues or pull requests**
- Create a branch, commit or **push**
- Read or update the **GitHub wiki**, if that is part of the agreed work

Then identify how **this agent** accesses GitHub. Use accessible evidence,
asking one targeted question if needed. Examples include:
- A coding agent in a local editor or terminal (VS Code, Codex CLI,
  Claude Code), potentially using SSH to a remote development machine
- A hosted/cloud coding agent or a GitHub Codespace with its own shell
- An agent with a connected GitHub tool/API but **no local Git checkout**
- An agent and researcher using the GitHub website to perform some
  steps manually

These are **examples, not an exhaustive platform list or a ranking**.
Tool availability depends on the specific installation and permissions,
not just the agent's brand.

A signed-in browser, a connected GitHub app, the researcher's terminal,
the agent's tool environment and Git's own push credentials may all
differ. Test the capability required for the next approved step;
do not conclude that all GitHub access works or fails from one result.

## Diagnose through the access route actually available

**Connected GitHub tool or hosted agent, without a shell:** Identify the
repo and check what the available connector/tool can **read**. Review
its declared permissions if exposed. Use its supported GitHub actions
for the agreed workflow; do not demand a local clone or `gh auth login`
if a working connector is sufficient. Conversely, API access does not
establish the ability to run a *local* installation script. If the
needed operation is not supported, explain the limitation and discuss
a suitable environment or a researcher-operated GitHub UI step.

**Agent with a terminal and Git checkout:** First find the real working
directory rather than assuming a checkout is absent because a command
was run from a scratch directory:

```sh
pwd
git rev-parse --show-toplevel
git status --short
git remote
```

These are read-only diagnostics. Confirm that the resolved Git root
and remote refer to the **intended target repository**, not upstream
HILD or another project. If `git rev-parse` fails, locate the workspace
directory or ask where the checkout is. Inspect a remote URL only when
needed, and **redact embedded credentials before displaying or sharing
it**.

**If GitHub CLI (`gh`) is installed and relevant**, check its own
authentication before suggesting a login:

```sh
gh auth status
gh api repos/OWNER/REPO --jq '{full_name, permissions}'
```

Replace `OWNER/REPO` with the confirmed target. The second command
requires access and is read-only. A successful GitHub GET demonstrates
some read capability, **not** permission to create issues, open PRs or
push. Do not create dummy GitHub issues or commits solely to test
write permissions; exercise the real operation only after its HILD
approval gate.

If the tools, the researcher's terminal and the agent's own subprocess
report inconsistent results, **compare the environments before changing
authentication**. Shell users can check *presence only*, not values,
of GitHub CLI's token variables:

```sh
for n in GH_TOKEN GITHUB_TOKEN; do
  if test -n "$(printenv "$n")"; then
    printf '%s is set\n' "$n"
  else
    printf '%s is unset\n' "$n"
  fi
done
```

GitHub CLI honors `GH_TOKEN` and `GITHUB_TOKEN` ahead of stored
credentials. Their presence or identity can differ between terminals,
containers, SSH hosts and agent processes.

## Pick one appropriate recovery path

- **Wrong directory or missing checkout:** Locate the existing workspace
  or establish an appropriate clone *after agreement*, preserving
  uncommitted work. A GitHub API-connected agent may need a separate
  terminal environment only when an approved step requires it.
- **Issue or PR permissions missing:** Check the authenticated identity,
  target repository, credential scopes, and organization policy. Use a
  supported connected GitHub tool if it already has the needed rights,
  or offer a researcher-operated GitHub UI step. Explain any permission
  changes before requesting them.
- **CLI reports no usable login:** If `gh` is required and there is
  no working credential, explain the supported login options for the
  current environment. A browser login can be initiated by the
  researcher with `gh auth login --hostname github.com --git-protocol https --web`.
  If an inherited token prevents interactive login, one *optional*
  approach—with consent—is to omit the variables **for that command
  only**, instead of clearing them permanently:

  ```sh
  env -u GH_TOKEN -u GITHUB_TOKEN gh auth login --hostname github.com --git-protocol https --web
  ```

  Confirm `gh auth status` afterward in the **agent's actual execution
  environment**. Login stores or changes credentials, so explain that
  side effect. Do not ask anyone to paste a token or device code.
- **`gh` API works but `git push` fails:** Inspect whether the
  remote uses SSH or HTTPS and which Git credentials apply. When
  appropriate, `gh auth setup-git` can configure an authenticated
  GitHub CLI as an HTTPS Git credential helper, with the researcher's
  agreement; it changes Git configuration. Diagnose SSH separately
  rather than switching protocols blindly.
- **Wiki access missing:** Establish whether the repository has an
  initialized wiki and whether the current tool supports wiki writes.
  A wiki is an additional, separately authorized step; it is **not
  a prerequisite for the first read-only assessment or installation**.
  If tools cannot edit it, explain an appropriate manual review/edit
  handoff or a later scoped setup rather than claiming it was updated.

### Environment-specific notes, only when relevant

- **Local editor, terminal, or SSH:** The local repository, editor chat,
  SSH shell and credential store may be distinct. Run diagnostics in
  the environment **the agent uses to act**.
- **GitHub Codespaces:** The checkout is commonly under
  `/workspaces/REPO`. GitHub may provide a repository-scoped token;
  token availability in the user's interactive shell does not prove
  availability in the agent's execution environment. Verify both when
  they disagree.
- **Hosted agents or GitHub connectors:** Look for supported GitHub
  actions and their permissions before proposing CLI configuration.
  They may have no shell and still manage issues or PRs.

These notes are starting points, not claims of support for every product
version. Consult maintained platform documentation for actual behavior.

## Security, consent and return to HILD

Keep any explanation concrete and brief. Recommend **one next action**,
with alternatives when their tradeoffs matter.

- Never request or publish credentials, private keys, device codes or
  raw `gh auth token` output in chat, terminal logs, issues or PRs.
- Avoid embedding credentials in Git remote URLs or commits.
- Explain and seek agreement for login, credential storage, Git config
  changes, new clones, permissions, or any other consequential action.
- After recovery, verify the **specific blocked capability**, and say
  what is still unverified. Resume at the original HILD review gate:
  repairing GitHub access never grants approval to create or implement
  a scope, install HILD, or merge a PR.

## Maintained references

- [GitHub CLI environment variables](https://cli.github.com/manual/gh_help_environment)
- [GitHub CLI login](https://cli.github.com/manual/gh_auth_login)
- [GitHub CLI Git credential helper](https://cli.github.com/manual/gh_auth_setup-git)
- [GitHub: Codespaces repository authentication](https://docs.github.com/en/codespaces/troubleshooting/troubleshooting-authentication-to-a-repository)

Use the documentation of whichever agent/editor/host actually applies;
the listed GitHub documents are not a substitute for platform-specific
evidence.
