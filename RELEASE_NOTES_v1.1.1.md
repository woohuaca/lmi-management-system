# Release Notes v1.1.1

`lmi-management-system` v1.1.1 主要完善 GitHub 中文说明，并修订公开发布中的隐私边界。

## 这次修了什么

- README 改成中文，重点说明 LMI 计划闭环、Inbox / Focus 执行层、安装方式和环境变量
- Release 说明改成中文，方便直接在 GitHub 上阅读
- 移除最新源码中的硬编码 Feishu 目标 ID
- 将本机绝对路径改为 `$HOME`、脚本相对路径或环境变量
- 明确公开仓库不应包含真实工作 memory、Feishu 目标、账号密钥或访问 token

## 使用提醒

如果需要使用 Feishu / OpenClaw 自动提醒，请在本地设置：

```bash
export LMI_FEISHU_TARGET="你的 Feishu open_id 或会话目标"
export LMI_FEISHU_ACCOUNT="1"
```

不要把这些值提交到仓库。

## 隐私检查

本次发布前检查了最新源码中的常见风险模式：

- `/Users/woohuaca`
- 具体 Feishu `open_id`
- GitHub token
- OpenAI API key
- AWS access key
- Bearer token

最新源码未发现上述真实敏感值。

## 历史说明

旧提交历史和旧 Release 源码归档中曾出现本机路径和 Feishu 目标标识。`v1.1.1` 已在最新源码中清理；如果要从整个公开历史中彻底移除，需要单独做历史重写和凭据/目标轮换。
