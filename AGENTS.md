# Agent Maintenance Guide

This repository is the source-of-truth copy of the `lmi-management-system` skill. Use this guide when changing the project itself. Use `SKILL.md` when running the skill for LMI planning, review, Inbox, or focus-session collaboration.

## Project Shape

- This is an OpenClaw / Codex skill package, not a standalone app.
- Core behavior lives in `SKILL.md`.
- Method references live in `references/`.
- Output templates live in `assets/templates/`.
- Operational generators and delivery helpers live in `scripts/`.
- Runtime memory is outside this repo, normally under `$HOME/.openclaw/workspace-azai/memory`.

## Source Of Truth

- Treat this repo as the editable source.
- Do not directly edit `$HOME/.openclaw/skills/lmi-management-system` or `$HOME/.codex/skills/lmi-management-system` unless the user explicitly asks for an installed-copy hotfix.
- After repo changes, run `bash scripts/check-sync.sh` to see whether installed copies drift from source.
- If syncing installed copies is needed, tell the user exactly what will be copied before doing it.

## Side Effects

- Prefer dry-run or temporary-memory tests before touching real memory files.
- Do not send Feishu messages during validation unless the user explicitly asks for a live delivery test.
- Do not modify OpenClaw cron jobs, Feishu account routing, or LaunchAgent files unless the user explicitly asks for runtime configuration changes.
- Use a temp memory directory for script checks, for example `/private/tmp/lmi-diagnostic-memory.*`.
- Never overwrite real daily, weekly, monthly, role, Inbox, or focus-log files just to test parsing.

## Runtime Contracts

- Daily plan consumers now expect the user-facing order `## 昨日承接`, `## 今日主结果`, `## 硬约束`, `## 今日时间安排`, `## 事项归位`, `## 今天不排入主线`, `## 这样排的逻辑`, `## 收工前`, `## Todays Completed Items`, and `## Daily Review`.
- Under `## 事项归位`, keep machine-readable category headings as `### A：重要事项`, `### B：紧要事项`, `### C：联络/追踪事项`, and `### D：会议/讨论/协调事项`.
- Focus reminder parsing depends on the category headings above plus `## 今日时间安排`.
- Daily review and weekly review parsing depend on the headings above and on `## Todays Completed Items` / `## Daily Review`.
- Legacy headings such as top-level `## A：重要事项` and `## Schedule` are still supported for compatibility, but new edits should follow the new structure unless a migration requires otherwise.
- Weekly plan and review generators parse table and section labels in existing templates; change headings only with corresponding parser updates.
- `workspace-azai/memory` is the primary LMI memory home. Fallback to `workspace-main/memory` must remain opt-in recovery through `LMI_ALLOW_MAIN_MEMORY_FALLBACK=1`.
- Keep generated user-facing replies concise and manager-friendly Chinese unless the user asks otherwise.

## Configuration Rules

- Prefer environment variables over new hard-coded absolute paths.
- Existing path defaults may stay for the owner's local environment, but new scripts should expose `--memory-dir` or relevant env overrides.
- Avoid baking new Feishu target IDs or account IDs into multiple files. Centralize or pass them as arguments where practical.
- Keep scripts runnable with the macOS system `python3` and the standard library unless there is a strong reason to add dependencies.

## Safe Validation

Run these checks after meaningful edits:

```bash
python3 -c "import ast, pathlib; files=sorted(pathlib.Path('scripts').glob('*.py')); [ast.parse(p.read_text(encoding='utf-8'), filename=str(p)) for p in files]; print('parsed', len(files), 'python files')"
```

```bash
python3 scripts/lmi_capture_inbox.py "诊断测试项" --kind idea --role 测试角色 --horizon weekly --memory-dir /private/tmp/lmi-diagnostic-memory
```

```bash
python3 scripts/lmi_clean_inbox.py --memory-dir /private/tmp/lmi-diagnostic-memory
```

```bash
python3 scripts/lmi_clean_inbox.py --memory-dir /private/tmp/lmi-diagnostic-memory --decision inbox-2026-05-20-001=tomorrow
```

```bash
python3 scripts/lmi_rebuild_inbox.py --memory-dir /private/tmp/lmi-diagnostic-memory
```

```bash
python3 scripts/lmi_focus_session.py --memory-dir /private/tmp/lmi-diagnostic-memory start --task "诊断测试专注" --task-class A --role 测试角色 --minutes 25 --high-return
```

```bash
python3 scripts/lmi_focus_session.py --memory-dir /private/tmp/lmi-diagnostic-memory end --result "诊断完成" --status completed --focus-score 5
```

```bash
python3 scripts/lmi_focus_reminder.py --dry-run --memory-dir /private/tmp/lmi-diagnostic-memory
```

```bash
bash scripts/check-sync.sh
```

## Change Discipline

- Keep edits small and focused.
- Preserve user or prior-agent changes in the working tree.
- Update README or references when changing user-visible workflows.
- Update scripts and templates together when a parser depends on a heading or table shape.
- If a live OpenClaw / Feishu regression is needed, follow `references/openclaw-feishu-lmi-regression-checklist.md`.
