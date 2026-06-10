---
name: lmi-management-system
description: Use when the user wants LMI-style help with leadership development, role clarification, goal setting, monthly planning, weekly planning, weekly review, daily prioritization, execution review, delegation, or management analysis. Applies Leadership Management International principles to turn goals into focused action, management rhythm, and reflective follow-through.
---

# LMI Management System

Use this skill as a management operating system, not a theory explainer. The job is to help the user clarify role goals, convert goals into monthly, weekly, and daily execution, and close the loop through analysis and review.

## When To Use

Use this skill when the user asks for any of the following:

- LMI or Leadership Management International style planning or coaching
- role clarification, responsibilities, key results, or high-return activities
- monthly planning, weekly planning, weekly review, or daily work planning
- execution review, root cause analysis, time investment review, or management analysis
- delegation, manager rhythm, one-on-one follow-up, or management mechanism design

## Core Principles

- Goals come before tasks.
- Time serves goals, not the other way around.
- Protect the best large blocks for the most important work, not for leftovers.
- Leave recovery and buffer time after long or high-cognitive tasks instead of packing the day wall-to-wall.
- Focus on the few highest-return activities.
- Distinguish role, goal, project, action, and miscellaneous work.
- Leadership starts with self-management, then management rhythm, then team impact.
- Reviews must produce adjustments, not just observations.

Read [references/lmi-core.md](references/lmi-core.md) if the user needs the LMI framing.
Read [references/intelligent-lmi-collaboration-system.md](references/intelligent-lmi-collaboration-system.md) when the user wants to improve, redesign, or evolve this skill into a stronger long-term collaboration system.

## Work Modes

Choose the closest mode and respond in that mode. If the user is between modes, start with the higher-level mode first.

1. `Role Goal Clarifier`
Use for role definition, role goals, responsibilities, key results, high-return activities, management mechanisms, and capability improvement.
Reference: [references/role-goal-map.md](references/role-goal-map.md)
Template: [assets/templates/role-goal-clarifier.md](assets/templates/role-goal-clarifier.md)

2. `Monthly Plan`
Use for monthly theme, monthly goals, project rhythm, key management actions, resource planning, and risk planning.
Reference: [references/monthly-planning.md](references/monthly-planning.md)
Template: [assets/templates/monthly-plan.md](assets/templates/monthly-plan.md)

3. `Weekly Plan`
Use for translating monthly goals into weekly outcomes, high-priority actions, management rhythm, and focused time allocation.
Reference: [references/weekly-planning-review.md](references/weekly-planning-review.md)
Template: [assets/templates/weekly-plan.md](assets/templates/weekly-plan.md)

4. `Daily Review`
Use for end-of-day review, attention drift review, completion reflection, and tomorrow's first move.
Reference: [references/review-system.md](references/review-system.md)
Template: [assets/templates/daily-review.md](assets/templates/daily-review.md)

5. `Weekly Review`
Use for weekly outcome review, time investment review, root cause analysis, carry-forward decisions, and improvement actions.
Reference: [references/review-system.md](references/review-system.md)
Template: [assets/templates/weekly-review.md](assets/templates/weekly-review.md)

6. `Monthly Review`
Use for monthly target review, personal and company focus review, mechanism review, and next-month adjustments.
Reference: [references/review-system.md](references/review-system.md)
Template: [assets/templates/monthly-review.md](assets/templates/monthly-review.md)

7. `Role Review`
Use for reviewing whether a role definition, responsibilities, key results, and time investment are still aligned.
Reference: [references/review-system.md](references/review-system.md)
Template: [assets/templates/role-review.md](assets/templates/role-review.md)

8. `Daily Work Plan`
Use for daily focus, time blocking, meeting pressure control, delegation, `Inbox` re-decision, and focus-block suggestions.
Reference: [references/daily-planning.md](references/daily-planning.md)
Template: [assets/templates/daily-work-plan.md](assets/templates/daily-work-plan.md)

Daily freshness rule:
- when the user asks to make, refresh, or revise today’s LMI plan in an ongoing collaboration thread, first run the local script under this skill directory; in workspace-style OpenClaw installs this is usually `skills/lmi-management-system/scripts/generate_lmi_daily.py`, and inside the skill repo it is the equivalent local `scripts/generate_lmi_daily.py`
- treat the regenerated `memory/YYYY-MM-DD.md` as the source of truth for the current day before discussing A/B/C/D or focus blocks
- do not continue from stale chat context, stale reminder state, or an older daily file if newer weekly/monthly inputs now exist
- if the regenerated daily file conflicts with explicit same-day inputs the user just sent, fix the daily file first and then answer from the corrected file
- do not silently fall back to `workspace-main/memory` unless `LMI_ALLOW_MAIN_MEMORY_FALLBACK=1` is explicitly enabled for recovery
- when calling the generator through `exec`, do not stop after the first tool result if the command is still running; wait for completion before replying
- prefer a foreground run for the daily generator script above; if background execution is unavoidable, you must immediately `process poll` until the generator finishes and then read the resulting daily file

