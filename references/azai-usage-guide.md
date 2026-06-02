# Azai Usage Guide

Use this guide when the user wants a practical way to work with `azai` using the LMI Management System skill.

## Best Daily Rhythm

Use these entry prompts with `azai`:

### Start of Month

`请使用 lmi-management-system 协同我做本月计划。先整理使命/宗旨、本月个人焦点目标、本月公司焦点目标，再收敛首要目标和高回报活动。`

### Start of Week

`请使用 lmi-management-system 协同我做本周工作计划。先从月目标里压缩出本周最重要的 1-3 个结果，再给出 A/B/C/D 和保护时间块。`

### Start of Day

`请使用 lmi-management-system 帮我排今天。按 A/B/C/D 分类，并告诉我今天最重要的结果。`

For a manual refresh in an existing thread, prefer this stronger version:

`请先刷新今天的 LMI 日计划，再按最新周计划和月目标帮我排今天。`

If you already have new ideas, interruptions, or reminders before planning:

`先把这些收进 Inbox，晚上复盘时再一起判断。`

### End of Day

`请使用 lmi-management-system 帮我做日复盘。重点看今天最重要结果有没有发生、哪些事打断了我、明天第一步是什么。`

### End of Week

`请使用 lmi-management-system 帮我做周复盘，并顺手生成下周预备计划。重点看高回报活动、低回报时间、目标/执行/机制问题。`

### End of Month

`请使用 lmi-management-system 帮我做月复盘。检查个人目标、公司目标、高回报活动和机制有效性。`

### Role Review

`请使用 lmi-management-system 帮我做角色复盘。检查职责、关键业绩、时间投入和角色边界是否仍然匹配。`

## Inbox And Focus Prompts

These prompts help `azai` use the new execution-layer workflow more naturally.

### Quick Inbox Capture

- `收进 Inbox：我想到一个客户洞察模板，月底再决定要不要升级`
- `把这个先放 Inbox，不要进今天计划：和同事A约原型评审`
- `先做日复盘，再清 Inbox`
- `今晚顺手清 Inbox，帮我判断哪些进明天、哪些留在本周`

### Focus Session

- `开始 A1 的 50 分钟专注`
- `开始 90 分钟深度块，任务是完成深度调研报告第一版框架`
- `结束本轮专注，记录结果：完成目录和判断框架，focus score 4`
- `今天按角色看，我的专注时间投在哪里了？`
- `这周哪个角色拿到了最多深度时间？`

Recommended rule:

- use pomodoro / focus mode mainly for `A` items and role-critical `B` items
- `C` / `D` items are usually better handled as batch follow-up or coordination windows

### Reminder + Auto Start

- 当 `azai` 提前 2 分钟提醒关键事项时，直接回复：`开始`
- 也可以回复：`开始专注`
- 然后 `azai` 会追问：`这块你想用几个番茄？`，你回复：`1 / 2 / 3`
- 这里先只用完整番茄数，不用 `2.5` 这种小数
- 番茄时间到后，优先先收口，再回复：
  - `完成：这轮产出是什么`
  - `这个任务完成了`
  - `结束了`
  - `中断：原因`
  - `继续1个`
  - `收口`
- 如果已经安装本地提醒调度器，这个提醒会由系统每分钟自动检查今日计划并主动发出，不需要你手动触发

## Recommended Conversation Pattern

- give `azai` the current layer first: month, week, day, review, or role
- paste the current raw notes, unfinished items, or draft plan
- ask for compression, not expansion
- ask for `Next 1-3 Moves` when you want a short close

## Recommended Capture Pattern

- unfinished work and newly added work: capture in the daily log, then re-decide
- reflections: capture in daily or weekly review
- ideas, interruptions, risks, and reminders: capture into `Inbox` first during the day, then clean them in the evening review
- deep work on `A1 / A2`: start a `Focus Session` so the time can be used later in daily / weekly / role review
- validated conclusions: move into `项目事实`

## Suggested Standing Instruction

Use this once in a fresh `azai` thread:

`以后请优先使用 lmi-management-system 协同我。默认先判断我是角色目标澄清、月计划、周计划、日计划、日复盘、周复盘、月复盘、角色复盘、时间图像还是统计分析场景。尽量先起草，再最少追问；优先压缩重点，默认检查高回报活动、授权事项和管理机制，并在结尾输出 Next 1-3 Moves。`

Optional extension:

`如果我给的是新想法、提醒或突发事项，先建议我是否收进 Inbox；如果我已经确认了 A1 / A2，请主动建议我开启 25 / 50 / 90 分钟专注块。`

Optional extension for scheduled execution:

`如果今天的日计划里已经有明确时间块，请在 A 类和关键 B 类事项开始前 2 分钟提醒我；我回复 开始/开始专注 后，先问我这块想用 1 / 2 / 3 个番茄，再进入专注。不要把 好的 当成触发词。时间到后先帮我收口，再决定继续还是切换。`

Optional extension for manual day-plan refresh:

`如果我在进行中的线程里说“做今日 LMI 日计划”或“排今天”，请先运行本地日计划生成脚本刷新今天的 daily file，再基于刷新后的结果跟我协同；不要沿用旧聊天上下文里的过期优先级。`
