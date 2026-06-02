# LMI Management System

`lmi-management-system` is an OpenClaw / Codex skill that turns LMI-style role planning, time management, and review into a repeatable operating system.

It is designed for people who want an agent to help with:

- role goal clarification
- monthly planning
- weekly planning
- daily planning
- daily, weekly, monthly, and role review
- time design and personal productivity analysis

## Why This Skill Exists

Many planning systems stop at templates. This skill is meant to go further:

- convert role goals into monthly, weekly, and daily action
- separate planning from review
- separate ideas from validated project facts
- force unfinished work to be re-decided instead of endlessly rolling forward
- help an agent act like a management collaborator, not just a form filler

## What Is Included

The skill currently supports 10 working modes:

1. `Role Goal Clarifier`
2. `Monthly Plan`
3. `Weekly Plan`
4. `Daily Review`
5. `Weekly Review`
6. `Monthly Review`
7. `Role Review`
8. `Daily Work Plan`
9. `Time Image`
10. `Stats Analysis`

## Core Ideas

- Goals come before tasks
- Time should follow goals
- High-return activities deserve protected time
- Role goals must flow into month, week, and day
- Reviews should create adjustments, not just observations

## Planning And Review Loop

Use the skill as a closed loop:

```text
Role Goal Clarifier
-> Monthly Plan
-> Weekly Plan
-> Daily Work Plan
-> Daily Review
-> Weekly Review
-> Monthly Review
-> Role Review
```

Correction loop:

```text
Time Image
<-> Stats Analysis
-> Weekly Plan / Monthly Review
```

## Daily Classification

For day-to-day execution, classify work like this:

- `A`: important items
- `B`: urgent items
- `C`: contact or follow-up items
- `D`: meetings, discussions, or coordination items

This is used to decide attention, not just to label tasks.

## Recommended Storage Pattern

If you use an OpenClaw memory workspace, a practical storage layout is:

```text
memory/
├── YYYY-MM-DD.md
├── 日报归档/YYYY-MM-DD_工作日志.md
├── 周复盘-YYYY-MM-DD-YY.md
├── 月复盘-YYYY-MM.md
├── 角色复盘-角色名-YYYY-MM.md
├── 项目事实/
└── 长期偏好/
```

Recommended usage:

- `memory/YYYY-MM-DD.md`: raw daily log and lightweight daily review
- `日报归档`: cleaner daily log
- `周复盘 / 月复盘 / 角色复盘`: formal reviews
- `项目事实`: validated conclusions and stable project knowledge
- `长期偏好`: stable working preferences and recurring rules

## Management Rules

- Unfinished work must be re-decided each day: move, defer, delegate, or stop
- New work should be classified before entering the day plan
- Role goals should flow into month, week, and day instead of staying in a static role sheet
- Reflections belong in reviews
- Ideas should be captured first, then filtered weekly
- Only validated conclusions should be stored as project facts

## Installation

### OpenClaw

Install into the managed OpenClaw skills directory:

```bash
cp -R lmi-management-system ~/.openclaw/skills/
```

Then verify:

```bash
openclaw skills info lmi-management-system
```

### Codex

Install into the Codex skills directory:

```bash
cp -R lmi-management-system ~/.codex/skills/
```

## Quick Start Prompts

These prompts are good first tests:

- `用 LMI 帮我梳理这个岗位的角色目标澄清表`
- `按 LMI 帮我做本月计划，先写使命/宗旨、个人焦点目标和公司焦点目标`
- `用 LMI 把我的月目标拆成这周的工作计划`
- `用 LMI 帮我排今天，按 A/B/C/D 分类，并给我日程安排`
- `按 LMI 帮我做今天的日复盘，并给出明天第一步`
- `按 LMI 周复盘帮我看：这周哪些是高回报活动，哪些时间浪费了`
- `按 LMI 帮我做月复盘，检查个人目标、公司目标和机制问题`
- `按 LMI 帮我做角色复盘，看看我的职责、关键业绩和时间投入是否匹配`
- `按 LMI 时间图像帮我设计理想的一周时间分配`
- `用 LMI 个人生产力摘要表分析我这周的时间投入`

## Execution Add-ons

This repository now includes three lightweight execution-layer add-ons:

1. `Inbox`
   - GTD-style capture buffer for ideas, interruptions, risks, and follow-ups
2. `Focus Log`
   - start / end based focus-session log for A-item execution and later role-based time review
3. `Focus Reminder`
   - 2-minute pre-start reminders for scheduled `A` work and key `B` work, plus reply-driven focus support

Suggested storage:

```text
memory/
├── inbox.md
├── inbox-capture/
│   └── YYYY-MM-DD.md
├── inbox-archive/
│   └── YYYY-MM-inbox-archive.md
├── 本周待跟进输入.md
├── 项目事实/
│   └── Inbox-项目事实候选.md
└── focus-log/
    └── YYYY-MM-focus-log.md
```

Helpful scripts:

- `scripts/lmi_capture_inbox.py`
- `scripts/lmi_clean_inbox.py`
- `scripts/lmi_rebuild_inbox.py`
- `scripts/lmi_focus_session.py`
- `scripts/lmi_focus_reply_router.py`
- `scripts/lmi_focus_reminder.py`
- `scripts/install_focus_reminder_launch_agent.sh`

Examples:

