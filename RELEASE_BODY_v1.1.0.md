# v1.1.0

`lmi-management-system` v1.1.0 是一次执行层增强发布。

这个版本保留原有 LMI 主线：角色目标 -> 月计划 -> 周计划 -> 日计划 -> 日复盘 -> 周复盘 -> 月复盘 -> 角色复盘。同时新增 Inbox 与 Focus 执行层，让计划、执行和复盘之间的承接更稳定。

## 主要更新

- 新增 Inbox 捕获、清理、重建和归档能力
- 新增 Focus Session 开始/结束记录
- 新增短回复路由，例如 `开始`、`1`、`完成：...`、`收口`
- 新增本地提醒能力，可通过 OpenClaw / Feishu 运行时发送专注提醒
- 日计划、周计划、月复盘、角色复盘生成器开始读取 Inbox 和 Focus 记忆
- 新增 `AGENTS.md`，方便后续 Agent 安全维护这个 Skill
- 强化同步检查，覆盖源码、OpenClaw 和 Codex 的多个安装副本

## 为什么重要

这个 Skill 不再只停留在“生成计划”。它可以帮助你捕获打断、重新决定未完成事项、保护关键专注块，并把执行证据带回复盘系统。

## 隐私说明

最新版本不在源码中内置个人 Feishu 目标 ID。提醒和消息发送所需的目标会话请通过环境变量或命令行参数配置，例如 `LMI_FEISHU_TARGET`。

本仓库不包含真实工作 memory 文件、访问 token 或账号密钥。可选的 Feishu / OpenClaw 自动化依赖本地运行时环境。

## 验证

- 解析全部 14 个 Python 脚本
- 检查同步脚本和 LaunchAgent 安装脚本的 Shell 语法
- 检查 Markdown 内部链接
- 使用临时 memory 跑通 Inbox 捕获、清理、重建和 Focus 开始/结束流程
- 执行 focus reminder dry-run
- 验证 OpenClaw 能识别 Skill
- 验证源码、OpenClaw 和 Codex 安装副本同步一致

## 仓库

GitHub: [woohuaca/lmi-management-system](https://github.com/woohuaca/lmi-management-system)
