# LMI Management System

LMI Management System is an OpenClaw skill inspired by Leadership Management International workflows.

It helps turn role goals into practical management rhythm across:

- role goal clarification
- monthly planning
- weekly planning
- daily review
- weekly review
- monthly review
- role review
- daily work planning
- time image design
- personal productivity summary and analysis

## What It Does

This skill is designed to help an agent act as a management collaborator, not just a template filler.

It can:

- clarify roles, responsibilities, key results, and high-return activities
- connect monthly goals to weekly focus and daily execution
- support weekly review and carry-forward decisions
- support daily, weekly, monthly, and role review
- design an ideal weekly time image
- analyze actual time use through a personal productivity summary
- identify delegation, management mechanisms, and review actions

## Structure

- `SKILL.md`: skill entry point and workflow rules
- `agents/openai.yaml`: UI metadata
- `references/`: planning, review, and collaboration guidance
- `assets/templates/`: reusable output templates

## Main Modes

- `Role Goal Clarifier`
- `Monthly Plan`
- `Weekly Plan`
- `Daily Review`
- `Weekly Review`
- `Monthly Review`
- `Role Review`
- `Daily Work Plan`
- `Time Image`
- `Stats Analysis`

## Workflow

Use the skill as a closed loop:

1. `Role Goal Clarifier`: define role value, responsibilities, key results, and high-return activities
2. `Monthly Plan`: decide what matters this month
3. `Weekly Plan`: compress the month into a few weekly wins
4. `Daily Work Plan`: classify today's work as `A/B/C/D`
5. `Daily Review`: re-decide unfinished work and protect tomorrow's first move
6. `Weekly Review`: review leverage, drag, and next-week carry-forward
7. `Monthly Review`: review personal goals, company goals, and mechanism effectiveness
8. `Role Review`: review whether the role itself still fits the value expected
9. `Time Image` and `Stats Analysis`: compare ideal time use with actual time use and correct the system

## Storage Pattern

Recommended storage in an OpenClaw memory workspace:

- `memory/YYYY-MM-DD.md`: raw daily log and lightweight daily review
- `memory/日报归档/YYYY-MM-DD_工作日志.md`: cleaned daily work log
- `memory/周复盘-YYYY-MM-DD-YY.md`: weekly review
- `memory/月复盘-YYYY-MM.md`: monthly review
- `memory/角色复盘-角色名-YYYY-MM.md`: role review
- `memory/项目事实/...`: validated project facts and stable conclusions
- `memory/长期偏好/...`: stable working preferences and recurring rules

## Management Rules

- Unfinished work must be re-decided each day: move, defer, delegate, or stop
- New work must be classified before it enters today's plan
- Role goals must flow into month, week, and day instead of staying only in the role sheet
- Reflections belong in reviews, ideas belong in capture then weekly filtering, and only validated conclusions belong in project facts

## Using With Azai

See [references/azai-usage-guide.md](references/azai-usage-guide.md) for a practical operating guide and ready-to-send prompts for `azai`.

## Install

Copy the folder into your Codex or OpenClaw skills directory:

```bash
cp -R lmi-management-system ~/.codex/skills/
```

Then restart the gateway or app so the new skill is discovered.

## Example Prompts

- `用 LMI 帮我梳理这个岗位的角色目标澄清表`
- `按 LMI 帮我做本月计划，先写使命/宗旨、个人焦点目标和公司焦点目标`
- `用 LMI 把我的月目标拆成这周的工作计划`
- `按 LMI 帮我做今天的日复盘，并给出明天第一步`
- `按 LMI 周复盘帮我看：这周哪些是高回报活动，哪些时间浪费了`
- `按 LMI 帮我做月复盘，检查个人目标、公司目标和机制问题`
- `按 LMI 帮我做角色复盘，看看我的职责、关键业绩和时间投入是否匹配`
- `用 LMI 帮我排今天，按 A/B/C/D 分类，并给我日程安排`
- `按 LMI 时间图像帮我设计理想的一周时间分配`
- `用 LMI 个人生产力摘要表分析我这周的时间投入`

## Repository

GitHub: [woohuaca/lmi-management-system](https://github.com/woohuaca/lmi-management-system)