```bash
python3 scripts/lmi_capture_inbox.py "想到一个客户洞察模板，便于销售前置筛选" --kind idea --role 新机会发现者 --horizon weekly

python3 scripts/lmi_clean_inbox.py

python3 scripts/lmi_clean_inbox.py --decision inbox-2026-05-20-001=tomorrow --decision inbox-2026-05-20-002=project_fact_candidate

python3 scripts/lmi_rebuild_inbox.py

python3 scripts/lmi_focus_session.py start --task "完成深度调研报告第一版框架" --task-class A --role 新机会发现者 --minutes 50 --high-return

python3 scripts/lmi_focus_session.py end --result "完成调研报告第一版框架与目录" --focus-score 4

python3 scripts/lmi_focus_reminder.py --dry-run

zsh scripts/install_focus_reminder_launch_agent.sh
```

Reply-driven focus flow:

- when a key scheduled item is 2 minutes away, `Focus Reminder` can send a prompt
- reply `开始` or `开始专注`, and the router will first ask how many pomodoros you want: `1 / 2 / 3`
- after you choose, the router starts a protected focus block and gives a short environment-reset prompt
- use whole pomodoros only for now; do not use fractional values like `2.5`
- when the focus block ends, reply `完成：结果` or `中断：原因`, or choose `继续1个 / 继续2个 / 收口`
- the result is written back into the monthly focus log and later used in daily / weekly review

Inbox flow:

- daytime: capture into `Inbox`
- evening daily review: clean `Inbox` into `进明天 / 留在本周 / 转项目事实候选 / 丢弃`
- next morning: build the day plan from the decided carryover first, then reread any remaining unprocessed Inbox items

## Example Output

Here is a short example of the kind of structured output this skill is meant to produce.

Prompt:

```text
用 LMI 把我的月目标拆成这周的工作计划
```

Example output:

```text
Week Theme
- 本周主题：把月目标收敛成可推进的 2 个结果
- 对应月目标：完成制造业场景验证，并建立客户跟进机制

This Week's Top Goals
- Goal 1：完成制造业场景 demo 的第一轮可演示版本
- Goal 2：完成 8 个重点客户的跟进触达

High-Return Activities
- Activity 1：保护 2 个 90 分钟深度工作块做 demo
- Activity 2：集中 1 个时间块完成客户跟进 SOP

Delegation And Follow-Up
- Must personally drive：demo 核心逻辑、客户价值主张
- Delegate：资料整理、会后纪要
- Follow up only：客户触达结果汇总

Next 1-3 Moves
- Move 1：先确定本周只保留 2 个 top goals
- Move 2：把周三前的深度工作时间块锁定
- Move 3：列出 8 个客户跟进名单和触达方式
```

## Using With Azai

See [references/azai-usage-guide.md](references/azai-usage-guide.md) for a practical usage guide and ready-to-send prompts for `azai`.

For OpenClaw / Feishu / agent-routing verification after changes, use:

- [references/openclaw-feishu-lmi-regression-checklist.md](references/openclaw-feishu-lmi-regression-checklist.md)

Recommended standing instruction:

```text
以后请优先使用 lmi-management-system 协同我。默认先判断我是角色目标澄清、月计划、周计划、日计划、日复盘、周复盘、月复盘、角色复盘、时间图像还是统计分析场景。尽量先起草，再最少追问；优先压缩重点，默认检查高回报活动、授权事项和管理机制，并在结尾输出 Next 1-3 Moves。
```

## Repository Layout

```text
lmi-management-system/
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
├── assets/
│   └── templates/
├── references/
└── scripts/
    ├── check-sync.sh
    ├── lmi_capture_inbox.py
    ├── lmi_execution_support.py
    ├── lmi_focus_reminder.py
    ├── lmi_focus_reply_router.py
    └── lmi_focus_session.py
```

### Important Files

- `SKILL.md`: main routing and workflow rules
- `agents/openai.yaml`: UI metadata
- `assets/templates/`: reusable planning and review templates
- `references/`: methodology, storage, review, and execution guidance
- `scripts/check-sync.sh`: checks whether source, OpenClaw, and Codex copies are still in sync
- `scripts/lmi_capture_inbox.py`: capture ideas and interruptions into inbox
- `scripts/lmi_focus_reminder.py`: send 2-minute key-task reminders and pomodoro end reminders
- `scripts/lmi_focus_reply_router.py`: turn short Feishu replies into focus start / end records
- `scripts/install_focus_reminder_launch_agent.sh`: install a local macOS LaunchAgent to run reminder checks every minute
- `scripts/lmi_focus_session.py`: start and end focus sessions for later analysis

## Main Files To Read

- [SKILL.md](SKILL.md)
- [CHANGELOG.md](CHANGELOG.md)
- [RELEASE_NOTES_v1.1.0.md](RELEASE_NOTES_v1.1.0.md)
- [references/storage-system.md](references/storage-system.md)
- [references/openclaw-execution-playbook.md](references/openclaw-execution-playbook.md)
- [references/review-system.md](references/review-system.md)
- [references/azai-usage-guide.md](references/azai-usage-guide.md)
- [references/inbox-focus-design.md](references/inbox-focus-design.md)

## Current Status

This repository is the source-of-truth version used to sync:

- local development copy
- OpenClaw managed skill copy
- Codex skill copy

## License

MIT. See [LICENSE](LICENSE).

## Repository

GitHub: [woohuaca/lmi-management-system](https://github.com/woohuaca/lmi-management-system)
