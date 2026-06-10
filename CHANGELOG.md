# Changelog

## 2026-06-10 v1.2.0

### Added

- 中文版 `LMI_SKILL_USER_GUIDE.md`，帮助第一次接触 LMI Skill 的用户从“先做日复盘”开始上手
- `references/intelligent-lmi-collaboration-system.md`，系统化整理 LMI 协同系统的原则层、策略层、运行层，以及后续升级方向
- `scripts/lmi_time_commitments.py`，把周计划中的保护时间块沉淀为结构化“周时间承诺”对象
- `scripts/sync_lmi_calendar_commitments.py`，支持把周时间承诺预览或同步到飞书日历，并单独保存同步状态

### Improved

- `SKILL.md`、日计划、周计划、时间图像等参考资料补充了大块时间保护、任务后恢复缓冲、固定承诺进入稳定日历源等时间设计原则
- 周计划生成器现在会同时输出人可读的“固定承诺与日历同步”说明和机器可读的 `calendar_sync_items`
- 日计划生成器现在会优先读取结构化周时间承诺，让每天的时间安排更贴近本周已保护的大块时间
- 存储系统说明新增时间承诺与日历同步状态文件，降低模型靠文本猜测系统状态的比例

### Fixed

- 移除了源码里的默认 Feishu 目标 ID，公开仓库重新回到“通过环境变量提供运行时目标”的安全边界
- 飞书日历同步在未授权状态下会明确返回所缺 scope 和对应授权命令，而不是停留在模糊失败

## 2026-06-02 v1.1.2

### Fixed

- anonymized example person names, internal role labels, and organization-style acronyms in public references
- replaced domain-specific customer event and industry examples with generic customer-activity and industry-scenario wording
- removed concrete customer-count phrasing from generator fallback text

## 2026-06-02 v1.1.1

### Improved

- GitHub-facing README and release notes are now written in Chinese for easier public review and onboarding
- repository privacy guidance now clearly states that Feishu targets, runtime memory, tokens, and account-specific values should be provided through environment variables or CLI arguments
- optional delivery and reminder scripts now avoid hard-coded Feishu targets and local repository paths
- default memory paths now use `$HOME`-based paths instead of publishing a machine-specific user path

### Fixed

- removed a previously hard-coded Feishu target identifier from the latest source
- removed machine-specific local absolute paths from the latest source and public docs

## 2026-06-02

### Added

- Agent maintenance guide in `AGENTS.md`, covering source-of-truth rules, sync discipline, validation commands, and safe editing boundaries
- LMI Inbox and Focus execution layer for capturing incoming tasks, rebuilding and cleaning inbox memory, starting focus sessions, routing focus replies, and sending reminder nudges
- reusable inbox/focus templates and a detailed execution-design reference for how daily work should flow from capture to focus to review
- optional macOS LaunchAgent installer for focus reminders

### Improved

- daily, weekly, monthly, and role generators now read inbox/focus memory so plans and reviews reflect live execution context instead of only static planning files
- weekly planning and weekly review templates now make inbox triage, focus evidence, and carry-forward work more explicit
- README, SKILL instructions, and `azai` usage guidance now describe the Inbox/Focus workflow and the newer operating rhythm more clearly
- sync checking now ignores generated caches, logs, and local blog drafts so source, OpenClaw, and Codex copies can be compared without false drift

### Fixed

- execution support source labels now respect custom memory directories instead of always reporting default-path context
- local-only draft material is excluded from repository sync checks and Git tracking

## 2026-05-07

### Improved

- daily plan now reads current-month plan and current-month role clarification directly, instead of relying mainly on yesterday carry-forward plus the last weekly file
- daily planning priority now follows `month -> role -> week -> yesterday -> calendar`, so `A1` is less likely to be hijacked by an operational reminder such as checking the schedule
- weekly plan now uses May monthly goals and May role weights as its primary source of truth, with weekly deadline items moved behind the main monthly battle line
- daily review now shows monthly and weekly anchor context, making end-of-day reflection easier to tie back to role and goal intent
- customer-related `C` follow-up items are now compressed into fewer, more natural action lines instead of repeating near-duplicate follow-up text

## 2026-04-09

### Added

- `azai` migration planning and manifests for moving LMI work onto the dedicated workspace
- regression checklist for OpenClaw, Feishu, and LMI end-to-end verification
- weekly, monthly, and role review generator scripts for the `azai` LMI workflow

### Improved

- `azai`-first LMI daily planning and review flow
- daily plan now carries forward yesterday's review context, weekly anchors, and high-return activities
- daily plan now checks Feishu calendar availability and generates more realistic workday schedules
- daily plan output now emphasizes `Today's Primary Result`, cleaner `A/B/C/D` categories, and less noisy system metadata
- daily review now includes work-experience feedback and writes back better next-day carry-forward guidance
- README with clearer operational guidance for Feishu/OpenClaw regression and `azai` usage

## 2026-03-31

### Added

- Four-level review system:
  - daily review
  - weekly review
  - monthly review
  - role review
- `A/B/C/D` daily classification:
  - `A` important items
  - `B` urgent items
  - `C` contact or follow-up items
  - `D` meetings, discussions, or coordination items
- storage system guidance for plans, reviews, ideas, project facts, and long-term preferences
- `azai` usage guide with ready-to-send prompts
- sync check script for source, OpenClaw, and Codex copies
- MIT license

### Improved

- GitHub README structure for easier discovery, installation, and onboarding
- OpenClaw execution playbook for cross-layer handoff
- daily planning guidance to reflect the new task classification
- repository setup so local source, OpenClaw runtime copy, Codex copy, and GitHub repo stay aligned

## 2026-03-20

### Added

- initial public version of the `lmi-management-system` skill
- role goal clarification
- monthly plan
- weekly plan
- daily work plan
- weekly review
- time image
- stats analysis
- agent collaboration rules
- execution playbook
- GitHub repository publishing
