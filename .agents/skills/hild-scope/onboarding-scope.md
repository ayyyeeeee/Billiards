# Onboarding: introduce HILD and develop a useful first scope

**Read this companion when a researcher is new to HILD, asks for guidance
getting started, or wants an onboarding scope.** It is the authoritative
procedure for newcomer-facing conversations **before or after installation**,
not a separate agent skill.

The [HILD process](../../../HILD/process.md) governs all work agreements,
reviews and approvals. The [hild-scope skill](SKILL.md) handles ordinary
scoping; [hild-integrate](../hild-integrate/SKILL.md) handles read-only
assessment and installation. This file describes what onboarding adds.

## First contact: explain HILD in the researcher's context

Introduce HILD as a way to develop scientific software with an AI coding
agent while keeping the researcher in control of decisions and supporting
a deep understanding of the code and algorithms.

**Explain where HILD lives and what happens in practice.** HILD is adopted
*into the researcher's own Git repository*. It adds process instructions,
agent skills and optional hooks, along with plans, journals and decision
records. The researcher and agent use GitHub issues to agree on bounded
work and pull requests to examine and approve proposed changes. A separate
GitHub wiki can document important concepts, code and the researcher's
understanding. Coding agents carry out the agreed work using the repository,
its development tools and GitHub; HILD is a development process and toolkit,
rather than a continuously running service.

Connect those practices to **the researcher's existing goals and repository**.
Ask what they want to build only when it is not already clear. For a nearly
empty repository, installing HILD can itself become a useful first project
step. For an established repository, explain how HILD can work with what
is already there.

Help the researcher see why a **scope** is a natural first step: they and
the agent agree on a manageable piece of work before any changes are made.
Invite them to develop that first scope together.

An example of an introduction (adapt to the actual project; **not a script
to recite**):

> HILD helps you develop scientific software with an AI agent while
> keeping control of what gets built and understanding how it works.
> We'll agree on small pieces of work, review changes, and preserve
> important decisions and explanations so the project stays understandable.
>
> Your repository is currently almost empty, so we could learn HILD while
> preparing it for the project you want to build. Would you like us to
> develop our first scope together?

The first conversation should give the researcher a reason to care and a
clear invitation. Save implementation detail for decisions that need it,
and offer to explain further whenever it would help.

**Set expectations for access early, without turning them into a
prerequisite questionnaire.** HILD works best when the agent can read and
change the project's Git files and can use GitHub to create issues and
pull requests. A wiki may require additional access later if the researcher
chooses to use it. Briefly explain this at a suitable early point; offer to check readiness
now **or** defer checking until an operation needs access, depending on
the conversation. Avoid making this another required question. The researcher
need not configure every permission before developing the first scope;
some steps may be completed through an agreed manual GitHub handoff.
If an access check is requested or a step fails, use the
[GitHub-access companion](../hild-integrate/github-access.md).

## After the researcher says yes to developing a scope

First build a shared **goal**, then let boundaries, evidence and autonomy
emerge from the conversation. For a researcher who has already said they
want to learn HILD by installing it, the following is an approved example:

> Great. Let's develop our first scope together.
>
> In HILD, a scope is an agreement about a manageable piece of work. We
> start by agreeing on what we want to achieve, then decide what belongs
> in that work, what should wait, and how we'll know we've succeeded.
> Once we're satisfied, we'll record the agreement as a GitHub issue.
>
> You've said you want to learn HILD while installing it in your
> repository. I suggest our first scope have two outcomes: a repository
> ready to use HILD, and a first experience making and reviewing
> decisions together about how the work should proceed.
>
> Does that capture what you'd like to accomplish, or is there
> something else you want to get out of this first scope?

Follow the researcher's answer and develop the next consequential choice
together. The goal is a shared agreement, not a predetermined questionnaire.
Only once the researcher agrees on the **completed scope** should the agent
record and begin it under the ordinary process.

## During onboarding: surface useful choices

As decisions become relevant, explain the recommended default and why it
might help this project:

- **Where knowledge lives:** Will the default `HILD/` process, plan, journal
  and decision files work, or should established authoritative files stay
  where they are?
- **What supports understanding:** Are the default PR explanations and
  journal formats useful, or does the work call for different information?
- **Which agents to support:** Which AI coding agents does the researcher
  use? HILD can keep a single set of skills while configuring those agents.
- **Understanding map:** Should a fresh wiki be established to explain
  important concepts and code? If a wiki already exists, preserve it and
  address integration through a separately agreed scope.

A researcher may accept the defaults without making every choice into a
formal decision. Substantial customization can become future work. Record
a consequential choice when its rationale will matter later.

## From setup to productive development

**Check the installation state before deciding on the first task.**

- **Not installed:** suggest a reviewed HILD installation as a practical
  first scope, if that serves the researcher's goal.
- **Installed and verified up to date with the selected upstream revision:**
  ask what the researcher wants to accomplish next, unless they already
  said. Offer one or two useful suggestions grounded in the repository,
  and develop a small real task together.
- **Installed but older, locally changed or of uncertain provenance:**
  first help the researcher understand that state and whether updating
  is worth addressing now. Refer to `hild-integrate` for the read-only
  comparison. Preserve local changes; never assume an automatic upgrade
  is available.

Choose and shape the first task **with the researcher**. The ordinary
process introduces issues, PRs, explanation, review and journaling at
the appropriate time; onboarding need not teach the whole workflow upfront.

For an onboarding PR, suggest a `Process-HILD` wiki page explaining HILD
*in this repository*, with links to its authoritative files. If approved,
draft it **after the PR merges**. Only the researcher may confirm a page
as `understood`.

**Installation integrity** checks files and configuration; **onboarding
validation** observes whether the agent and researcher actually followed
the agreed process. Record which capabilities were demonstrated, blocked
or untested. A later fresh session should try recovering state from the
plan and journal. Onboarding is recommended, not required for every update.

## When a practical step is blocked

Investigate what tools or access are available. Explain the simplest
feasible path and help the researcher use it. For GitHub, Git checkout or
authentication problems, load the on-demand
[GitHub-access companion](../hild-integrate/github-access.md). A missing
local checkout matters when installation becomes the agreed next action;
keep the dialogue centered on the researcher's goal.

Before modifying an existing wiki or installing over existing process
files, establish a separate approved plan that preserves that work.
Treat unobserved agent startup behavior as unverified, even when its
configuration files are present.
