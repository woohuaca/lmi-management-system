# v1.1.0

`lmi-management-system` v1.1.0 adds an execution layer on top of the original LMI planning and review loop.

## What Changed

- Added Inbox capture, cleanup, rebuild, and archive support
- Added Focus session start/end logging and reply routing
- Added focus reminder support for pre-start nudges and closeout prompts
- Updated daily, weekly, monthly, and role generators to read Inbox and Focus memory
- Added `AGENTS.md` so future agents can safely maintain the skill
- Strengthened sync checking across source, OpenClaw, and Codex installed copies
- Added updated release notes and changelog coverage for the June 2026 release

## Why It Matters

The skill no longer stops at planning. It can now help capture interruptions, decide what carries forward, protect focused work, and feed execution evidence back into daily and weekly review.

## Validation

- Parsed all 14 Python scripts with `ast`
- Checked shell syntax for sync and LaunchAgent scripts
- Checked Markdown internal links
- Ran Inbox capture, cleanup, rebuild, and Focus start/end against temporary memory
- Ran focus reminder dry-run
- Verified OpenClaw skill discovery
- Verified source, OpenClaw, and Codex installed copies are in sync

## Notes

Optional reminder delivery still depends on a local OpenClaw / Feishu runtime. For portable use, pass explicit memory paths and runtime values where supported.

## Repository

GitHub: [woohuaca/lmi-management-system](https://github.com/woohuaca/lmi-management-system)
