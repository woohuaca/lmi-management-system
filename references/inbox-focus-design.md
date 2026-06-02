# Inbox And Focus Design

Use this reference when the user wants to add two execution-layer capabilities to the LMI system:

- `Capture Inbox`: a GTD-style intake buffer for ideas, interruptions, and new work
- `Focus Timer`: a focus-session workflow for starting key work, protecting attention, and recording time for later role-based analysis

These are not standalone productivity toys. They are execution support layers inside the LMI operating system.

## Why This Design Exists

The current LMI system is already strong at:

- role clarification
- monthly planning
- weekly planning
- daily planning
- daily / weekly / monthly / role review

But two gaps still exist:

1. New inputs arrive during the day and can easily hijack attention
2. Key work may be planned, but deep-focus execution and time evidence are not consistently captured

This design fills those two gaps without breaking the current month -> week -> day -> review loop.

## Design Principles

- Capture before judging
- Focus before multitasking
- Time evidence before time opinions
- Role goals should absorb new work, not be replaced by it
- Ideas, tasks, and facts must remain separate
- Reviews should convert captures and sessions into decisions

## New Capabilities

### 1. Capture Inbox

`Inbox` is the temporary landing zone for anything that appears before it is clarified.

Typical examples:

- a new idea
- a sudden reminder
- a risk
- a follow-up request
- a useful insight
- a possible future project

Inbox items should not automatically become daily tasks.

### 2. Focus Timer

`Focus Timer` is the execution entrypoint for important work.

It should be used when the user intentionally starts:

- an `A` item
- a major `B` item with deadline pressure
- a high-return activity
- a role-critical weekly objective

The focus layer does two things:

- helps protect real execution time
- records structured time evidence for later review and analysis

## Position In The LMI Loop

The updated loop becomes:

`Role Goal Clarifier -> Monthly Plan -> Weekly Plan -> Daily Work Plan -> Focus Sessions -> Daily Review -> Weekly Review -> Monthly Review -> Role Review`

With a parallel intake buffer:

`Inbox -> Daily / Weekly / Monthly decision points -> Plan or discard`

## Capture Inbox Design

### Inbox Purpose

Inbox exists to reduce cognitive load and prevent immediate attention hijacking.

The user should be able to say things like:

- `收进 Inbox：我想到一个客户洞察模板`
- `记个想法：AI 周报以后想分成 3 个层级`
- `记一下：需要和忆雪约原型评审`
- `这个先放 Inbox：EBG 版本价值表达有偏差`

### Inbox Categories

Keep categories lightweight:

- `idea`
- `todo`
- `risk`
- `question`
- `followup`
- `insight`

Category is for later triage, not for perfection.

### Minimum Item Schema

Each item should record:

- `id`
- `captured_at`
- `raw_text`
- `kind`
- `suggested_role`
- `suggested_horizon`
- `status`
- `decided_at`
- `decision`
- `linked_file`

Example:

```json
{
  "id": "inbox-2026-05-07-001",
  "captured_at": "2026-05-07T14:22:00+08:00",
  "raw_text": "想到一个客户洞察模板，便于销售前置筛选",
  "kind": "idea",
  "suggested_role": "新机会发现者",
  "suggested_horizon": "weekly",
  "status": "unprocessed",
  "decided_at": null,
  "decision": null,
  "linked_file": null
}
```

### Recommended Storage

Use one lightweight current inbox file plus optional archive files.

Suggested structure:

```text
memory/
├── inbox.md
├── inbox-archive/
│   └── 2026-05-inbox-archive.md
```

Suggested sections inside `memory/inbox.md`:

```md
# LMI Inbox

## Unprocessed

- [inbox-2026-05-07-001][idea][新机会发现者][weekly] 想到一个客户洞察模板，便于销售前置筛选
- [inbox-2026-05-07-002][todo][产品概念定义][daily] 和忆雪确认原型评审时间
- [inbox-2026-05-07-003][insight][CDT项目管理者][weekly] EBG 版本价值表达偏差不只是文案问题

## Decided

- [inbox-2026-05-06-009][idea] 已转入 2026-05-06.md 的 C 类跟进事项
```

### Inbox Decision Outcomes

Allowed outcomes:

- add to today
- add to later this week
- add to next month input
- convert to follow-up only
- convert to project fact candidate
- discard

### Inbox Review Rhythm

Inbox should be reviewed at 3 levels:

1. `Daily`
During morning planning, decide whether any unprocessed items deserve entry into today.

2. `Weekly`
During weekly planning and weekly review, convert surviving items into:
- next-week work
- follow-up
- idea backlog
- deleted noise

3. `Monthly`
During monthly review, promote repeated or validated ideas into:
- next month goals
- role updates
- project facts

### Inbox And Existing LMI Outputs

Daily plan should add:

- `Inbox items to decide today`

Daily review should add:

- `New captures that should not automatically roll into tomorrow`

Weekly review should add:

- `Best inbox item worth upgrading`
- `Inbox item to delete`

Monthly review should add:

- `Idea promoted into next-month focus`

## Focus Timer Design

### Focus Purpose

Focus sessions exist to turn planned priority into real time investment.

They are most useful for:

- `A1 / A2`
- strategic `B` items
- high-return activities
- role-critical work that needs uninterrupted time

### Focus Session Workflow

Recommended flow:

