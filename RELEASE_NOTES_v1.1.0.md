# Release Notes v1.1.0

`lmi-management-system` v1.1.0 turns the original LMI planning and review skill into a more complete execution operating system.

The core LMI loop is unchanged: role goals still flow into monthly planning, weekly planning, daily planning, and review. This release adds the missing day-to-day execution layer around that loop.

## Highlights

- Inbox capture and cleanup workflow for ideas, interruptions, risks, reminders, and follow-ups
- Focus session workflow for protected `A` work and role-critical `B` work
- focus reminder support for pre-start nudges and pomodoro closeout prompts
- daily, weekly, monthly, and role generators now read Inbox and Focus memory
- `AGENTS.md` maintenance guide for future agents changing the skill
- stronger sync checking across source, OpenClaw, and Codex installed copies

## New Execution Layer

This release adds scripts and templates for:

- capturing incoming items without polluting today's plan
- cleaning Inbox into `tomorrow`, `this_week`, `project_fact_candidate`, or `archive`
- rebuilding Inbox from the operation log
- starting and ending focus sessions
- routing short focus replies such as `开始`, `1`, `完成：...`, and `收口`
- sending reminder prompts through a local OpenClaw / Feishu runtime

The intended rhythm is:

```text
daytime capture
-> evening Inbox cleanup
-> next-morning daily planning
-> protected focus execution
-> daily and weekly review
```

## Planning And Review Improvements

- Daily planning now considers decided Inbox carryover before raw Inbox noise.
- Weekly planning and weekly review now surface Inbox decisions and focus evidence.
- Daily review can feed tomorrow carryover, weekly input, and project-fact candidates.
- The newer templates make re-decision and carry-forward work more explicit.

## Operational Notes

The skill remains a local OpenClaw / Codex skill package. The planning and review scripts use the Python standard library.

Some optional execution features depend on the owner's local environment:

- OpenClaw command-line access
- Feishu account routing
- macOS LaunchAgent for recurring focus reminders
- local memory directories such as `workspace-azai/memory`

For portable use, pass explicit paths and runtime values where the scripts expose CLI arguments or environment variables.

## Validation

Release validation covered:

- Python AST parsing for all 14 scripts
- shell syntax checks for sync and LaunchAgent scripts
- Markdown internal link checks
- temporary-memory Inbox capture, cleanup, rebuild, and Focus start/end flow
- focus reminder dry-run
- OpenClaw skill discovery
- sync checking across source, OpenClaw, and Codex copies

## Upgrade Notes

If you already use `v1.0.0`, review:

- [README.md](README.md)
- [CHANGELOG.md](CHANGELOG.md)
- [references/inbox-focus-design.md](references/inbox-focus-design.md)
- [AGENTS.md](AGENTS.md)

Then reinstall or resync the skill into the active OpenClaw / Codex skill directories.
