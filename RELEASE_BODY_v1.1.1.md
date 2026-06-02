# v1.1.1

`lmi-management-system` v1.1.1 是一次 GitHub 发布页与隐私边界修订。

## 主要更新

- README 改为中文说明，便于中文用户直接理解安装、使用和执行层能力
- GitHub Release 正文改为中文
- 仓库说明更清楚地区分 Skill 源码、运行时 memory、Feishu 目标和本地配置
- 移除最新源码中的硬编码 Feishu 目标 ID
- 将本机绝对路径改为 `$HOME`、脚本相对路径或环境变量默认值
- `deliver_lmi.py` 和 `lmi_focus_reminder.py` 改为通过 `LMI_FEISHU_TARGET` / `--target` 接收 Feishu 发送目标

## 隐私检查结果

最新源码已重新扫描：

- 未发现 GitHub token、OpenAI key、AWS key、Bearer token 等常见密钥模式
- 未发现真实 Feishu `open_id` 常量
- 未发现机器特定的 `/Users/woohuaca/...` 路径
- 未发布真实工作 memory 文件

注意：旧提交历史和旧 Release 源码归档中曾包含本机路径和一个 Feishu 目标标识。`v1.1.1` 已在最新发布中移除这些内容；如果需要从整个 Git 历史中彻底删除，需要单独执行 history rewrite、删除/重建旧 Release，并轮换相关 Feishu 目标。

## 验证

- Python AST 解析全部 14 个脚本
- Shell 语法检查通过
- Markdown 内部链接检查通过
- 临时 memory 下 Inbox / Focus 流程通过
- 隐私模式二次扫描通过
- OpenClaw / Codex 安装副本同步检查通过

## 仓库

GitHub: [woohuaca/lmi-management-system](https://github.com/woohuaca/lmi-management-system)