1. User chooses a task from the daily plan
2. System starts a focus session
3. Session runs for a chosen block
4. User ends or interrupts session
5. System records time, output, interruptions, and role mapping

### Supported Focus Modes

Support simple choices only:

- `25 min`
- `50 min`
- `90 min`
- `custom`

Recommended interpretation:

- `25 min`: light start / activation block
- `50 min`: standard execution block
- `90 min`: deep work / high-return block

### Minimum Session Schema

Each focus session should record:

- `session_id`
- `started_at`
- `ended_at`
- `minutes`
- `task`
- `task_class`
- `role`
- `linked_week_goal`
- `linked_month_goal`
- `is_high_return_activity`
- `result`
- `status`
- `interrupted`
- `interruption_reason`
- `focus_score`

Example:

```json
{
  "session_id": "focus-2026-05-07-001",
  "started_at": "2026-05-07T08:50:00+08:00",
  "ended_at": "2026-05-07T10:00:00+08:00",
  "minutes": 70,
  "task": "产出完整的SKILL.md + 使用指南",
  "task_class": "A",
  "role": "CDT项目管理者",
  "linked_week_goal": "产出完整的SKILL.md + 使用指南",
  "linked_month_goal": "产出完整的SKILL.md + 使用指南",
  "is_high_return_activity": true,
  "result": "完成结构初稿和操作步骤大纲",
  "status": "completed",
  "interrupted": false,
  "interruption_reason": null,
  "focus_score": 4
}
```

### Recommended Storage

Suggested structure:

```text
memory/
├── focus-log/
│   ├── 2026-05-focus-log.md
│   └── 2026-06-focus-log.md
```

Suggested format inside a monthly log:

```md
# 2026-05 Focus Log

## 2026-05-07

- [focus-2026-05-07-001] 08:50-10:00 | 70 min | A | CDT项目管理者 | 产出完整的SKILL.md + 使用指南 | completed | score 4
  - result: 完成结构初稿和操作步骤大纲
  - interruption: none
```

### Focus And Daily Planning

Daily plan should support commands like:

- `开始 A1 的 50 分钟专注`
- `开始 90 分钟深度块，任务是装备制造调研`
- `结束这轮专注，记录结果`

The daily plan output should eventually include:

- `Focus block suggested for A1`
- `Best next focus block if A1 is blocked`

### Focus And Daily Review

Daily review should be able to summarize:

- today's best focus block
- total focus minutes
- whether A1 received real uninterrupted time
- biggest interruption to deep work

### Focus And Weekly Review

Weekly review should aggregate:

- focus minutes by role
- focus minutes by task class `A/B/C/D`
- focus minutes on high-return activities
- interruption rate
- best time blocks

### Focus And Monthly / Role Review

Monthly review should ask:

- did time investment match monthly priorities?
- which goals looked important but received little focus time?
- which high-return activities received the most real execution?

Role review should ask:

- does time spent by role match role weight?
- which role is over-consuming time with weak return?
- which role is under-served despite strategic importance?

## Time Analysis Design

Once focus logs exist, they should power role-based time analysis.

Key metrics:

- focus minutes by role
- focus minutes by day
- focus minutes by `A/B/C/D`
- focus minutes by monthly goal
- focus minutes by weekly goal
- interrupted vs uninterrupted session ratio
- average focus score
- high-return activity time share

## Suggested User Prompts

### Inbox

- `收进 Inbox：我想到一个客户洞察模板`
- `帮我记个 idea，月底再看`
- `把这个先放进 Inbox，不要进今天计划`
- `先做日复盘，再清 Inbox，决定哪些进明天`

### Focus

- `开始 A1 的 50 分钟专注`
- `开始 90 分钟深度块，任务是装备制造调研`
- `结束本轮专注，记录结果`
- `今天按角色看，我的专注时间投在哪里了？`
- `这周哪个角色拿到了最多深度时间？`

## Implementation Order

### Phase 1: Minimal Closed Loop

Build first:

1. `Inbox capture`
2. `Inbox decision during evening daily review`
3. `Focus session start / stop`
4. `Focus log storage`
5. `Daily review reads today's focus sessions`

### Phase 2: Weekly And Monthly Integration

Build next:

1. weekly review reads inbox decisions
2. weekly review aggregates focus by role
3. monthly review aggregates focus by role and goal
4. role review compares role weight vs actual focus time

### Phase 3: Interaction Layer

Build last:

1. timer reminders
2. countdown UX
3. interruption tagging prompts
4. automatic session summaries

## Acceptance Criteria

The design is working when:

### Inbox

- new ideas no longer immediately pollute the day plan
- inbox items are visibly re-decided at daily or weekly checkpoints
- repeated or validated ideas can be promoted to real planning layers

### Focus

- A1 work can be started through a clear focus action
- focus time is recorded with role and goal linkage
- weekly review can say which role actually received deep work time
- monthly or role review can compare role intention vs real time

## Anti-Patterns

- Do not turn Inbox into a hidden permanent backlog
- Do not automatically move Inbox items into tomorrow
- Do not treat every focus session as equal; role and goal linkage matter
- Do not measure time without later using it in review
- Do not let the timer become more important than the task

## Recommended Next Step

Start with a minimal implementation:

1. add `memory/inbox.md`
2. add `memory/focus-log/YYYY-MM-focus-log.md`
3. update daily plan to import `Inbox items to decide today`
4. update daily review to summarize today's focus sessions
5. update weekly review to summarize role-based focus time
