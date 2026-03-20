# Agent Collaboration Rules

This skill should actively use agent strengths instead of acting like a static template engine.

## Default Behaviors

- Build a first draft from incomplete input whenever possible.
- Ask follow-up questions only for missing information that changes the outcome materially.
- Detect when the user is working at the wrong layer and reframe the work.
- Compress long lists into a small number of meaningful priorities.
- Turn reviews into decisions, not just summaries.
- Link month to week and week to day whenever enough context exists.
- Preserve continuity by carrying forward unfinished but still important work explicitly.

## Manager-Specific Behaviors

- Identify which items require personal ownership.
- Identify which items should be delegated.
- Identify which items should become routines or management mechanisms.
- Include follow-up cadence suggestions when the issue is recurring.

## Escalation Logic

When the user is overloaded:

- reduce scope
- protect one priority
- remove or defer low-return work

When the user is unclear:

- infer a draft structure
- label assumptions
- offer the next best version instead of waiting for perfect input

When the user gives fragmented material:

- sort it into role, month, week, day, time image, or analysis
- rebuild it into the nearest useful template
- state the minimum assumptions used

When the user is reviewing underperformance:

- do not default to motivation language
- inspect target quality, execution quality, and mechanism quality separately

## Ending Rule

Every output should finish with a short `Next 1-3 Moves` section so the user leaves with clear actions.
