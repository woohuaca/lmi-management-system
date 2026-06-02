#!/usr/bin/env python3
from __future__ import annotations

import re
import os
from datetime import date, datetime, timedelta
from io import StringIO
from pathlib import Path

from generate_lmi_weekly_plan import build_weekly_plan
from lmi_execution_support import decided_inbox_items_in_range, summarize_focus_range


def env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


PRIMARY_MEMORY_DIR = Path(os.environ.get('LMI_PRIMARY_MEMORY_DIR', '/Users/woohuaca/.openclaw/workspace-azai/memory')).expanduser()
ALLOW_MAIN_MEMORY_FALLBACK = env_flag('LMI_ALLOW_MAIN_MEMORY_FALLBACK', False)
FALLBACK_MEMORY_DIR = (
    Path(os.environ.get('LMI_FALLBACK_MEMORY_DIR', '/Users/woohuaca/.openclaw/workspace-main/memory')).expanduser()
    if ALLOW_MAIN_MEMORY_FALLBACK
    else None
)
PLACEHOLDER_MARKERS = (
    '待补充',
    '待确认',
    'missing',
    '信息不足',
    '待在今天执行后回填',
    '未回填',
    '____',
    '待今晚',
    '计划中',
)


def week_bounds(today: date) -> tuple[date, date]:
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)
    return monday, friday


def read_text(path: Path | None) -> str:
    if not path:
        return ''
    try:
        return path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return ''


def latest_matching(memory_dir: Path, patterns: list[str]) -> Path | None:
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(memory_dir.glob(pattern))
    return sorted(set(candidates))[-1] if candidates else None


def clean_md(text: str) -> str:
    value = text.strip()
    value = re.sub(r'\*\*(.+?)\*\*', r'\1', value)
    value = re.sub(r'`(.+?)`', r'\1', value)
    value = re.sub(r'~~(.+?)~~', r'\1', value)
    return re.sub(r'\s+', ' ', value).strip()


def strip_priority_label(text: str) -> str:
    value = clean_md(text)
    value = re.sub(r'^[A-D]\d?\s+', '', value)
    value = re.sub(r'^[A-D]\d?\s*:\s*', '', value)
    return value.strip()


def meaningful(text: str) -> bool:
    value = clean_md(text)
    return bool(value) and not any(marker in value for marker in PLACEHOLDER_MARKERS)


