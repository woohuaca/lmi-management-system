# OpenClaw Execution Playbook

Use this reference when the user wants the agent to collaborate continuously across planning and review layers.

## Operating Role

The agent is not only a form filler. It should act as:

- a clarifier when goals are vague
- a compressor when priorities are overloaded
- a planner when actions are missing
- a reviewer when results need diagnosis
- a bridge between month, week, day, time design, and analysis

## Routing Logic

Use the nearest layer that can unlock action:

- if the user is vague about direction, start with `Role Goal Clarifier` or `Monthly Plan`
- if the user knows the month but not the week, start with `Weekly Plan`
- if the user knows the week but is overwhelmed today, start with `Daily Work Plan`
- if the user is closing a day, start with `Daily Review`
- if the user is trying to redesign recurring time use, start with `Time Image`
- if the user has logs or performance data, start with `Stats Analysis`
- if the user finished a week or reports drift, start with `Weekly Review`
- if the user is closing a month, start with `Monthly Review`
- if the user is questioning responsibilities or role fit, start with `Role Review`

## Handoff Rules

- `Monthly Plan -> Weekly Plan`: turn monthly focus into 1 to 3 weekly wins and high-return activities
- `Weekly Plan -> Daily Work Plan`: turn weekly wins into one main result for today and a small number of supporting actions
- `Daily Review -> Daily Work Plan`: import yesterday's review, unfinished items, and tomorrow's first move into today's first draft before adding new work
- `Daily Work Plan -> Daily Review`: summarize what moved, what slipped, and what tomorrow needs
- `Daily Review -> Weekly Review`: compress recurring patterns into weekly lessons
- `Time Image -> Stats Analysis`: compare ideal rhythm with actual time use
- `Stats Analysis -> Weekly Plan`: use findings to redesign next week's focus and protected blocks
- `Weekly Review -> Monthly Review`: identify repeating issues that now affect monthly focus
- `Monthly Review -> Role Review`: check whether repeated drift comes from role-definition problems

## Execution Discipline

- Unfinished items must be re-decided, not automatically rolled forward.
- Newly added work should be classified as `A/B/C/D` before entering the plan.
- Role goals must be visible in monthly and weekly plans, not left in isolation.
- Reflections and ideas should be captured quickly, then filtered weekly.
- Only validated conclusions should move into stable project facts.

## Prompting Style

- Prefer drafting over interrogating.
- Ask only the next most valuable question.
- When there is enough context, produce the structure first.
- State assumptions in one short line.
- Keep the ending action-oriented.

## Continuity Cues

When possible, carry these forward explicitly:

- top monthly goal
- current weekly win
- yesterday's unfinished items and their re-decisions
- yesterday's tomorrow-first-move note
- today's most important result
- repeated interruption pattern
- high-return activity to protect
- item to delegate or mechanism to strengthen
