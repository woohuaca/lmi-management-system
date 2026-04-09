# Azai-Owned LMI Migration Plan

## Goal

Move the LMI operating system to `azai` end-to-end while minimizing migration risk.

End state:

- `azai` owns all LMI planning and review workflows.
- `workspace-azai/memory` becomes the primary LMI memory store.
- `main` stops handling LMI planning/review flows.
- Daily/weekly/monthly/role LMI work uses one consistent memory source.
- Cron, direct chat, and skill behavior all point to the same agent and data source.

## Why This Plan Exists

Current state is inconsistent:

- LMI cron ownership is mostly on `azai`, but some summary flows still use `main`.
- Real LMI history is in `workspace-main/memory`.
- `workspace-azai/memory` is empty.
- Some interactions were previously routed to `main` because Feishu account bindings were mismatched.
- Users see split behavior: morning planning from `azai`, some summaries from `main`, and incomplete context import.

This plan avoids a risky "big bang" cutover.

## Design Principles

1. Copy first, switch later.
2. Keep rollback simple.
3. Do not delete working history during migration.
4. Separate LMI data from general assistant data.
5. Validate with real daily/weekly/role flows before cleanup.

## End-State Architecture

### Agents

- `azai`
  - Owns all LMI tasks
  - Owns LMI cron jobs
  - Uses `lmi-management-system` as the default planning/review skill for LMI requests
  - Reads and writes LMI records under `workspace-azai/memory`

- `main`
  - No longer owns LMI planning/review cron jobs
  - May still handle non-LMI summaries, general chat, and unrelated automations

### Memory Ownership

Primary LMI memory location:

- `/Users/woohuaca/.openclaw/workspace-azai/memory`

Historical source during migration:

- `/Users/woohuaca/.openclaw/workspace-main/memory`

### Cron Ownership

LMI-only cron jobs should belong to `azai`:

- `lmi-morning-plan`
- `lmi-evening-review`
- future weekly/monthly/role review reminders if added

Non-LMI summaries should either:

- remain clearly outside the LMI system, or
- be redesigned as LMI flows and then moved to `azai`

## Migration Scope

### Files To Migrate Into `workspace-azai/memory`

These are LMI-related and should move into `azai` ownership:

- daily work logs relevant to LMI planning and review
- weekly review files
- monthly review files
- role clarification review files
- role goal files
- quarter goal files that support LMI review
- LMI templates or norms that should live beside LMI memory

Based on the current source tree, the first migration wave should include:

- `2026-03-18.md`
- `2026-03-20.md`
- `2026-03-25.md`
- `2026-03-26.md`
- `2026-03-27.md`
- `2026-03-28.md`
- `2026-04-01.md`
- `3月角色澄清表复盘-2026.md`
- `Q2-OKR-2026.md`
- `Q2角色目标-2026.md`
- `周复盘-2026-03-24-28.md`
- `周复盘-2026-03-24-28-完整版.md`
- `角色澄清表-Q2目标-2026.md`
- `日报归档/2026-03-16_工作日志.md`
- `日报归档/2026-03-17_工作日志.md`
- `日报归档/2026-03-30_工作日志.md`
- `README_记忆写入规范.md`
- `模板/` (only if we want azai-local memory conventions)

### Files Not To Move In The First Wave

These should remain in `main` unless explicitly reclassified:

- unrelated project facts
- non-LMI long-term preferences
- general operating memory for `main`
- non-LMI cron state files

Examples to keep out of first-wave migration:

- `项目事实/制造业日报_*.md`
- `长期偏好/2026-03-13_家庭规则.md`

## Low-Risk Migration Phases

### Phase 0: Freeze The Architecture

Before moving files:

- confirm that all LMI cron jobs are owned by `azai`
- confirm that `azai` Feishu direct routing lands in `agent:azai`
- stop adding new LMI logic to `main`

Success criteria:

- new direct LMI chat with `azai` routes to `azai`
- morning/evening LMI jobs still run

### Phase 1: Copy, Do Not Move

Create the target structure under `workspace-azai/memory`.

Copy the LMI-related files listed above from `workspace-main/memory`.

Rules:

- preserve filenames
- preserve folder structure where useful
- do not delete originals
- keep a migration manifest

Success criteria:

- all selected files exist in `workspace-azai/memory`
- originals still exist in `workspace-main/memory`

