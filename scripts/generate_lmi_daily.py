#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
from datetime import date, datetime, time, timedelta
from pathlib import Path

PRIMARY_MEMORY_DIR = Path('/Users/woohuaca/.openclaw/workspace-azai/memory')
FALLBACK_MEMORY_DIR = Path('/Users/woohuaca/.openclaw/workspace-main/memory')
PLACEHOLDER_MARKERS = ('待补充', '待从', 'missing', '待确认', '待今晚', '待在今天')
GUIDANCE_MARKERS = ('当前无明确', '当前无固定', '建议开工前', '建议先补', '建议先快速补')


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return ''


def resolve_memory_file(rel_path: str) -> tuple[Path, str]:
    primary = PRIMARY_MEMORY_DIR / rel_path
    if primary.exists():
        return primary, 'workspace-azai/memory'
    fallback = FALLBACK_MEMORY_DIR / rel_path
    if fallback.exists():
        return fallback, 'workspace-main/memory (fallback)'
    return primary, 'workspace-azai/memory (missing)'


def section_lines(text: str, headings: list[str]) -> list[str]:
    if not text:
        return []
    lines = text.splitlines()
    out: list[str] = []
    capture = False
    for line in lines:
        stripped = line.strip()
        if any(stripped.startswith(h) for h in headings):
            capture = True
            continue
        if capture and stripped.startswith('#'):
            break
        if capture and stripped:
            out.append(stripped)
    return out


