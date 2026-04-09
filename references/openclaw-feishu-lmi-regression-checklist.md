# OpenClaw + Feishu + LMI Regression Checklist

Use this checklist whenever changing:

- Feishu account routing
- `main` / `azai` agent ownership
- LMI cron jobs
- LMI memory paths
- LMI generator scripts
- OpenClaw upgrades or plugin changes

This checklist exists to prevent "it runs in the backend but looks wrong in Feishu" bugs.

## Success Standard

A change is only considered complete when all 4 layers match:

1. Config is correct
2. Backend execution is correct
3. Delivery target is correct
4. User-facing Feishu experience is correct

If any one of these fails, the change is not done.

## Layer 1: Config Check

Confirm the intended ownership first.

### LMI ownership

The intended steady-state design is:

- `azai` owns all LMI work
- `main` does not own LMI cron jobs
- `workspace-azai/memory` is the primary LMI memory source

### Must-check items

- `openclaw.json`
  - Feishu account routing
  - `main` account routes to `main`
  - `azai` account routes to `azai`
- `jobs.json`
  - each LMI cron has `agentId = azai`
  - each LMI cron has `delivery.accountId = azai`
  - non-LMI summary jobs are clearly named as non-LMI

### Expected LMI jobs

- `lmi-morning-plan`
- `lmi-evening-review`
- `lmi-weekly-plan`
- `lmi-weekly-review`

## Layer 2: Backend Execution Check

Do not stop at job config. Verify the actual run.

### Must-check items

- `openclaw cron list`
  - target status is `ok`
- cron run file
  - confirm latest run belongs to the expected job
- agent session file
  - confirm the session is under the expected agent directory
  - confirm the working directory matches the intended workspace
- script execution
  - confirm the run called the intended generator script

### Pass examples

- `lmi-morning-plan` should create a session under `agents/azai/sessions`
- daily scripts should run from `workspace-azai`
- output should mention `workspace-azai/memory` as the source

## Layer 3: Delivery Check

The content may be correct and still arrive in the wrong place.

### Must-check items

- cron run record
  - `deliveryStatus = delivered`
- delivery target
  - verify the intended `to` target
  - verify the intended `accountId`
- if testing by message send
  - verify the message reaches the expected recipient without cross-app errors

### Failure patterns to watch for

- `status = ok`, but `deliveryStatus = not-delivered`
- `open_id cross app`
- delivery succeeds, but message lands in an unexpected Feishu conversation context

## Layer 4: Feishu Experience Check

This is the most important final check.

The user should be able to answer yes to all of these:

- I received the message in the expected conversation
- It looks like it came from the expected bot
- The content type matches the intended workflow
- It does not look like another agent or another thread took over

If the backend says `azai` but the user experience still looks like `main`, treat that as a real bug.

## LMI-Specific Content Check

### Daily plan

Expected structure:

- `Imported From Yesterday`
- `A`
- `B`
- `C`
- `D`
- `Schedule`
- `Todays Completed Items`
- `Daily Review`
- `Next 1-3 Moves`

Expected behavior:

- import from yesterday's review and unfinished items
- prefer `workspace-azai/memory`
- show missing inputs honestly instead of inventing facts

### Daily review

Expected structure:

- `Daily Snapshot`
- `Completed Items`
- `Attention Drift Review`
- `Adjustment Decisions`
- `Tomorrow First Move`
- `Next 1-3 Moves`

### Weekly plan

Expected structure includes:

- `Weekly Snapshot`
- `Weekly Top Goals`
- `Role Focus`
- `High-Return Activities`
- `A / B / C / D`
- `Week-End Review Hooks`

### Weekly review

Expected structure includes:

- `Weekly Snapshot`
- `Plan Vs Actual`
- `Role Review`
- `High-Return Activity Review`
- `Root Cause Review`
- `Lessons And Insights`
- `Carry Forward Decisions`
- `Next Week GPS Preview`

## Memory Check

After any LMI memory migration, verify:

- `workspace-azai/memory` contains the active LMI files
- scripts prefer `workspace-azai/memory`
- fallback to `workspace-main/memory` is temporary and intentional
- current day files exist when testing import-forward behavior

Common false alarm:

- the system is working correctly, but yesterday's file does not exist
- this causes "missing" or "待补充" output
- this is a data gap, not a routing bug

## Required Manual Test Set

After meaningful changes, run this minimum set:

1. Trigger `lmi-morning-plan`
2. Trigger `lmi-evening-review`
3. Trigger `lmi-weekly-plan`
4. Trigger `lmi-weekly-review`
5. Send a direct message to `azai`
6. Confirm Feishu-side appearance for at least one cron message and one direct reply

## Final Acceptance Rule

Do not say "fixed" until all of the following are true:

- config ownership is correct
- actual session ownership is correct
- delivery succeeds
- the user sees the expected bot and expected conversation behavior

## Current Intended Architecture

- `main`
  - general assistant
  - non-LMI summaries or reminders
- `azai`
  - LMI planning and review
  - daily / weekly / monthly / role workflow
- `workspace-azai/memory`
  - primary LMI memory home