### Phase 2: Switch LMI Readers To `workspace-azai/memory`

Update LMI scripts and prompts so that:

- daily plan reads `workspace-azai/memory`
- daily review reads `workspace-azai/memory`
- weekly review prompts prefer `workspace-azai/memory`
- role review prompts prefer `workspace-azai/memory`

Important:

- do not remove fallback support immediately
- if a file is missing in `azai`, the system may optionally log that gap and fall back to `main` during a short transition window
- that fallback should be temporary and explicit

Success criteria:

- azai can import yesterday's LMI review from its own memory tree
- no more `待补充` caused only by empty azai memory

### Phase 3: Validation Window

Run real validations before cleanup.

Required validations:

1. Daily plan validation
- trigger `lmi-morning-plan`
- confirm imported items come from `workspace-azai/memory`
- confirm output includes yesterday carry-forward items when available

2. Daily review validation
- trigger `lmi-evening-review`
- confirm it can write or summarize against `workspace-azai/memory`

3. Weekly review validation
- use a real weekly review request in `azai`
- confirm it finds prior weekly plan/review files from `workspace-azai/memory`

4. Role review validation
- use a role clarification review request in `azai`
- confirm it finds role review history and quarter goal files from `workspace-azai/memory`

Success criteria:

- all four validations produce complete outputs without depending on `workspace-main/memory`

### Phase 4: Tighten Ownership

After successful validation:

- update docs to state that LMI memory now lives under `workspace-azai/memory`
- stop LMI scripts from reading `workspace-main/memory`
- ensure new LMI notes are written only into `workspace-azai/memory`

Success criteria:

- azai is the single owner of LMI workflows and LMI memory

### Phase 5: Archive, Not Delete

Only after stable operation:

- leave historical copies in `workspace-main/memory` for an observation period, or
- move old LMI files into a clearly named archive folder under `workspace-main/memory/_legacy_lmi/`

Do not hard-delete until the new path has proven stable.

## Cron Design After Migration

### Keep

- `lmi-morning-plan` -> `azai`
- `lmi-evening-review` -> `azai`

### Reclassify

The current 17:00 summary job is not part of the LMI chain as currently designed.

Current issue:

- it is owned by `main`
- it reads only `HEARTBEAT.md`
- it does not read real LMI records

Recommended options:

1. Keep it as a non-LMI summary under `main`
2. Replace it with a real `azai` LMI evening review flow
3. Retire it if it duplicates the LMI daily review

Preferred option:

- retire or redesign it, rather than keeping a confusing parallel summary stream

## Data Model For LMI Under Azai

Recommended structure:

- `memory/YYYY-MM-DD.md`
- `memory/日报归档/YYYY-MM-DD_工作日志.md`
- `memory/周复盘-YYYY-MM-DD-YY.md`
- `memory/月复盘-YYYY-MM.md`
- `memory/角色复盘-角色名-YYYY-MM.md`
- `memory/角色目标/` (optional)
- `memory/模板/`

### Content Rules

- unfinished work must be re-decided, not auto-rolled
- role goals must map into monthly and weekly work
- insights belong in reviews
- ideas are captured first, then reviewed later
- validated project facts do not automatically belong in LMI memory unless they directly support role/goal review

## Rollback Plan

If validation fails:

1. revert LMI readers to `workspace-main/memory`
2. keep copied files in `workspace-azai/memory` for inspection
3. leave cron ownership on `azai` if routing is stable
4. do not delete anything from `main`

Rollback is intentionally simple because Phase 1 is copy-only.

## Implementation Order

Recommended execution order:

1. inventory and manifest the LMI files to migrate
2. copy selected files into `workspace-azai/memory`
3. adjust daily scripts to prefer `workspace-azai/memory`
4. validate daily plan and daily review
5. validate weekly review and role review
6. update docs and ownership notes
7. archive legacy LMI files in `main` only after stable observation

## What This Solves

This design removes the current split-brain behavior:

- `azai` owns LMI agent behavior
- `azai` owns LMI memory
- `main` stops being a hidden dependency for LMI
- cron and direct chat point to the same owner and same data source

## Current Decision

Chosen direction:

- Option 2: migrate LMI into `workspace-azai/memory`
- Migration strategy: copy -> switch -> validate -> archive
- Risk posture: minimize data loss and preserve rollback