def meaningful(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    return not any(marker in stripped for marker in PLACEHOLDER_MARKERS + GUIDANCE_MARKERS)


def non_placeholder(items: list[str]) -> list[str]:
    return [item for item in items if meaningful(item)]


def extract_progress(yesterday: str) -> str:
    snapshot_match = re.search(r'## LMI Review Snapshot[\s\S]*?- Biggest progress:\s*(.+)', yesterday)
    if snapshot_match and meaningful(snapshot_match.group(1)):
        return snapshot_match.group(1).strip()
    completed = [ln for ln in section_lines(yesterday, ['### 已完成']) if ln.startswith('- [x]')]
    if completed:
        return re.sub(r'^- \[x\]\s*', '', completed[0])
    ongoing = [ln for ln in section_lines(yesterday, ['### 进行中']) if ln.startswith('- ')]
    if ongoing:
        return ongoing[0][2:]
    line_match = re.search(r'Biggest progress:\s*(.+)', yesterday)
    if line_match and meaningful(line_match.group(1)):
        return line_match.group(1).strip()
    return '待从昨天记录补充'


def extract_unfinished(yesterday: str) -> list[str]:
    items: list[str] = []
    in_snapshot = False
    capture_snapshot_items = False
    for line in yesterday.splitlines():
        stripped = line.strip()
        if stripped == '## LMI Review Snapshot':
            in_snapshot = True
            continue
        if in_snapshot and stripped.startswith('## '):
            break
        if in_snapshot and stripped.startswith('- Unfinished items to re-decide:'):
            capture_snapshot_items = True
            continue
        if in_snapshot and capture_snapshot_items:
            if stripped.startswith('- Tomorrow First Move:'):
                capture_snapshot_items = False
                continue
            if stripped.startswith('- ') or stripped.startswith('## '):
                capture_snapshot_items = False
            elif stripped.startswith('  - '):
                item = stripped[4:].strip()
                if meaningful(item) and item not in items:
                    items.append(item)
    for line in yesterday.splitlines():
        m = re.match(r'\d+\. \*\*(.+?)\*\*', line.strip())
        if m:
            items.append(m.group(1))
    pending = [ln for ln in section_lines(yesterday, ['### 已完成']) if ln.startswith('- [ ]')]
    for ln in pending:
        txt = re.sub(r'^- \[ \]\s*', '', ln)
        if txt not in items:
            items.append(txt)
    numbered = [ln for ln in section_lines(yesterday, ['### A 重要事项', '### B 紧要事项', '### C 联络/追踪事项', '### D 会议/协调事项']) if re.match(r'^\d+\.\s+\*\*', ln)]
    for ln in numbered:
        txt = re.sub(r'^\d+\.\s+\*\*', '', ln)
        txt = re.sub(r'\*\*.*$', '', txt).strip()
        if txt and txt not in items:
            items.append(txt)
    return non_placeholder(items)[:6]


def extract_tomorrow_first_move(yesterday: str) -> str:
    m = re.search(r'## LMI Review Snapshot[\s\S]*?- Tomorrow First Move:\s*(.+)', yesterday)
    if m and meaningful(m.group(1)):
        return m.group(1).strip()
    m = re.search(r'Tomorrow First Move:\s*(.+)', yesterday)
    if m and meaningful(m.group(1)):
        return m.group(1).strip()
    return ''


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


def strip_priority_prefix(item: str) -> str:
    return re.sub(r'^[A-D]\d?\s+', '', item).strip()


def explode_compound_items(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        clean = strip_priority_prefix(item)
        parts = [part.strip() for part in re.split(r'[；;]', clean) if part.strip()]
        if parts:
            out.extend(parts)
        elif clean:
            out.append(clean)
    return dedupe_keep_order(out)


def classify(items: list[str], primary_items: list[str] | None = None) -> tuple[list[str], list[str], list[str], list[str]]:
    a: list[str] = []
    b: list[str] = []
    c: list[str] = []
    d: list[str] = []
    primary_norm = {strip_priority_prefix(i).lower() for i in (primary_items or [])}
    for item in items:
        clean = strip_priority_prefix(item)
        low = clean.lower()
        if low in primary_norm:
            continue
        if any(k in clean for k in ['会议', '沟通', '对齐', '协调']) or any(k in low for k in ['sync', 'meeting', 'discussion']):
            d.append(item)
        elif any(k in clean for k in ['跟进', '联系', '触达', '回复', '客户']) or any(k in low for k in ['follow', 'contact', 'customer']):
            c.append(item)
        elif any(k in clean for k in ['提交', 'charter', '目标', '方案']) or any(k in low for k in ['charter', 'goal']):
            a.append(item)
        else:
            b.append(item)
    return dedupe_keep_order(a)[:3], dedupe_keep_order(b)[:3], dedupe_keep_order(c)[:3], dedupe_keep_order(d)[:3]


def today_schedule(today_text: str) -> list[str]:
    rows = []
    for line in today_text.splitlines():
        if re.match(r'^\|\s*\d{2}:\d{2}-\d{2}:\d{2}\s*\|', line.strip()):
            parts = [p.strip() for p in line.strip('|').split('|')]
            if len(parts) >= 2:
                rows.append(f'- {parts[0]} {parts[1]}')
    return rows[:6]


def parse_json_array(text: str) -> list[dict]:
    stripped = text.strip()
    if not stripped:
        return []
    if stripped.startswith('```'):
        stripped = re.sub(r'^```(?:json)?', '', stripped).strip()
        stripped = re.sub(r'```$', '', stripped).strip()
    match = re.search(r'(\[[\s\S]*\])', stripped)
    payload = match.group(1) if match else stripped
    try:
        data = json.loads(payload)
    except Exception:
        return []
    return data if isinstance(data, list) else []


def query_calendar_events(today: date) -> tuple[list[dict], str]:
    prompt = (
        '请直接使用飞书日历工具，查询今天（Asia/Shanghai）所有日程。'
        '只返回 JSON 数组，每项格式为 {"start":"HH:MM","end":"HH:MM","title":"..."}。'
        '如果今天没有任何日程，只返回 []。'
        '如果工具失败，只返回 ERROR。'
    )
    try:
        result = subprocess.run(
            [
                'openclaw',
                'agent',
                '--agent',
                'azai',
                '--channel',
                'feishu',
                '--message',
                prompt,
                '--json',
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except Exception as exc:
        return [], f'calendar query failed: {exc}'
    if result.returncode != 0:
        err = result.stderr.strip() or result.stdout.strip() or 'calendar query command failed'
        return [], f'calendar query failed: {err}'
    try:
        payload = json.loads(result.stdout)
        text = payload['result']['payloads'][0]['text']
    except Exception:
        text = result.stdout.strip()
    if 'ERROR' in text:
        return [], 'calendar query returned ERROR'
    events = parse_json_array(text)
    if events:
        return events, 'feishu calendar via azai'
    if text.strip() in ('[]', '**NO_EVENTS**', 'NO_EVENTS'):
        return [], 'feishu calendar via azai (no events today)'
    return [], 'calendar unavailable in azai runtime; using weekly-priority-based fallback blocks'


def hm(value: str) -> tuple[int, int] | None:
    m = re.match(r'^(\d{1,2}):(\d{2})$', value.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def minutes(value: str) -> int | None:
    parsed = hm(value)
    if not parsed:
        return None
    hour, minute = parsed
    return hour * 60 + minute


def minute_label(total: int) -> str:
    return f'{total // 60:02d}:{total % 60:02d}'


def overlaps_lunch(start: int, end: int) -> bool:
    lunch_start = 12 * 60
    lunch_end = 13 * 60 + 30
    return start < lunch_end and end > lunch_start


def build_focus_labels(a_items: list[str], c_items: list[str], d_items: list[str]) -> list[str]:
    labels: list[str] = []
    if a_items:
        labels.append(f'深度推进 -> {a_items[0]}')
    if len(a_items) > 1:
        labels.append(f'重点推进 -> {a_items[1]}')
    if len(a_items) > 2:
        labels.append(f'重点推进 -> {a_items[2]}')
    if c_items:
        joined = '；'.join(c_items[:2])
        labels.append(f'联络/跟进窗口 -> {joined}')
    if d_items:
        labels.append(f'协调 / 评审 / 对齐 -> {d_items[0]}')
    return labels


def schedule_from_calendar(events: list[dict], a_items: list[str], c_items: list[str], d_items: list[str]) -> list[str]:
    schedule: list[str] = []
    day_start = 8 * 60 + 30
    day_end = 18 * 60
    busy: list[tuple[int, int, str]] = []
    for event in events:
        start = minutes(str(event.get('start', '')))
        end = minutes(str(event.get('end', '')))
        title = str(event.get('title', '')).strip() or '日历事项'
        if start is None or end is None or end <= start:
            continue
        busy.append((start, end, title))
    busy.sort()
    free_slots: list[tuple[int, int]] = []
    cursor = day_start + 20
    schedule.append('- 08:30-08:50 晨间校准 -> 检查日历、确认 A1、收拢今天重点')
    for start, end, title in busy:
        if cursor < 12 * 60 <= start:
            if cursor < 12 * 60:
                free_end = min(start, 12 * 60)
                if free_end - cursor >= 45:
                    free_slots.append((cursor, free_end))
            schedule.append('- 12:00-13:30 午间留白 / 休息 / 碎务缓冲')
            cursor = max(cursor, 13 * 60 + 30)
        if start > cursor + 45 and not overlaps_lunch(cursor, start):
            free_slots.append((cursor, start))
        schedule.append(f'- {minute_label(start)}-{minute_label(end)} 日历安排 -> {title}')
        cursor = max(cursor, end + 10)
    if cursor < 12 * 60 < day_end and not any('午间留白' in row for row in schedule):
        if cursor < 12 * 60:
            block_end = 12 * 60
            if block_end - cursor >= 45:
                free_slots.append((cursor, block_end))
        schedule.append('- 12:00-13:30 午间留白 / 休息 / 碎务缓冲')
        cursor = max(cursor, 13 * 60 + 30)
    while cursor < day_end:
        if overlaps_lunch(cursor, min(cursor + 90, day_end)):
            if not any('午间留白' in row for row in schedule):
                schedule.append('- 12:00-13:30 午间留白 / 休息 / 碎务缓冲')
            cursor = max(cursor, 13 * 60 + 30)
            continue
        block_end = min(cursor + 90, day_end)
        if block_end - cursor < 45:
            break
        free_slots.append((cursor, block_end))
        cursor = block_end + 15

    labels = build_focus_labels(a_items, c_items, d_items)
    if free_slots and labels:
        longest_index = max(range(len(free_slots)), key=lambda i: free_slots[i][1] - free_slots[i][0])
        scheduled_focus: list[tuple[int, str]] = [(longest_index, labels[0])]
        remaining_labels = labels[1:]
        remaining_slot_indexes = [i for i in range(len(free_slots)) if i != longest_index]
        for slot_index, label in zip(remaining_slot_indexes, remaining_labels):
            scheduled_focus.append((slot_index, label))
        for slot_index, label in sorted(scheduled_focus):
            start, end = free_slots[slot_index]
            schedule.append(f'- {minute_label(start)}-{minute_label(end)} {label}')

    close_start = max(cursor, 17 * 60)
    if day_end - close_start >= 20:
        schedule.append(f'- {minute_label(close_start)}-{minute_label(day_end)} 收工整理 -> 回填完成事项，准备 Daily Review')
    schedule.sort(key=lambda row: minutes(row.split()[1].split('-')[0]) if re.match(r'^- \d{2}:\d{2}-', row) else 10**9)
    return schedule[:10]


def fallback_schedule(a_items: list[str], c_items: list[str], d_items: list[str]) -> list[str]:
    a1 = a_items[0] if a_items else 'A1 待补充'
    a2 = a_items[1] if len(a_items) > 1 else 'A2 待补充'
    a3 = a_items[2] if len(a_items) > 2 else ''
    follow_up = c_items[0] if c_items else (d_items[0] if d_items else '联络/协调事项待补充')
    closing = d_items[0] if d_items else '收工复盘与明日准备'
    schedule = [
        '- 08:30-08:50 晨间校准 -> 确认 A1、检查日历与昨日承接',
        f'- 09:00-10:30 深度推进 -> {a1}',
        f'- 10:45-12:00 重点推进 -> {a2}',
        '- 12:00-13:30 午间留白 / 休息 / 碎务缓冲',
    ]
    if a3:
        schedule.append(f'- 13:30-15:00 重点推进 -> {a3}')
        schedule.append(f'- 15:15-16:00 联络/跟进 -> {follow_up}')
    else:
        schedule.append(f'- 13:30-15:00 联络/跟进 -> {follow_up}')
    schedule.extend([
        f'- 16:00-17:00 协调 / 评审 / 对齐 -> {closing}',
        '- 17:00-17:30 收工整理 -> 回填完成事项，准备 Daily Review',
    ])
    return schedule


def build_followups(a_items: list[str], weekly_goals: list[str], weekly_hras_items: list[str]) -> list[str]:
    items: list[str] = []
    source = explode_compound_items(a_items + weekly_goals + weekly_hras_items)
    for raw in source:
        clean = strip_priority_prefix(raw)
        if not meaningful(clean):
            continue
        if '客户' in clean or '跟进' in clean:
            items.append(f'跟进{clean}')
        elif '提交' in clean and 'Charter' in clean:
            items.append('确认Charter提交状态，并跟进IPMT反馈')
        elif '方案启动' in clean:
            items.append('与相关人对齐新设计方案启动条件与下一步')
        elif '版本更新方向确定' in clean:
            items.append('对齐Charter版本更新方向，并确认责任人与时点')
    return dedupe_keep_order(items)[:3]


def build_urgent_items(a_items: list[str], unfinished: list[str], weekly_goals: list[str], c_items: list[str], d_items: list[str]) -> list[str]:
    urgency_words = ['今天', '尽快', '马上', '立即', '截止', '提交', '确认', '反馈', '回复', '风险']
    items: list[str] = []
    primary_norm = {strip_priority_prefix(item).lower() for item in a_items}
    followup_norm = {strip_priority_prefix(item).lower() for item in c_items}
    for source in [explode_compound_items(unfinished), explode_compound_items(weekly_goals)]:
        for raw in source:
            clean = strip_priority_prefix(raw)
            if not meaningful(clean):
                continue
            if clean.lower() in primary_norm:
                continue
            if clean.lower() in followup_norm:
                continue
            if any(sep in clean for sep in ['；', ';', '，']) and '确认' not in clean:
                continue
            if any(word in clean for word in urgency_words):
                items.append(clean)
    for item in d_items[:1]:
        if meaningful(item) and '待补充' not in item:
            items.append(item)
    return dedupe_keep_order(items)[:2]


def build_output(
    today: date,
    yesterday_source: str,
    biggest_progress: str,
    unfinished: list[str],
    tomorrow_first_move: str,
    carry: list[str],
    weekly_source: str,
    weekly_role: str,
    weekly_goals: list[str],
    weekly_hras_items: list[str],
    schedule_source: str,
    calendar_source: str,
    a_items: list[str],
    b_items: list[str],
    c_items: list[str],
    d_items: list[str],
    schedule: list[str],
) -> str:
    a_display = [strip_priority_prefix(item) for item in a_items]
    b_display = [strip_priority_prefix(item) for item in b_items]
    c_display = [strip_priority_prefix(item) for item in c_items]
    d_display = [strip_priority_prefix(item) for item in d_items]
    yesterday_progress_display = biggest_progress if meaningful(biggest_progress) else '昨晚未回填昨日进展，建议开工前先快速补一句昨天最重要推进。'
    tomorrow_first_move_display = strip_priority_prefix(tomorrow_first_move) if meaningful(tomorrow_first_move) else '昨晚未回填 Tomorrow First Move，建议先确认今天的第一步。'
    show_d_placeholder = bool(d_display) and all('待补充' in item for item in d_display)
    carry_display = carry[:2]
    weekly_anchor_lines: list[str] = []
    if weekly_role:
        weekly_anchor_lines.append(f'本周主角色：{weekly_role}')
    if weekly_goals:
        weekly_anchor_lines.append(f'本周关键结果：{"；".join(weekly_goals[:2])}')
    if weekly_hras_items:
        weekly_anchor_lines.append(f'本周高回报活动：{"；".join(weekly_hras_items[:2])}')
    out: list[str] = []
    out.append(f'# {today.isoformat()} LMI 日计划草案\n')
    out.append('## 昨日承接\n')
    out.append(f"- 昨日最大推进：{yesterday_progress_display}")
    if unfinished:
        out.append("- 今日待重新决策：")
        for item in unfinished[:5]:
            out.append(f'  - {item}')
    else:
        out.append("- 今日待重新决策：昨晚未回填未完成事项，建议先补 1-3 项仍需重新决策的事项。")
    out.append(f"- 延续到今天的第一步：{tomorrow_first_move_display}")
    out.append('- 今日承接决定：')
    for line in carry_display:
        out.append(f'  {line}')
    if weekly_anchor_lines:
        out.append('\n## 本周锚点\n')
        for line in weekly_anchor_lines:
            out.append(f'- {line}')
    if calendar_source == 'feishu calendar via azai (no events today)':
        out.append('\n## 日历状态\n')
        out.append('- 已成功读取飞书日历，今天没有日历事件；下方按周重点生成工作时间块。')
    elif calendar_source == 'feishu calendar via azai':
        out.append('\n## 日历状态\n')
        out.append('- 已成功读取飞书日历；下方日程结合今天的会议安排与可用时间块生成。')
    elif 'calendar query failed' in schedule_source or 'calendar unavailable' in schedule_source:
        out.append('\n## 日历状态\n')
        out.append('- 当前未能成功读取飞书日历；下方日程仍是 fallback block plan，不是 calendar-derived。')

    out.append('\n## Today’s Primary Result\n')
    out.append(f"- {a_display[0] if a_display else strip_priority_prefix(tomorrow_first_move)}")

    out.append('\n## A：重要事项\n')
    for i, item in enumerate(a_display, start=1):
        out.append(f'- A{i}: {item}')

    out.append('\n## B：紧要事项\n')
    if b_display and not all('待补充' in item for item in b_display):
        for i, item in enumerate(b_display, start=1):
            out.append(f'- B{i}: {item}')
    else:
        out.append('- 当前无明确紧急事项；如出现临时风险、截止或必须即时响应，再插入今天安排。')

    out.append('\n## C：联络/追踪事项\n')
    for i, item in enumerate(c_display, start=1):
        out.append(f'- C{i}: {item}')

    out.append('\n## D：会议/讨论/协调事项\n')
    if show_d_placeholder:
        out.append('- 当前无固定会议或讨论安排；预留机动协调时间处理临时沟通与对齐。')
    else:
        for i, item in enumerate(d_display, start=1):
            out.append(f'- D{i}: {item}')

    out.append('\n## Schedule\n')
    out.extend(schedule)

    out.append('\n## Todays Completed Items\n')
    out.append('- [ ] 待在今天执行后回填')

    out.append('\n## Quick Fill Before Review\n')
    out.append('- 完成了什么：至少补 1 条今天已完成事项，优先贴近 A1/A2。')
    out.append('- 最大推进：补 1 句今天最重要推进，哪怕只是部分推进。')
    out.append('- 最大打断：补 1 个今天最影响专注的打断或分心来源。')
    out.append('- 工作体验：补 1 句今天整体做事的感觉，以及最主要原因。')

    out.append('\n## Daily Review\n')
    out.append('- Biggest progress: 待今晚复盘填写')
    out.append('- Main interruption: 待今晚复盘填写')
    out.append('- Work experience: 待今晚复盘填写')
    out.append('- Roll forward or delegate: 今日收工前重新决策未完成事项')
    out.append('- Tomorrow First Move: 待今晚复盘填写')

    out.append('\n## Next 1-3 Moves\n')
    out.append(f"- 先确认 A1 是否仍是：{a_display[0] if a_display else strip_priority_prefix(tomorrow_first_move)}")
    out.append('- 把今日新增事项先分到 A/B/C/D，再决定是否进入今天')
    out.append('- 收工前补 Daily Review，并写下 Tomorrow First Move')
    return '\n'.join(out) + '\n'


def persist_daily_file(path: Path, content: str) -> None:
    path.write_text(content, encoding='utf-8')


def latest_weekly_plan(memory_dir: Path) -> Path | None:
    candidates = sorted(memory_dir.glob('周计划-*.md'))
    return candidates[-1] if candidates else None


def weekly_top_goals(text: str) -> list[str]:
    goals: list[str] = []
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == '## Weekly Top Goals':
            in_table = True
            continue
        if in_table and stripped.startswith('## '):
            break
        if in_table and stripped.startswith('|') and not stripped.startswith('| ---'):
            parts = [p.strip() for p in stripped.strip('|').split('|')]
            if len(parts) >= 3 and parts[0] != 'Priority':
                goal = parts[2]
                if goal and meaningful(goal):
                    goals.append(f'{parts[0]} {goal}')
    return goals[:4]


def weekly_hras(text: str) -> list[str]:
    items: list[str] = []
    for line in section_lines(text, ['## High-Return Activities']):
        if line.startswith('- Activity '):
            _, right = line.split(':', 1)
            value = right.strip()
            if meaningful(value):
                items.append(value)
    return items[:3]


def weekly_role_focus(text: str) -> str:
    m = re.search(r'Role to advance most this week:\s*(.+)', text)
    if m and meaningful(m.group(1)):
        return m.group(1).strip()
    return ''


def main() -> None:
    today = date.today()
    yesterday = today - timedelta(days=1)
    today_rel = f'{today.isoformat()}.md'
    yesterday_rel = f'{yesterday.isoformat()}.md'
    today_path, today_source = resolve_memory_file(today_rel)
    yesterday_path, yesterday_source = resolve_memory_file(yesterday_rel)

    today_text = read_text(today_path)
    yesterday_text = read_text(yesterday_path)
    weekly_path = latest_weekly_plan(PRIMARY_MEMORY_DIR) or latest_weekly_plan(FALLBACK_MEMORY_DIR)
    weekly_text = read_text(weekly_path) if weekly_path else ''
    weekly_source = 'workspace-azai/memory' if weekly_path and str(weekly_path).startswith(str(PRIMARY_MEMORY_DIR)) else ('workspace-main/memory (fallback)' if weekly_path else 'weekly plan missing')

    biggest_progress = extract_progress(yesterday_text)
    unfinished = extract_unfinished(yesterday_text)
    tomorrow_first_move = extract_tomorrow_first_move(yesterday_text)

    weekly_goals = weekly_top_goals(weekly_text)
    weekly_hras_items = weekly_hras(weekly_text)
    weekly_role = weekly_role_focus(weekly_text)
    if not meaningful(tomorrow_first_move):
        tomorrow_first_move = unfinished[0] if unfinished else (weekly_goals[0] if weekly_goals else '待从昨天复盘补充')

    exploded_weekly_goals = explode_compound_items(weekly_goals)
    combined_inputs = explode_compound_items(unfinished)
    for item in exploded_weekly_goals:
        if item not in combined_inputs:
            combined_inputs.append(item)
    for item in weekly_hras_items:
        if item not in combined_inputs:
            combined_inputs.append(item)

    a_seed = dedupe_keep_order(([tomorrow_first_move] if meaningful(tomorrow_first_move) else []) + exploded_weekly_goals + explode_compound_items(unfinished))[:3]
    a, b, c, d = classify(combined_inputs, primary_items=a_seed)
    schedule = today_schedule(today_text)
    schedule_source = today_source

    carry = []
    for item in unfinished[:3]:
        carry.append(f'- {item}: 今日重新决策（继续 / 延后 / 授权 / 删除）')
    if not carry:
        carry = ['- 昨晚未回填未完成事项，建议开工前先确认哪些需要继续、延后、授权或删除。']

    a_items = a_seed or (a if a else ['待你补充今天最重要的 1-2 个关键结果'])
    c_seed = build_followups(a_items, weekly_goals, weekly_hras_items)
    if c:
        for item in c:
            if item not in c_seed:
                c_seed.append(item)
    c_items = c_seed[:3] if c_seed else ['待补充今日需要联络或跟进的人与事项']
    d_items = d or ['待补充今天的会议 / 讨论 / 协调事项']
    b_items = build_urgent_items(a_items, unfinished, weekly_goals, c_items, d_items) or ['待补充今天必须处理的紧急事项']

    calendar_events, calendar_source = query_calendar_events(today)

    if not schedule and calendar_source.startswith('feishu calendar'):
        schedule = schedule_from_calendar(calendar_events, a_items, c_items, d_items)
        schedule_source = calendar_source

    if not schedule:
        schedule = fallback_schedule(a_items, c_items, d_items)
        schedule_source = calendar_source if calendar_source.startswith('calendar query failed') else 'calendar unavailable in azai runtime; using weekly-priority-based fallback blocks'

    output = build_output(
        today,
        yesterday_source,
        biggest_progress,
        unfinished,
        tomorrow_first_move,
        carry,
        weekly_source,
        weekly_role,
        weekly_goals,
        weekly_hras_items,
        schedule_source,
        calendar_source,
        a_items,
        b_items,
        c_items,
        d_items,
        schedule,
    )
    persist_daily_file(today_path, output)
    print(output, end='')


if __name__ == '__main__':
    main()
