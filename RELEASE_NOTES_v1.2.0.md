# Release Notes v1.2.0

`lmi-management-system` v1.2.0 开始把“计划文档”进一步推进为“可执行的 LMI 协同系统”。

这一版的重点不是再多生成几段计划文字，而是把时间设计、结构化状态和飞书日历同步链路补起来，让周计划和日计划更接近真实执行。

## 本次更新重点

- 新增中文版 `LMI_SKILL_USER_GUIDE.md`
  - 方便第一次试用的用户理解这套 Skill 不是普通 Todo，而是一条 `角色 -> 目标 -> 计划 -> 执行 -> 复盘` 的管理闭环
  - 推荐从“先做日复盘”开始进入系统

- 新增 `references/intelligent-lmi-collaboration-system.md`
  - 把系统原则、当前短板和后续升级方向整理清楚
  - 明确提出“脚本先定状态，模型再做协同”的分工

- 周计划现在会生成结构化时间承诺
  - 新增 `scripts/lmi_time_commitments.py`
  - 周计划生成后会把保护时间块、缓冲建议和日历同步对象写入 `memory/时间承诺/`
  - 不再只把这些信息留在 Markdown 段落里

- 新增飞书日历同步器
  - 新增 `scripts/sync_lmi_calendar_commitments.py`
  - 支持先预览，再执行同步
  - 支持保存同步状态，避免重复创建
  - 支持在缺少授权时明确提示所缺 scope

- 日计划和周计划加强了时间设计逻辑
  - 强调关键任务优先占据最好的连续大块时间
  - 长任务、高认知负荷任务后主动留恢复与切换缓冲
  - 固定承诺应进入飞书日历或其他稳定日历源，而不是只停留在草案

## 对使用者的实际影响

- 周计划不再只是“建议保护时间”，而是会形成可复用、可同步的结构化对象
- 日计划能更稳定承接本周保护时间块，而不是每次都从散乱文本里重新猜
- 飞书日历接入从“文档建议”迈进到“可执行链路”，只差一次用户授权即可真正写入

## 安全与发布边界

- 移除了源码中的默认 Feishu 目标 ID
- 公开仓库继续保持“运行时目标由环境变量提供”的边界
- 飞书日历真正写入前，仍需用户完成 `calendar:calendar.event:create` 与 `calendar:calendar.event:update` 授权

## 推荐验证命令

```bash
python3 scripts/generate_lmi_weekly_plan.py
```

```bash
python3 scripts/sync_lmi_calendar_commitments.py --memory-dir ~/.openclaw/workspace-azai/memory
```

```bash
python3 scripts/sync_lmi_calendar_commitments.py --memory-dir ~/.openclaw/workspace-azai/memory --apply
```
