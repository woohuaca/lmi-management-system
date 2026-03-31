# Storage System

Use this reference when the user wants a repeatable way to store plans, reviews, unfinished work, ideas, and stable project knowledge.

## Recommended Working Rhythm

- `Role Goal Clarifier`: reviewed less often, usually per quarter or when responsibilities change
- `Monthly Plan`: created at the start of the month
- `Weekly Plan`: created before the week begins
- `Daily Work Plan`: created at the start of the day
- `Daily Review`: done before ending the day
- `Weekly Review`: done at the end of the week
- `Monthly Review`: done at the end of the month
- `Role Review`: done monthly or quarterly

## Overall Workflow

Use this planning and review loop:

`Role Goal Clarifier -> Monthly Plan -> Weekly Plan -> Daily Work Plan -> Daily Review -> Weekly Review -> Monthly Review -> Role Review`

Use `Time Image` and `Stats Analysis` as correction tools when time use drifts away from the intended plan.

## Task Classification

For daily execution, classify items as:

- `A`: important items
- `B`: urgent items
- `C`: contact or follow-up items
- `D`: meetings, discussions, or coordination items

This classification is for deciding attention, not just for labeling.

## Recommended Storage Pattern

If the user has an OpenClaw memory workspace, store planning and review notes in markdown files with absolute dates.

Suggested structure:

- `memory/YYYY-MM-DD.md`: raw daily log and lightweight daily review
- `memory/日报归档/YYYY-MM-DD_工作日志.md`: cleaned daily work log
- `memory/周复盘-YYYY-MM-DD-YY.md`: weekly review
- `memory/月复盘-YYYY-MM.md`: monthly review
- `memory/角色复盘-角色名-YYYY-MM.md`: role review
- `memory/项目事实/...`: stable project facts and validated conclusions
- `memory/长期偏好/...`: stable user preferences and working rules

## Managing Unfinished Work And New Work

At the end of each day, every unfinished item should be actively re-decided instead of automatically rolling forward.

Allowed outcomes:

- move to tomorrow
- move to later this week
- delegate or follow up
- delete or stop

For newly added work, classify it first as `A/B/C/D` before deciding whether it deserves space in the day or week.

## Managing Role Goals

Role goals should not stay only in the role clarification table.

Recommended flow:

- `Role Goal Clarifier`: define role value, responsibilities, key results, and high-return activities
- `Monthly Plan`: choose which role goals matter this month
- `Weekly Plan`: choose which role goals get real movement this week
- `Daily Work Plan`: decide which concrete action advances the chosen role goal today
- `Monthly Review` and `Role Review`: check whether time, results, and role definition still align

This is how role goals become real execution instead of a static reference sheet.

## Managing Insights, Reflections, And Ideas

Keep these categories separate:

- `Daily or Weekly Reflection`: lessons, observations, emotional or execution reflections
- `Ideas`: unvalidated thoughts, creative directions, possible experiments
- `Project Facts`: validated conclusions, confirmed decisions, stable project knowledge

Recommended handling:

- record reflections in daily or weekly review files
- capture ideas in the daily log first, then review them weekly
- only move an item into `项目事实` after it is validated or confirmed
- move stable personal working patterns into `长期偏好`

## Storage Rules

- One file should serve one review level whenever possible.
- Use absolute dates in every file name.
- Separate facts from interpretations.
- Keep daily files lightweight; move durable conclusions into long-term or project files.
- Weekly and monthly reviews should summarize, not just repeat daily logs.
- Do not store raw ideas directly as project facts.
- Do not let unfinished tasks roll forever without a new decision.

## Current Workspace Observation

In the current setup, the main workspace already uses:

- `memory/YYYY-MM-DD.md`
- `memory/日报归档/YYYY-MM-DD_工作日志.md`
- `memory/周复盘-...md`
- `memory/项目事实/`
- `memory/长期偏好/`

This means the best next step is to add:

- `月复盘-YYYY-MM.md`
- `角色复盘-角色名-YYYY-MM.md`

without redesigning the whole storage system.