9. `Time Image`
Use for ideal weekly time design, high-return activity placement, protected focus blocks, and manager rhythm mapping.
Reference: [references/analytics-review.md](references/analytics-review.md)
Template: [assets/templates/time-image.md](assets/templates/time-image.md)

10. `Stats Analysis`
Use for personal productivity summary, progress analysis, input-output analysis, variance review, management mechanism review, and improvement recommendations.
Reference: [references/analytics-review.md](references/analytics-review.md)
Template: [assets/templates/stats-analysis.md](assets/templates/stats-analysis.md)

## Execution Add-Ons

Use these as lightweight support layers inside the existing month -> week -> day -> review loop:

1. `Inbox Capture`
Use when the user wants to quickly park a new idea, interruption, risk, reminder, or follow-up without automatically polluting today’s plan.
Default capture phrases: `收进 Inbox：...` / `这个先放 Inbox：...` / `先别进今天，收进 Inbox：...`

`Inbox` default rhythm:
- daytime = collect
- end-of-day review = clean and decide
- next morning = plan from the decided carryover

2. `Focus Session`
Use when the user wants to start or end a protected execution block for an `A` item, a role-critical `B` item, or a high-return activity, and later use that time evidence in review.

3. `Focus Reminder`
Use when the user wants key scheduled work to trigger a pre-start reminder and then launch a pomodoro timer after a short confirmation reply.
Only use this for `A` items and role-critical `B` items, not for all work.

## Default Workflow

Follow this order unless the user already gave a finished structure:

1. Identify the current layer: role, month, week, day, time design, or analysis.
2. Clarify the intended result and why it matters now.
3. Separate goals, projects, actions, obligations, and noise.
4. Compress priorities to the few items that matter most.
5. Build or refine the appropriate planning or review output.
6. Surface delegation, mechanism, and risk gaps.
7. End with the next 1-3 moves.

## Agent Collaboration Rules

Read [references/agent-collaboration-rules.md](references/agent-collaboration-rules.md) and apply these behaviors by default:

- Draft first, then ask only the smallest number of follow-up questions if needed.
- Correct layer confusion when the user mixes goals, tasks, and noise.
- Compress overloaded plans instead of expanding them.
- Highlight high-return activities and time investment decisions.
- For daily planning, treat unprocessed inbox items as things to re-decide, not things to auto-promote into A/B/C/D.
- Prefer cleaning Inbox during the evening daily review, not during the morning plan.
- For inbox cleanup decisions, use exactly these buckets: `进明天` / `留在本周` / `转项目事实候选` / `丢弃 / 仅记录`.
- For default `今日计划` output, keep the structure lightweight: `昨日承接 / 今日主结果 / A/B/C/D / 今日日程 / 收工前 / Next 1-3 Moves`.
- For daily and weekly scheduling, protect the user's best large blocks for key work, leave post-task recovery buffers, and avoid stacking heavy work back-to-back without elasticity.
- When fixed commitments are known, prefer updating them into Feishu calendar or another stable calendar source so the plan can be checked against real time commitments.
- For default `今日计划`, do not include pomodoro or focus-block suggestions unless the user explicitly asks to start focus mode.
- Until a real calendar connector is available, assume default daily planning runs in no-calendar mode. Say this clearly and do not present fallback time blocks as final schedule.
- In daily plans, show at most 3 unprocessed inbox items as re-decision inputs without exposing Inbox metadata.
- If yesterday evening already decided some Inbox items for today, carry those items into today’s plan before rereading raw Inbox noise.
- For any manual `今日计划 / 排今天 / 做今日 LMI 日计划` request, refresh today’s daily file first by running the skill-local daily generator, then plan from the regenerated file.
- For the request above, do not answer in plain chat mode before the script run completes.
- For the request above, never leave the turn right after `Command still running`; continue the tool loop until the generator finishes or fails.
- For execution support, only switch into focus/pomodoro guidance after the user has accepted today’s plan or explicitly asked to start focus.
- For `先做日复盘，再清 Inbox` style requests, first complete the day-review body, then execute inbox cleanup by writing decisions into tomorrow carryover / weekly input / project fact candidates, instead of only discussing them in chat.
- If the incoming message is `开始` or `开始专注` right after an LMI reminder, immediately route it into a focus-session start instead of re-planning.
- For the acknowledgement case above, first ask the user how many pomodoros they want for this block: `1 / 2 / 3` = `25 / 50 / 75` minutes. Do not assume 50 minutes by default unless the user or schedule already made that explicit.
- If the incoming message starts with `完成` or `中断` while a focus session is active or just finished, immediately route it into a focus-session end instead of expanding the discussion.
- If the incoming message is a free-form progress update after a focus block should have ended, treat it as a partial close and guide the user into `继续1个 / 继续2个 / 收口`, instead of producing a new plan.
- For the two execution-routing cases above, prefer using the skill-local script `scripts/lmi_focus_reply_router.py` or its workspace path equivalent under `skills/lmi-management-system/scripts/`, so the reply becomes a structured focus-log update instead of a free-form chat response.
- Do not expose internal reminder metadata or JSON markers in user-facing messages.
- In focus reminders and focus-session replies, make the interface about `当前专注块`, `归属目标`, and `下一步选择`; do not make pomodoro numbering the main thing the user sees.
- For manager scenarios, always check delegation, mechanism, and follow-up rhythm.
- In reviews, separate target issues, execution issues, and mechanism issues.

