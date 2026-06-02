# Release Notes v1.1.0

`lmi-management-system` v1.1.0 把原来的 LMI 计划 / 复盘 Skill 扩展成更完整的执行操作系统。

核心 LMI 闭环没有改变：角色目标仍然向下流入月计划、周计划、日计划和复盘。本次发布补上的是日常执行层，让白天的打断、临时想法、专注执行和复盘承接有地方可去。

## 亮点

- Inbox 捕获与清理工作流，用于处理想法、打断、风险、提醒和待跟进事项
- Focus Session 工作流，用于记录 A 类事项和关键 B 类事项的专注执行
- Focus Reminder 支持本地预提醒和番茄结束收口提示
- 日计划、周计划、月复盘和角色复盘生成器开始读取 Inbox / Focus 记忆
- 新增 `AGENTS.md`，方便后续 Agent 安全维护 Skill
- 强化同步检查，覆盖源码、OpenClaw global、OpenClaw workspace 和 Codex 副本

## 新增执行层

本次发布新增脚本和模板，用于：

- 捕获新输入，但不自动污染今天的计划
- 将 Inbox 清理为 `tomorrow`、`this_week`、`project_fact_candidate` 或 `archive`
- 从操作日志重建 Inbox
- 开始和结束 Focus Session
- 路由 `开始`、`1`、`完成：...`、`收口` 等短回复
- 在本地 OpenClaw / Feishu 环境中发送提醒

推荐节奏：

```text
白天捕获
-> 晚上清理 Inbox
-> 次日上午从已决定事项生成日计划
-> 保护关键专注块
-> 日复盘 / 周复盘吸收执行证据
```

## 计划与复盘改进

- 日计划会优先读取昨晚已经决定承接到今天的 Inbox 项，而不是直接把原始 Inbox 噪声升成任务。
- 周计划和周复盘会呈现 Inbox 决策和 Focus 证据。
- 日复盘可以把事项写入明日承接、本周输入或项目事实候选。
- 模板更强调重新决定、承接和停止，而不是无限滚动未完成任务。

## 隐私与运行说明

源码不应内置个人 Feishu `open_id`、真实工作 memory 或访问 token。消息发送目标请使用环境变量或命令行参数，例如：

```bash
export LMI_FEISHU_TARGET="你的 Feishu open_id 或会话目标"
```

可选提醒能力依赖本地 OpenClaw / Feishu 运行时。普通计划、复盘、Inbox 和 Focus 记录脚本只依赖 Python 标准库。

## 验证

发布验证覆盖：

- Python AST 解析全部 14 个脚本
- Shell 语法检查
- Markdown 内部链接检查
- 临时 memory 下的 Inbox 捕获、清理、重建、Focus 开始/结束流程
- focus reminder dry-run
- OpenClaw Skill 可发现性
- 源码、OpenClaw 和 Codex 副本同步检查

## 升级建议

如果你已经使用 `v1.0.0`，建议先阅读：

- [README.md](README.md)
- [CHANGELOG.md](CHANGELOG.md)
- [references/inbox-focus-design.md](references/inbox-focus-design.md)
- [AGENTS.md](AGENTS.md)

然后把 Skill 重新同步到正在使用的 OpenClaw / Codex 技能目录。
