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

## Using With Azai

See [references/azai-usage-guide.md](references/azai-usage-guide.md) for a practical usage guide and ready-to-send prompts for `azai`.

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
    └── check-sync.sh
```

### Important Files

- `SKILL.md`: main routing and workflow rules
- `agents/openai.yaml`: UI metadata
- `assets/templates/`: reusable planning and review templates
- `references/`: methodology, storage, review, and execution guidance
- `scripts/check-sync.sh`: checks whether source, OpenClaw, and Codex copies are still in sync

## Main Files To Read

- [SKILL.md](SKILL.md)
- [references/storage-system.md](references/storage-system.md)
- [references/openclaw-execution-playbook.md](references/openclaw-execution-playbook.md)
- [references/review-system.md](references/review-system.md)
- [references/azai-usage-guide.md](references/azai-usage-guide.md)

## Current Status

This repository is the source-of-truth version used to sync:

- local development copy
- OpenClaw managed skill copy
- Codex skill copy

## Repository

GitHub: [woohuaca/lmi-management-system](https://github.com/woohuaca/lmi-management-system)
