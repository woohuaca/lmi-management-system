# LMI Management System

LMI Management System is an OpenClaw skill inspired by Leadership Management International workflows.

It helps turn role goals into practical management rhythm across:

- role goal clarification
- monthly planning
- weekly planning
- weekly review
- daily work planning
- time image design
- personal productivity summary and analysis

## What It Does

This skill is designed to help an agent act as a management collaborator, not just a template filler.

It can:

- clarify roles, responsibilities, key results, and high-return activities
- connect monthly goals to weekly focus and daily execution
- support weekly review and carry-forward decisions
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
- `Weekly Review`
- `Daily Work Plan`
- `Time Image`
- `Stats Analysis`

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
- `按 LMI 周复盘帮我看：这周哪些是高回报活动，哪些时间浪费了`
- `用 LMI 帮我排今天，按 A1/A2/B/D 分类，并给我日程安排`
- `按 LMI 时间图像帮我设计理想的一周时间分配`
- `用 LMI 个人生产力摘要表分析我这周的时间投入`

## Repository

GitHub: [woohuaca/lmi-management-system](https://github.com/woohuaca/lmi-management-system)