def dedupe_keep_order(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        norm = re.sub(r'\s+', ' ', item).strip().lower()
        if not norm or norm in seen:
            continue
        seen.add(norm)
        out.append(item.strip())
    return out


def first_meaningful(items: list[str]) -> str:
    for item in items:
        if meaningful(item):
            return clean_md(item)
    return ''


def current_month_monthly_plan(today: date) -> tuple[Path | None, str]:
    prefix = today.strftime('%Y-%m')
    patterns = [f'{prefix}_LMI_monthly_plan_complete.md', f'{prefix}_LMI_monthly_plan.md']
    primary = latest_matching(PRIMARY_MEMORY_DIR, patterns)
    if primary:
        return primary, 'workspace-azai/memory'
    if FALLBACK_MEMORY_DIR is not None:
        fallback = latest_matching(FALLBACK_MEMORY_DIR, patterns)
        if fallback:
            return fallback, 'workspace-main/memory (fallback)'
    return None, 'monthly plan missing'


def current_month_role_file(today: date) -> tuple[Path | None, str]:
    prefix = today.strftime('%Y-%m')
    patterns = [f'{prefix}_role_clarification.md']
    primary = latest_matching(PRIMARY_MEMORY_DIR, patterns)
    if primary:
        return primary, 'workspace-azai/memory'
    if FALLBACK_MEMORY_DIR is not None:
        fallback = latest_matching(FALLBACK_MEMORY_DIR, patterns)
        if fallback:
            return fallback, 'workspace-main/memory (fallback)'
    return None, 'role clarification missing'


def current_week_plan(monday: date, friday: date) -> tuple[Path | None, str]:
    patterns = [
        f'周计划-{monday.isoformat()}-{friday.strftime("%d")}.md',
        f'{monday.isoformat()}_weekly_plan.md',
    ]
    primary = latest_matching(PRIMARY_MEMORY_DIR, patterns)
    if primary:
        return primary, 'workspace-azai/memory'
    if FALLBACK_MEMORY_DIR is not None:
        fallback = latest_matching(FALLBACK_MEMORY_DIR, patterns)
        if fallback:
            return fallback, 'workspace-main/memory (fallback)'
    return None, 'weekly plan missing'


def lines_under(text: str, heading: str) -> list[str]:
    if not text:
        return []
    lines = text.splitlines()
    out: list[str] = []
    capture = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(heading):
            capture = True
            continue
        if capture and stripped.startswith('## '):
            break
        if capture and stripped:
            out.append(stripped)
    return out


def section_lines(text: str, heading_prefixes: list[str], stop_prefixes: list[str]) -> list[str]:
    if not text:
        return []
    out: list[str] = []
    capture = False
    for line in text.splitlines():
        stripped = line.strip()
        if any(stripped.startswith(prefix) for prefix in heading_prefixes):
            capture = True
            continue
        if capture and any(stripped.startswith(prefix) for prefix in stop_prefixes):
            break
        if capture:
            out.append(line.rstrip())
    return out


def parse_table_rows(lines: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith('|'):
            continue
        if re.match(r'^\|\s*[-: ]+\|', stripped):
            continue
        rows.append([clean_md(cell) for cell in stripped.strip('|').split('|')])
    return rows


def clean_status_text(text: str) -> str:
    value = clean_md(text)
    value = value.lstrip('> ').strip()
    value = re.sub(r'^[✅❌⚠️⏸️🔄🌟💡📌🚨📝📋🎯📚]+\s*', '', value)
    value = re.sub(r'^\d+\.\s*', '', value)
    return value.strip(' -')


def extract_primary_result(text: str) -> str:
    for line in lines_under(text, '## Today’s Primary Result'):
        stripped = clean_status_text(line)
        if stripped.startswith('- '):
            stripped = stripped[2:].strip()
        if meaningful(stripped):
            return stripped

    a_table = parse_table_rows(section_lines(text, ['## 🎯 今日重要事项（A级）'], ['## ']))
    for row in a_table:
        if len(row) >= 2 and row[0] != '优先级':
            candidate = clean_status_text(row[1])
            if meaningful(candidate):
                return candidate

    for line in lines_under(text, '## A：重要事项'):
        stripped = line.strip()
        if stripped.startswith('- '):
            candidate = clean_status_text(re.sub(r'^- ', '', stripped))
            candidate = strip_priority_label(candidate)
            if meaningful(candidate):
                return candidate
    return ''


def section_bullets(text: str, heading: str) -> list[str]:
    items: list[str] = []
    for line in lines_under(text, heading):
        stripped = line.strip()
        if stripped.startswith('- '):
            items.append(clean_md(stripped[2:]))
    return items


def parse_weekly_goals(text: str) -> list[str]:
    goals: list[str] = []
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if (
            stripped.startswith('| Priority | Role | Weekly goal |')
            or stripped.startswith('| 优先级 | 角色 | 本周目标 |')
            or stripped.startswith('| 优先级 | 角色 | 周目标 |')
        ):
            in_table = True
            continue
        if in_table and stripped.startswith('| ---'):
            continue
        if in_table and stripped.startswith('|'):
            parts = [p.strip() for p in stripped.strip('|').split('|')]
            if len(parts) >= 3 and parts[0] not in ('Priority', '优先级'):
                goals.append(f"{parts[0]} {strip_priority_label(parts[2])}")
            continue
        if in_table and stripped and not stripped.startswith('|'):
            break
    return dedupe_keep_order(goals)[:5]


def anchor_value(text: str, label: str) -> str:
    m = re.search(rf'-\s+{re.escape(label)}：\s*(.+)', text)
    return clean_md(m.group(1)) if m else ''


def monthly_top_goals(text: str) -> list[str]:
    items: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('🎯'):
            items.append(clean_md(stripped.lstrip('🎯').strip()))
    return dedupe_keep_order(items)[:4]


def role_weights(text: str) -> list[tuple[str, int]]:
    items: list[tuple[str, int]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith('| **'):
            continue
        parts = [p.strip() for p in stripped.strip('|').split('|')]
        if len(parts) < 3 or '角色' in parts[0]:
            continue
        role = clean_md(re.sub(r'^\d+\.\s*', '', re.sub(r'^\*\*|\*\*$', '', parts[0]).strip()))
        pct_match = re.search(r'(\d+)%', parts[2])
        if role and pct_match:
            items.append((role, int(pct_match.group(1))))
    items.sort(key=lambda item: (-item[1], item[0]))
    return items


def weekly_daily_files(monday: date, friday: date) -> list[tuple[date, Path, str]]:
    files: list[tuple[date, Path, str]] = []
    cursor = monday
    while cursor <= friday:
        rel = f'{cursor.isoformat()}.md'
        primary = PRIMARY_MEMORY_DIR / rel
        if primary.exists():
            files.append((cursor, primary, 'workspace-azai/memory'))
        else:
            if FALLBACK_MEMORY_DIR is not None:
                fallback = FALLBACK_MEMORY_DIR / rel
                if fallback.exists():
                    files.append((cursor, fallback, 'workspace-main/memory (fallback)'))
        cursor += timedelta(days=1)
    return files


def extract_completed(text: str) -> list[str]:
    items: list[str] = []
    for line in lines_under(text, '## Todays Completed Items'):
        stripped = line.strip()
        if stripped.startswith('- [x]'):
            items.append(clean_md(re.sub(r'^- \[x\]\s*', '', stripped)))
    custom_rows = parse_table_rows(section_lines(text, ['### ✅ 已完成事项'], ['### ', '## ']))
    for row in custom_rows:
        if len(row) >= 3 and row[0] != '时间':
            item = clean_status_text(row[1])
            result = clean_status_text(row[2])
            if meaningful(item) and meaningful(result):
                items.append(f'{item}：{result}')
            elif meaningful(result):
                items.append(result)
            elif meaningful(item):
                items.append(item)
    return dedupe_keep_order(items)


def extract_review_value(text: str, key: str) -> str:
    match = re.search(rf'-\s+{re.escape(key)}:\s*(.+)', text)
    if match and meaningful(match.group(1)):
        return clean_md(match.group(1))
    if key == 'Biggest progress':
        summary = extract_custom_summary(text)
        if summary:
            return summary
    return ''


def extract_unfinished(text: str) -> list[str]:
    items: list[str] = []
    capture = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == '## LMI Review Snapshot':
            capture = True
            continue
        if capture and stripped.startswith('## '):
            break
        if capture and stripped.startswith('- Unfinished items to re-decide:'):
            continue
        if capture and line.startswith('  - '):
            candidate = strip_priority_label(line[4:])
            if meaningful(candidate):
                items.append(candidate)
    custom_rows = parse_table_rows(section_lines(text, ['### 🔄 未完成事项与决策'], ['### ', '## ']))
    for row in custom_rows:
        if len(row) >= 3 and row[0] != '原目标':
            goal = clean_status_text(row[0])
            status = clean_status_text(row[1])
            decision = clean_status_text(row[2])
            if meaningful(goal) and meaningful(decision):
                items.append(f'{goal} -> {decision}')
            elif meaningful(goal) and meaningful(status):
                items.append(f'{goal} ({status})')
            elif meaningful(goal):
                items.append(goal)
    return dedupe_keep_order(items)


def extract_custom_summary(text: str) -> str:
    for line in section_lines(text, ['### 💡 一句话总结'], ['### ', '## ']):
        stripped = clean_status_text(line)
        if meaningful(stripped):
            return stripped
    return ''


def extract_tomorrow_first_move(text: str) -> str:
    standard = extract_review_value(text, 'Tomorrow First Move')
    if standard:
        return standard

    custom_items: list[str] = []
    for line in section_lines(text, ['### 🎯 Tomorrow First Move'], ['### ', '## ']):
        stripped = line.strip()
        if re.match(r'^\d+\.\s+', stripped):
            candidate = clean_status_text(re.sub(r'^\d+\.\s*', '', stripped))
            if meaningful(candidate):
                custom_items.append(candidate)
        elif stripped.startswith('- '):
            candidate = clean_status_text(stripped[2:])
            if meaningful(candidate):
                custom_items.append(candidate)
    return '；'.join(dedupe_keep_order(custom_items)[:2])


def extract_standard_worklog(text: str) -> list[str]:
    entries: list[str] = []
    for line in lines_under(text, '## Schedule'):
        stripped = line.strip()
        if not stripped.startswith('- '):
            continue
        raw = stripped[2:].strip()
        if any(marker in raw for marker in ('✅', '已完成', '🍅')):
            candidate = clean_status_text(raw)
            if meaningful(candidate):
                entries.append(candidate)
    for item in extract_completed(text):
        if meaningful(item):
            entries.append(item)
    return dedupe_keep_order(entries)[:4]


def extract_custom_worklog(text: str) -> list[str]:
    entries: list[str] = []
    rows = parse_table_rows(section_lines(text, ['### ✅ 已完成事项'], ['### ', '## ']))
    for row in rows:
        if len(row) >= 3 and row[0] != '时间':
            time_text = clean_status_text(row[0])
            item = clean_status_text(row[1])
            result = clean_status_text(row[2])
            pieces = [piece for piece in [time_text, item, result] if piece]
            candidate = ' | '.join(pieces)
            if meaningful(candidate):
                entries.append(candidate)
    return dedupe_keep_order(entries)[:4]


def extract_worklog(text: str) -> list[str]:
    custom = extract_custom_worklog(text)
    standard = extract_standard_worklog(text)
    return dedupe_keep_order(custom + standard)[:4]


def daily_review_status(progress: str, interruption: str, experience: str, completed: list[str], summary: str, worklog: list[str]) -> str:
    if any([progress, interruption, experience, summary, completed]):
        return 'reviewed'
    if worklog:
        return 'worklog-only'
    return 'plan-only'


def summarize_day(day: date, text: str, source: str) -> dict:
    completed = extract_completed(text)
    progress = extract_review_value(text, 'Biggest progress')
    interruption = extract_review_value(text, 'Main interruption')
    experience = extract_review_value(text, 'Work experience')
    unfinished = extract_unfinished(text)
    summary = extract_custom_summary(text)
    tomorrow_first_move = extract_tomorrow_first_move(text)
    worklog = extract_worklog(text)
    primary_result = extract_primary_result(text)
    status = daily_review_status(progress, interruption, experience, completed, summary, worklog)

    recap_parts: list[str] = []
    if status == 'plan-only':
        recap_parts.append('仅有日计划，未回填完成项/日复盘')
    elif status == 'worklog-only':
        recap_parts.append(f'有工作记录但未回填复盘：{"；".join(worklog[:2])}')
        if tomorrow_first_move:
            recap_parts.append(f'明日第一步：{tomorrow_first_move}')
    else:
        if progress:
            recap_parts.append(f'推进：{progress}')
        elif summary:
            recap_parts.append(summary)
        elif primary_result:
            recap_parts.append(f'核心事项：{primary_result}')
        if interruption:
            recap_parts.append(f'打断：{interruption}')
        if tomorrow_first_move:
            recap_parts.append(f'明日第一步：{tomorrow_first_move}')
    if not recap_parts:
        recap_parts.append('仅有日计划，未回填完成项/日复盘')

    return {
        'date': day.isoformat(),
        'source': source,
        'status': status,
        'primary_result': primary_result,
        'completed': completed,
        'progress': progress or summary,
        'interruption': interruption,
        'experience': experience,
        'unfinished': unfinished,
        'tomorrow_first_move': tomorrow_first_move,
        'worklog': worklog,
        'recap': '；'.join(recap_parts[:3]),
    }


def summarize_week(days: list[tuple[date, Path, str]]) -> dict:
    completed: list[str] = []
    progresses: list[str] = []
    interruptions: list[str] = []
    experiences: list[str] = []
    unfinished: list[str] = []
    sources: list[str] = []
    daily_recaps: list[dict] = []
    reviewed_days = 0
    worklog_only_days = 0
    plan_only_days = 0
    for day, path, source in days:
        text = read_text(path)
        day_info = summarize_day(day, text, source)
        daily_recaps.append(day_info)
        completed.extend(day_info['completed'])
        progress = day_info['progress']
        interruption = day_info['interruption']
        experience = day_info['experience']
        if progress:
            progresses.append(f'{day.isoformat()}: {progress}')
        if interruption:
            interruptions.append(f'{day.isoformat()}: {interruption}')
        if experience:
            experiences.append(f'{day.isoformat()}: {experience}')
        unfinished.extend(day_info['unfinished'])
        sources.append(f'{day.isoformat()} -> {source}')
        if day_info['status'] == 'reviewed':
            reviewed_days += 1
        elif day_info['status'] == 'worklog-only':
            worklog_only_days += 1
        else:
            plan_only_days += 1
    return {
        'completed': dedupe_keep_order(completed),
        'progresses': dedupe_keep_order(progresses),
        'interruptions': dedupe_keep_order(interruptions),
        'experiences': dedupe_keep_order(experiences),
        'unfinished': dedupe_keep_order(unfinished),
        'sources': sources,
        'daily_recaps': daily_recaps,
        'reviewed_days': reviewed_days,
        'worklog_only_days': worklog_only_days,
        'plan_only_days': plan_only_days,
    }


def goal_tokens(text: str) -> list[str]:
    tokens = re.findall(r'[\u4e00-\u9fffA-Za-z0-9→]+', strip_priority_label(text))
    cleaned: list[str] = []
    for token in tokens:
        if len(token) < 2:
            continue
        if token.isdigit():
            continue
        cleaned.append(token)
    return cleaned[:5]


def find_related_fact(goal: str, candidates: list[str]) -> str:
    tokens = goal_tokens(goal)
    best = ''
    best_score = 0
    goal_clean = strip_priority_label(goal)
    for candidate in candidates:
        candidate_clean = strip_priority_label(candidate)
        if not candidate_clean or candidate_clean == goal_clean:
            continue
        score = sum(1 for token in tokens if token in candidate_clean)
        if score > best_score:
            best_score = score
            best = candidate
        if score > 1:
            return candidate
    if best_score > 0:
        return best
    return ''


def infer_role_for_item(item: str, weighted_roles: list[tuple[str, int]]) -> str:
    clean = clean_md(item)
    low = clean.lower()
    rules = [
        (['客户', '漏斗', '装备制造', '轨道交通', '市场'], '新机会发现者'),
        (['charter', 'skill', 'pic'], 'CDT项目管理者'),
        (['prd', '需求', '原型', '设计'], '产品概念定义'),
        (['验证', 'poc', '价值'], '概念价值验证'),
    ]
    for keywords, role in rules:
        if any(keyword in clean or keyword in low for keyword in keywords):
            return role
    return weighted_roles[0][0] if weighted_roles else '待判断角色'


def main() -> None:
    today = date.today()
    monday, friday = week_bounds(today)
    week_label = f'{monday.isoformat()} to {friday.isoformat()}'

    monthly_path, monthly_source = current_month_monthly_plan(today)
    role_path, role_source = current_month_role_file(today)
    weekly_plan_path, weekly_plan_source = current_week_plan(monday, friday)

    monthly_text = read_text(monthly_path)
    role_text = read_text(role_path)
    weekly_plan_text = read_text(weekly_plan_path)

    month_goals = monthly_top_goals(monthly_text)
    weighted_roles = role_weights(role_text)
    weekly_goals = parse_weekly_goals(weekly_plan_text)
    week_role = (
        anchor_value(weekly_plan_text, 'Role to advance most this week')
        or anchor_value(weekly_plan_text, '本周主角色')
        or anchor_value(weekly_plan_text, '本周主推进角色')
    )

    days = weekly_daily_files(monday, friday)
    week_data = summarize_week(days)
    focus_summary, focus_source = summarize_focus_range(monday, friday)
    inbox_decisions, inbox_decision_source = decided_inbox_items_in_range(monday, friday)

    completed = week_data['completed']
    progresses = week_data['progresses']
    interruptions = week_data['interruptions']
    experiences = week_data['experiences']
    unfinished = week_data['unfinished']
    daily_recaps = week_data['daily_recaps']
    recap_facts = [f"{item['date']}: {item['recap']}" for item in daily_recaps if item['status'] != 'plan-only']
    worklog_facts = [f"{item['date']}: {'；'.join(item['worklog'][:2])}" for item in daily_recaps if item['worklog']]
    fact_pool = dedupe_keep_order(completed + progresses + unfinished + recap_facts + worklog_facts)

    overall = '待补充'
    if week_data['reviewed_days']:
        overall = f"已有 {week_data['reviewed_days']}/{len(days)} 天完成复盘，可据此做计划与实际对照"
    elif week_data['worklog_only_days']:
        overall = '已有部分工作记录，但复盘回填不足'
    review_buffer = StringIO()

    def emit(line: str = '') -> None:
        review_buffer.write(line + '\n')

    emit('## 周复盘概览')
    emit('')
    emit(f'- 复盘周期: {week_label}')
    emit(f'- 每日来源: {"；".join(week_data["sources"]) if week_data["sources"] else "缺少本周每日文件"}')
    emit(f'- 周计划来源: {weekly_plan_source}')
    emit(f'- 月计划来源: {monthly_source}')
    emit(f'- 角色澄清来源: {role_source}')
    emit(f'- 本周主题: {strip_priority_label(weekly_goals[0]) if weekly_goals else (month_goals[0] if month_goals else "待结合本周实际确认")}')
    emit(f'- 关联月目标: {"；".join(month_goals[:2]) if month_goals else "待补充"}')
    emit(f'- 整体完成度: {overall}')
    emit(f'- 复盘覆盖率: 已回填复盘 {week_data["reviewed_days"]} 天；仅有工作记录 {week_data["worklog_only_days"]} 天；仅有计划 {week_data["plan_only_days"]} 天')

    emit('')
    emit('## 每日复盘摘录')
    emit('')
    if daily_recaps:
        status_map = {
            'reviewed': '已回填复盘',
            'worklog-only': '仅有工作记录',
            'plan-only': '仅有计划',
        }
        for item in daily_recaps:
            emit(f'- {item["date"]} [{status_map.get(item["status"], item["status"])}]: {item["recap"]}')
    else:
        emit('- 本周没有读取到每日文件')

    emit('')
    emit('## 每日日工作亮点')
    emit('')
    if daily_recaps:
        for item in daily_recaps:
            if item['worklog']:
                emit(f'- {item["date"]}: {"；".join(item["worklog"][:3])}')
            else:
                emit(f'- {item["date"]}: 无可提取的当日工作记录')
    else:
        emit('- 本周没有读取到每日工作记录')

    emit('')
    emit('## 计划与实际对照')
    emit('')
    if weekly_goals:
        for goal in weekly_goals[:5]:
            goal_text = strip_priority_label(goal)
            related = find_related_fact(goal_text, fact_pool)
            progress = related if related else '待补充与该目标相关的实际结果'
            emit(f'- {goal}: {progress}')
    else:
        emit('- 待补充本周计划与实际对照')

    emit('')
    emit('## 角色复盘')
    emit('')
    if weighted_roles:
        best_role = infer_role_for_item(completed[0], weighted_roles) if completed else (week_role or weighted_roles[0][0])
        underserved = weighted_roles[0][0] if best_role != weighted_roles[0][0] else (weighted_roles[1][0] if len(weighted_roles) > 1 else best_role)
        emit(f'- 本周推进最好的角色: {best_role}')
        emit(f'- 本周投入不足的角色: {underserved}')
        emit('- 投入较多但回报偏弱的角色: 待结合本周低回报投入补充')
        emit('- 下周角色优先级调整: 依据本周事实调整最高权重角色的实际时间保护')
    else:
        emit('- 角色复盘数据不足')

    emit('')
    emit('## 专注时间复盘')
    emit('')
    if focus_summary['sessions']:
        role_parts = [f"{role} {minutes} min" for role, minutes in sorted(focus_summary['by_role'].items(), key=lambda item: item[1], reverse=True)]
        class_parts = [f"{task_class} {minutes} min" for task_class, minutes in sorted(focus_summary['by_class'].items(), key=lambda item: item[1], reverse=True)]
        emit(f'- 专注记录来源: {focus_source}')
        emit(f'- 总专注分钟: {focus_summary["total_minutes"]}')
        emit(f'- 按角色专注: {"；".join(role_parts)}')
        emit(f'- 按类别专注: {"；".join(class_parts)}')
        emit(f'- 高回报专注分钟: {focus_summary["high_return_minutes"]}')
        emit(f'- 中断次数: {focus_summary["interrupted_sessions"]}')
    else:
        emit('- 本周还没有专注记录；下周如果要做角色时间分析，建议至少记录 A1/A2 的开始与结束。')

    emit('')
    emit('## Inbox 去向汇总')
    emit('')
    if inbox_decisions:
        counts = {
            'tomorrow': sum(1 for item in inbox_decisions if item.get('decision') == 'tomorrow'),
            'this_week': sum(1 for item in inbox_decisions if item.get('decision') == 'this_week'),
            'project_fact_candidate': sum(1 for item in inbox_decisions if item.get('decision') == 'project_fact_candidate'),
            'discard': sum(1 for item in inbox_decisions if item.get('decision') == 'discard'),
        }
        emit(f'- Inbox 决策来源: {inbox_decision_source}')
        emit(f'- 本周转成明日执行: {counts["tomorrow"]} 项')
        emit(f'- 本周留在本周输入: {counts["this_week"]} 项')
        emit(f'- 本周转项目事实候选: {counts["project_fact_candidate"]} 项')
        emit(f'- 本周丢弃 / 仅记录: {counts["discard"]} 项')
    else:
        emit('- 本周还没有 Inbox 决策记录。')

    emit('')
    emit('## 高回报活动复盘')
    emit('')
    if progresses:
        emit(f'- 本周最有效的高回报活动: {progresses[0]}')
        emit('- 为什么有效: 待补充是因为时间块保护、方法有效还是协作顺畅')
    else:
        emit('- 本周最有效的高回报活动: 待补充')
        emit('- 为什么有效: 待补充')
    under_invested = unfinished[0] if unfinished else (strip_priority_label(weekly_goals[1]) if len(weekly_goals) > 1 else '待补充')
    repeatable = experiences[0] if experiences else (progresses[0] if progresses else '待补充')
    emit(f'- 投入不足的高回报活动: {under_invested}')
    emit(f'- 低回报时间投入: {interruptions[0] if interruptions else "待补充"}')
    emit(f'- 值得重复的做法: {repeatable}')

    emit('')
    emit('## 经验与洞察')
    emit('')
    if progresses:
        emit(f'- 最值得保留的经验: {progresses[0]}')
    else:
        emit('- 最值得保留的经验: 待补充')
    emit(f'- 已验证的方法/流程: {experiences[0] if experiences else "待补充"}')
    emit(f'- 下周停止重复的事: {interruptions[0] if interruptions else "待补充"}')
    emit('- 本周战略洞察: 待结合本周推进与客户/方案反馈补充')

    emit('')
    emit('## 延续与调整决策')
    emit('')
    continue_item = unfinished[0] if unfinished else (strip_priority_label(weekly_goals[0]) if weekly_goals else '待补充')
    adjust_item = unfinished[1] if len(unfinished) > 1 else (strip_priority_label(weekly_goals[1]) if len(weekly_goals) > 1 else '待补充')
    delegate_item = unfinished[2] if len(unfinished) > 2 else ('客户跟进状态整理或会议纪要整理' if weekly_goals else '待补充')
    emit(f'- 继续: {continue_item}')
    emit(f'- 启动或调整: {adjust_item}')
    emit(f'- 停止: {interruptions[0] if interruptions else "待补充"}')
    emit(f'- 授权/委托: {delegate_item}')
    emit('- 不滚动直接删除: 不再服务下周主角色与月目标的事项')
    emit(f'- 转入下周: {continue_item}')

    emit('')
    emit('## 根因复盘')
    emit('')
    emit(f'- 目标问题: {continue_item}')
    emit(f'- 执行问题: {interruptions[0] if interruptions else "待补充"}')
    emit('- 机制问题: 是否缺少固定检查点、保护时间块、委托机制或复盘闭环')
    emit('- 本周已做的战略调整: 待补充本周是否主动调整了方向、角色或节奏')

    emit('')
    emit('## 下周 GPS 预览')
    emit('')
    goal_preview = strip_priority_label(weekly_goals[0]) if weekly_goals else (month_goals[0] if month_goals else '待补充')
    emit(f'- 下周目标: {goal_preview}')
    emit('- 优先级:')
    emit(f'  - A1: {strip_priority_label(weekly_goals[0]) if len(weekly_goals) > 0 else "待补充"}')
    emit(f'  - A2: {strip_priority_label(weekly_goals[1]) if len(weekly_goals) > 1 else "待补充"}')
    emit(f'  - B: {strip_priority_label(continue_item)}')
    emit('- 关键步骤:')
    emit('  - 步骤1: 先保护下周最高回报时间块')
    emit('  - 步骤2: 明确必须亲自推进与可授权事项')
    emit('  - 步骤3: 删除不值得滚动的未完成事项')

    emit('')
    emit('## 其他观察')
    emit('')
    emit(f'- 本周工作体验线索: {"；".join(experiences[:3]) if experiences else "待补充"}')
    emit(f'- 本周打断线索: {"；".join(interruptions[:3]) if interruptions else "待补充"}')

    emit('')
    emit('## Next 1-3 Moves（接下来 1-3 步）')
    emit('')
    emit('- 先做计划与实际对照，而不是普通总结')
    emit('- 通过角色视角检查时间投入与结果是否一致')
    emit('- 直接把复盘转成下周 GPS 和保护时间块')

    review_body = review_buffer.getvalue().strip()
    plan_content, _next_week_path, _compat_path = build_weekly_plan(
        anchor_date=today,
        target_week_offset=1,
        title='LMI 下周计划草案',
        weekly_review_text_override=review_body,
        weekly_review_source_override='当前周复盘草案',
    )
    plan_lines = plan_content.strip().splitlines()
    plan_body = '\n'.join(plan_lines[1:]).lstrip() if plan_lines and plan_lines[0].startswith('# ') else plan_content.strip()

    combined_parts = [
        '# LMI 周复盘与下周计划',
        '',
        '## 一、本周复盘',
        '',
        review_body,
        '',
        '---',
        '',
        '## 二、下周计划',
        '',
        plan_body,
    ]
    print('\n'.join(combined_parts).rstrip() + '\n', end='')


if __name__ == '__main__':
    main()
