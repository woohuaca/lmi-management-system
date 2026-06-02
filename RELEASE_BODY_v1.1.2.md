# v1.1.2

`lmi-management-system` v1.1.2 是一次内容隐私补丁。

## 主要更新

- 匿名化公开参考文档里的示例人名
- 泛化内部角色标签、组织缩写和项目语境词
- 将具体区域/行业/客户活动示例改为通用表达
- 将生成器 fallback 文案中的具体客户数量和具体活动名称改成泛化表达

## 隐私检查结果

最新源码已重新扫描：

- 未发现真实人名示例
- 未发现具体公司名或客户名
- 未发现先前识别出的内部缩写 / 场景词
- 未发现真实 Feishu 目标 ID、访问 token 或本机绝对路径

说明：`azai`、`workspace-main`、`workspace-azai` 仍作为本地 Agent / workspace 命名保留。它们不像人名、公司名或客户名，但如果后续希望仓库完全中性化，可以再单独做一轮命名抽象。

## 验证

- 高风险词扫描通过
- 模板目录人工检查通过
- Python AST 解析通过
- Shell 语法检查通过
- Markdown 内部链接检查通过
- Inbox / Focus 临时 memory 流程通过
- OpenClaw / Codex 安装副本同步检查通过

## 仓库

GitHub: [woohuaca/lmi-management-system](https://github.com/woohuaca/lmi-management-system)
