# LMI Management System

`lmi-management-system` 是一个面向 OpenClaw / Codex 的 LMI 管理 Skill。它把角色目标澄清、月计划、周计划、日计划、复盘和执行跟进串成一套可重复使用的个人管理系统。

它不是普通 Todo List。它更关注：目标是否清楚、时间是否服务目标、今天的重点是否承接本周和本月目标，以及复盘结果是否真的回到下一轮计划里。

## 适合谁

- 想用 LMI / Leadership Management International 方法做目标管理的人
- 需要把角色、目标、项目、行动和临时事项分清楚的人
- 想让 AI 协同完成月计划、周计划、日计划和复盘的人
- 想建立 Inbox、专注块和回顾闭环的人
- 管理者、创业者、产品/销售/运营负责人，以及需要自我管理节奏的人

## 核心能力

当前 Skill 支持 10 个工作模式：

1. `Role Goal Clarifier`：角色目标澄清
2. `Monthly Plan`：月计划
3. `Weekly Plan`：周计划
4. `Daily Review`：日复盘
5. `Weekly Review`：周复盘
6. `Monthly Review`：月复盘
7. `Role Review`：角色复盘
8. `Daily Work Plan`：日工作计划
9. `Time Image`：理想时间图像
10. `Stats Analysis`：个人生产力分析

v1.1.0 之后还增加了执行层：

- `Inbox`：捕获想法、打断、风险、提醒和待跟进事项
- `Focus Log`：记录 A 类事项和关键 B 类事项的专注执行
- `Focus Reminder`：在本地 OpenClaw / Feishu 环境中发送提醒，并支持回复式专注流程

## 方法闭环

推荐按下面的闭环使用：

```text
角色目标澄清
-> 月计划
-> 周计划
-> 日计划
-> 日复盘
-> 周复盘
-> 月复盘
-> 角色复盘
```

执行层建议这样接入：

```text
白天收进 Inbox
-> 晚上清理 Inbox
-> 次日计划承接已决定事项
-> 执行关键专注块
-> 日复盘 / 周复盘吸收执行证据
```

## 日常分类

日计划使用 `A/B/C/D` 分类：

- `A`：重要事项，直接服务角色目标或本周关键结果
- `B`：紧要事项，有时限压力或外部承诺
- `C`：联络 / 追踪事项
- `D`：会议 / 讨论 / 协调事项

分类的目的不是给任务贴标签，而是帮助决定注意力、授权、延期和停止。

## 安装

### OpenClaw

```bash
cp -R lmi-management-system ~/.openclaw/skills/
openclaw skills info lmi-management-system
```

### Codex

```bash
cp -R lmi-management-system ~/.codex/skills/
```

## 快速开始

可以直接用这些提示词试运行：

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

推荐长期指令：

```text
以后请优先使用 lmi-management-system 协同我。默认先判断我是角色目标澄清、月计划、周计划、日计划、日复盘、周复盘、月复盘、角色复盘、时间图像还是统计分析场景。尽量先起草，再最少追问；优先压缩重点，默认检查高回报活动、授权事项和管理机制，并在结尾输出 Next 1-3 Moves。
```

## Inbox 与 Focus 执行层

建议的 memory 结构：

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

常用脚本：

```bash
python3 scripts/lmi_capture_inbox.py "想到一个客户洞察模板，便于销售前置筛选" --kind idea --role 新机会发现者 --horizon weekly

python3 scripts/lmi_clean_inbox.py

python3 scripts/lmi_clean_inbox.py --decision inbox-2026-05-20-001=tomorrow --decision inbox-2026-05-20-002=project_fact_candidate

python3 scripts/lmi_rebuild_inbox.py

python3 scripts/lmi_focus_session.py start --task "完成深度调研报告第一版框架" --task-class A --role 新机会发现者 --minutes 50 --high-return

python3 scripts/lmi_focus_session.py end --result "完成调研报告第一版框架与目录" --focus-score 4

python3 scripts/lmi_focus_reminder.py --dry-run
```

如果要启用本地提醒，需要先配置目标会话，避免把私人 ID 写入仓库：

```bash
export LMI_FEISHU_TARGET="你的 Feishu open_id 或会话目标"
export LMI_FEISHU_ACCOUNT="1"
zsh scripts/install_focus_reminder_launch_agent.sh
```

## 环境变量

常用可配置项：

- `LMI_PRIMARY_MEMORY_DIR`：主 memory 目录，默认 `$HOME/.openclaw/workspace-azai/memory`
- `LMI_ALLOW_MAIN_MEMORY_FALLBACK`：是否允许回退读取 `workspace-main/memory`
- `LMI_FALLBACK_MEMORY_DIR`：回退 memory 目录
- `LMI_AZAI_SESSION_DIR`：azai 会话目录
- `LMI_FEISHU_TARGET`：Feishu 发送目标，默认不设置
- `LMI_FEISHU_ACCOUNT`：Feishu 账号编号，默认 `1`
- `LMI_OPENCLAW_BIN`：OpenClaw 命令路径

## 目录结构

```text
lmi-management-system/
├── SKILL.md
├── README.md
├── CHANGELOG.md
├── RELEASE_NOTES_v1.1.1.md
├── AGENTS.md
├── agents/
│   └── openai.yaml
├── assets/
│   └── templates/
├── references/
└── scripts/
```

重要文件：

- [SKILL.md](SKILL.md)：Skill 触发、路由和工作规则
- [AGENTS.md](AGENTS.md)：维护该项目时给 Agent 的工程规则
- [CHANGELOG.md](CHANGELOG.md)：版本更新记录
- [RELEASE_NOTES_v1.1.1.md](RELEASE_NOTES_v1.1.1.md)：最新发布说明
- [references/inbox-focus-design.md](references/inbox-focus-design.md)：Inbox / Focus 设计说明
- [references/storage-system.md](references/storage-system.md)：存储系统建议
- [references/openclaw-execution-playbook.md](references/openclaw-execution-playbook.md)：OpenClaw 协同执行指南
- [references/review-system.md](references/review-system.md)：复盘体系

## 隐私与发布边界

公开仓库不应包含个人 Feishu `open_id`、账号密钥、访问 token 或真实工作 memory 文件。

本仓库只发布 Skill、模板、参考说明和脚本。运行时所需的个人路径、Feishu 目标和 OpenClaw 配置应通过环境变量或命令行参数提供。

本地宣传素材、公众号草稿和缓存文件已通过 `.gitignore` 排除，不进入 GitHub 发布包。

## 同步检查

如果你同时使用源码副本、OpenClaw 副本和 Codex 副本，可以运行：

```bash
bash scripts/check-sync.sh
```

该脚本会检查：

- `$HOME/.openclaw/skills/lmi-management-system`
- `$HOME/.openclaw/workspace-main/skills/lmi-management-system`
- `$HOME/.openclaw/workspace-azai/skills/lmi-management-system`
- `$HOME/.codex/skills/lmi-management-system`

## 许可证

MIT. See [LICENSE](LICENSE).

## 仓库

GitHub: [woohuaca/lmi-management-system](https://github.com/woohuaca/lmi-management-system)