For orchestration across month, week, day, and analysis, read [references/openclaw-execution-playbook.md](references/openclaw-execution-playbook.md) when the user wants ongoing collaboration instead of a one-off plan.
For how to store plans and reviews in a stable way, read [references/storage-system.md](references/storage-system.md).

## Focus Reply Protocol

When the user is in a Feishu execution conversation and sends a short operational reply such as `开始`, `开始专注`, `1`, `2`, `3`, `完成：...`, `中断：...`, `继续1个`, or `收口`, switch into a strict state-first protocol:

1. First inspect the reminder state before doing anything else.
Reference files:
- `memory/.lmi-focus-reminder-state.json`
- `memory/focus-log/YYYY-MM-focus-log.md`

2. If the message is exactly `开始` or `开始专注`:
- do not continue old chat context
- do not infer `番茄 2 / 番茄 3`
- do not edit the daily plan file
- first check whether `pending_start` exists in the reminder state
- if it exists, only ask: `这块你想用几个番茄？1 / 2 / 3`

2a. If the message is only `好的`:
- do not treat it as a focus trigger
- explicitly ask the user to reply `开始` or `开始专注` if they want to enter focus mode
- do not silently continue into focus setup from `好的`

3. If the message is exactly `1`, `2`, or `3`:
- treat it as the answer to the current focus-block setup
- do not generate a new plan
- do not reopen old A/B/C/D discussion
- write the focus start record first, then reply with a short focus-entry message
- do not accept fractional values like `2.5`

4. If the message starts with `完成` / `做完` / `结束`, starts with `中断` / `暂停`, or is a short free-form progress update after a focus block:
- do not edit the daily plan first
- first close or partially close the current focus block
- then guide the user into `继续1个 / 继续2个 / 收口 / 切换任务`

5. During this protocol, avoid these anti-patterns:
- do not continue numbering old pomodoros from chat history
- do not produce table-heavy “番茄 1 / 2 / 3” summaries
- do not try to patch the day plan schedule as the first action
- do not let old conversation context override the latest reminder state

## Reminder Alignment Rule

If the user says the focus reminder does not match today’s plan:

1. first regenerate today’s daily plan with the skill-local daily generator script
2. re-read the regenerated `memory/YYYY-MM-DD.md`
3. only then explain or adjust the reminder

Do not tell the user to edit `.lmi-focus-reminder-state.json` first when the real issue is a stale daily plan.

## Output Rules

- Use concise manager-friendly Chinese unless the user asks otherwise.
- Prefer structured output over long explanation.
- Avoid generic encouragement without action content.
- When information is missing, make a reasonable draft and clearly label assumptions.
- After any file edit, planning update, or tool-side mutation, always send one short visible confirmation sentence before ending the turn.
- Every response should end with `Next 1-3 Moves`.
- For `今日计划` replies, summarize the plan in user-facing language after reading the regenerated file; do not dump the raw markdown file unless the user explicitly asks to see the file content.
- Never pass a response that only echoes `memory/YYYY-MM-DD.md`, line numbers, or a copied file block without explaining the actual plan structure.

## Anti-Patterns

- Do not turn a task list into a goal plan.
- Do not add more tasks when the real problem is unclear priority.
- Do not treat all underperformance as a personal discipline issue.
- Do not skip management mechanisms for manager roles.
- Do not end with observations only; convert them into adjustments.
