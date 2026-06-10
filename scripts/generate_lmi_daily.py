#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from lmi_execution_support import load_inbox_snapshot, load_tomorrow_carry_items
from lmi_time_commitments import load_weekly_time_commitments


def env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


PRIMARY_MEMORY_DIR = Path(os.environ.get('LMI_PRIMARY_MEMORY_DIR', str(Path.home() / '.openclaw' / 'workspace-azai' / 'memory'))).expanduser()
ALLOW_MAIN_MEMORY_FALLBACK = env_flag('LMI_ALLOW_MAIN_MEMORY_FALLBACK', False)
FALLBACK_MEMORY_DIR = (
    Path(os.environ.get('LMI_FALLBACK_MEMORY_DIR', str(Path.home() / '.openclaw' / 'workspace-main' / 'memory'))).expanduser()
    if ALLOW_MAIN_MEMORY_FALLBACK
    else None
)
DISABLE_CALENDAR_QUERY = env_flag('LMI_DISABLE_CALENDAR_QUERY', False)
PLACEHOLDER_MARKERS = ('待补充', '待从', 'missing', '待确认', '待今晚', '待在今天')
GUIDANCE_MARKERS = ('当前无明确', '当前无固定', '当前无必须', '建议开工前', '建议先补', '建议先快速补')
SOURCE_WEIGHTS = {
    'weekly_goal': 120,
    'tomorrow_first_move': 105,
    'unfinished': 95,
    'monthly_goal': 70,
    'role_goal': 65,
    'weekly_hra': 55,
    'monthly_hra': 50,
    'weekly_schedule': 95,
    'today_schedule': 85,
    'calendar_event': 100,
}
PRIORITY_BONUS = {
    'A1': 20,
    'A2': 15,
    'A3': 10,
    'A': 8,
    'B': 4,
}
STREAM_RULES = [
    {
        'key': 'charter_skill',
        'patterns': ['charter skill', 'skill主体文档', '复盘会时间'],
        'canonical': 'Charter Skill完成主体文档 + 确定复盘会时间',
        'bucket': 'a',
    },
    {
        'key': 'opportunity_mvp',
        'patterns': ['机会洞察mvp', '用例/场景/测试集', '用例+场景'],
        'canonical': '机会洞察MVP打造（用例/场景/测试集）',
        'bucket': 'a',
    },
    {
        'key': 'customer_event',
        'patterns': ['客户活动', '现场活动', '客户价值验证'],
        'canonical': '客户活动价值验证',
        'bucket': 'a',
    },
    {
        'key': 'customer_pipeline',
        'patterns': ['重点意向客户', '意向客户', '转化漏斗', '客户转化', '下一阶段', '系统跟进'],
        'canonical': '重点意向客户推进，明确各客户下一阶段动作',
        'bucket': 'c',
    },
]
WEEKLY_GOAL_HEADINGS = ('## Weekly Top Goals', '## 本周目标', '## 本周关键目标')
WEEKLY_HRA_HEADINGS = ('## High-Return Activities', '## 高回报活动')
WEEKDAY_ALIASES = {
    0: {'Mon', 'Monday', '周一'},
    1: {'Tue', 'Tuesday', '周二'},
    2: {'Wed', 'Wednesday', '周三'},
    3: {'Thu', 'Thursday', '周四'},
    4: {'Fri', 'Friday', '周五'},
    5: {'Sat', 'Saturday', '周六'},
    6: {'Sun', 'Sunday', '周日'},
}
CARRY_FORWARD_HEADINGS = (
    '## A：重要事项',
    '### A：重要事项',
    '## B：紧要事项',
    '### B：紧要事项',
    '## C：联络/追踪事项',
    '### C：联络/追踪事项',
)
SCHEDULE_ADMIN_MARKERS = (
    '晨间校准',
    '午餐',
    '休息',
    '缓冲',
    '整理',
    '留白',
    '收工',
    '复盘',
    '返程',
    '抵达',
    '出发',
    '休整',
    '碎务',
)
LONG_BLOCK_THRESHOLD_MINUTES = 90
RECOVERY_BUFFER_MINUTES = 20
HEAVY_TASK_MARKERS = (
    '深度推进',
    '重点推进',
    '外出',
    '发布会',
    '拜访',
    '客户活动',
    '评审',
    '工作坊',
    '路演',
)
CALENDAR_SYNC_MARKERS = (
    '会议',
    '评审',
    '外出',
    '出发',
    '返程',
    '发布会',
    '拜访',
    '复盘',
    '对齐',
    '协调',
)
HARD_CONSTRAINT_MARKERS = (
    '会议',
    '交流',
    '评审',
    '拜访',
    '外出',
    '返程',
    '出发',
    '抵达',
    '客户活动',
    '发布会',
)
BUFFER_TASK_MARKERS = (
    '沉淀',
    '恢复',
    '缓冲',
    '收口',
)
LUNCH_TASK_MARKERS = (
    '午餐',
    '午间留白',
    '休息',
)
MORNING_CALIBRATION_MARKERS = (
    '晨间校准',
)
EXPLANATORY_PREFIXES = (
    '产出目标：',
    '关键输入：',
    '讨论要点：',
    '说明：',
    '为什么重要：',
    '判断标准：',
    '背景：',
    '备注：',
)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return ''


def resolve_memory_file(rel_path: str) -> tuple[Path, str]:
    primary = PRIMARY_MEMORY_DIR / rel_path
    if primary.exists():
        return primary, 'workspace-azai/memory'
    if FALLBACK_MEMORY_DIR is not None:
        fallback = FALLBACK_MEMORY_DIR / rel_path
        if fallback.exists():
            return fallback, 'workspace-main/memory (fallback)'
    return primary, 'workspace-azai/memory (missing)'


def latest_matching(memory_dir: Path, patterns: list[str]) -> Path | None:
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(memory_dir.glob(pattern))
    return sorted(set(candidates))[-1] if candidates else None


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


def lines_under_heading(text: str, heading: str) -> list[str]:
    if not text:
        return []
    lines = text.splitlines()
    out: list[str] = []
    capture = False
    heading_level = len(heading) - len(heading.lstrip('#'))
    for line in lines:
        stripped = line.strip()
        if stripped == heading:
            capture = True
            continue
        if capture and stripped.startswith('#'):
            current_level = len(stripped) - len(stripped.lstrip('#'))
            if current_level <= heading_level:
                break
        if capture and stripped:
            out.append(line.rstrip())
    return out


def top_level_bullets(text: str, headings: tuple[str, ...]) -> list[str]:
    items: list[str] = []
    for heading in headings:
        for line in lines_under_heading(text, heading):
            if line.startswith('- '):
                items.append(line[2:].strip())
    return dedupe_keep_order(items)


def meaningful(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    return not any(marker in stripped for marker in PLACEHOLDER_MARKERS + GUIDANCE_MARKERS)


def non_placeholder(items: list[str]) -> list[str]:
    return [item for item in items if meaningful(item)]


def is_explanatory_note(text: str) -> bool:
    clean = clean_md(strip_priority_prefix(text))
    return any(clean.startswith(prefix) for prefix in EXPLANATORY_PREFIXES)


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
    for bullet in top_level_bullets(yesterday, CARRY_FORWARD_HEADINGS):
        clean = strip_priority_prefix(bullet)
        if meaningful(clean) and not is_explanatory_note(clean):
            items.append(clean)

    in_snapshot = False
    capture_snapshot_items = False
    if not items:
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
                if line.startswith('  - '):
                    item = line[4:].strip()
                    if meaningful(item) and not is_explanatory_note(item) and item not in items:
                        items.append(item)
                    continue
                if stripped.startswith('- ') or stripped.startswith('## '):
                    capture_snapshot_items = False
    for line in yesterday.splitlines():
        m = re.match(r'\d+\. \*\*(.+?)\*\*', line.strip())
        if m:
            items.append(m.group(1))
    pending = [ln for ln in section_lines(yesterday, ['### 已完成']) if ln.startswith('- [ ]')]
    for ln in pending:
        txt = re.sub(r'^- \[ \]\s*', '', ln)
        if txt not in items and not is_explanatory_note(txt):
            items.append(txt)
    numbered = [ln for ln in section_lines(yesterday, ['### A 重要事项', '### B 紧要事项', '### C 联络/追踪事项', '### D 会议/协调事项']) if re.match(r'^\d+\.\s+\*\*', ln)]
    for ln in numbered:
        txt = re.sub(r'^\d+\.\s+\*\*', '', ln)
        txt = re.sub(r'\*\*.*$', '', txt).strip()
        if txt and txt not in items and not is_explanatory_note(txt):
            items.append(txt)
    return [item for item in non_placeholder(items) if not is_explanatory_note(item)][:6]


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


def first_meaningful(items: list[str]) -> str:
    for item in items:
        if meaningful(item):
            return item.strip()
    return ''


def clean_md(text: str) -> str:
    value = text.strip()
    value = re.sub(r'\*\*(.+?)\*\*', r'\1', value)
    value = re.sub(r'`(.+?)`', r'\1', value)
    return re.sub(r'\s+', ' ', value).strip()


def normalize_role_name(text: str) -> str:
    value = clean_md(text)
    value = re.sub(r'^\d+\.\s*', '', value)
    value = re.sub(r'^角色\d+[：:]\s*', '', value)
    return value.strip()


def is_operational_first_move(text: str) -> bool:
    value = clean_md(text)
    operational_markers = [
        '检查日程',
        '检查明日日程',
        '检查今天日程',
        '查看日历',
        '确认日历',
        '保护半天时间块',
        '安排时间块',
        '回填',
        '补填',
        '补昨天',
    ]
    return any(marker in value for marker in operational_markers)


def strip_priority_prefix(item: str) -> str:
    return re.sub(r'^[A-D]\d+\s*[:：]?\s*', '', item).strip()


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


def priority_code(text: str) -> str:
    match = re.match(r'^([A-D]\d?)\s+', clean_md(text))
    return match.group(1) if match else ''


def normalize_match_text(text: str) -> str:
    value = clean_md(strip_priority_prefix(text)).lower()
    value = value.replace('（', '(').replace('）', ')')
    value = value.replace('＋', '+').replace('：', ':')
    return re.sub(r'[\s/()\-_:]+', '', value)


def fallback_stream_key(text: str) -> str:
    normalized = normalize_match_text(text)
    normalized = re.sub(r'[^0-9a-z\u4e00-\u9fff]+', '', normalized)
    return normalized[:80] or clean_md(strip_priority_prefix(text))


def match_stream_rule(text: str) -> dict | None:
    normalized = normalize_match_text(text)
    for rule in STREAM_RULES:
        for pattern in rule['patterns']:
            if normalize_match_text(pattern) in normalized:
                return rule
    return None


def infer_bucket(text: str, *, explicit_rule: dict | None = None) -> str:
    if explicit_rule:
        return explicit_rule['bucket']
    clean = strip_priority_prefix(clean_md(text))
    low = clean.lower()
    if any(word in clean for word in ['会议', '沟通', '对齐', '协调', '讨论', '评审']):
        return 'd'
    if any(word in clean for word in ['跟进', '联系', '触达', '回复', '检查机制']):
        return 'c'
    if any(word in clean for word in ['出发', '返程', '抵达', '休整']):
        return 'd'
    if any(word in clean for word in ['完成', '打造', '验证', '调研', '文档', '方案', '输出', '整理']):
        return 'a'
    if any(word in low for word in ['charter', 'skill', 'mvp']):
        return 'a'
    return 'b'


def canonical_thread(text: str) -> tuple[str, str, str]:
    clean = strip_priority_prefix(clean_md(text))
    rule = match_stream_rule(clean)
    if rule:
        return rule['key'], rule['canonical'], infer_bucket(clean, explicit_rule=rule)
    return fallback_stream_key(clean), clean, infer_bucket(clean)


def source_weight(source: str, text: str, minutes_span: int = 0) -> int:
    score = SOURCE_WEIGHTS.get(source, 40)
    score += PRIORITY_BONUS.get(priority_code(text), 0)
    if minutes_span:
        score += min(minutes_span, 240) // 30 * 4
    return score


def parse_schedule_rows(schedule: list[str]) -> list[dict]:
    return [
        {
            'start': entry['start'],
            'end': entry['end'],
            'minutes': entry['minutes'],
            'task': (
                f"{entry['label']} -> {entry['task']}"
                if entry.get('label') and entry.get('task') and entry['label'] != entry['task']
                else entry.get('task', entry.get('label', ''))
            ),
        }
        for entry in parse_schedule_entries(schedule)
    ]


def parse_schedule_entries(schedule: list[str]) -> list[dict]:
    rows: list[dict] = []
    for raw in schedule:
        stripped = raw.strip()
        match = re.match(r'^-\s*(\d{2}:\d{2})-(\d{2}:\d{2})\s+(.+)$', stripped)
        if not match:
            continue
        start_label, end_label, rest = match.groups()
        start = minutes(start_label)
        end = minutes(end_label)
        if start is None or end is None or end <= start:
            continue
        parts = re.split(r'->|→', rest, maxsplit=1)
        label = clean_md(parts[0].strip())
        task = clean_md(parts[1].strip()) if len(parts) > 1 else label
        rows.append({
            'start': start,
            'end': end,
            'minutes': end - start,
            'label': label,
            'task': task,
            'raw': stripped,
        })
    return rows


def parse_calendar_rows(events: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for event in events:
        start = minutes(str(event.get('start', '')))
        end = minutes(str(event.get('end', '')))
        title = clean_md(str(event.get('title', '')).strip() or '日历事项')
        if start is None or end is None or end <= start:
            continue
        rows.append({
            'start': start,
            'end': end,
            'minutes': end - start,
            'task': title,
        })
    return rows


def is_admin_schedule_task(text: str) -> bool:
    return any(marker in text for marker in SCHEDULE_ADMIN_MARKERS)


def merge_thread_signal(
    threads: dict[str, dict],
    text: str,
    *,
    source: str,
    minutes_span: int = 0,
) -> None:
    if not meaningful(text):
        return
    key, canonical, default_bucket = canonical_thread(text)
    score = source_weight(source, text, minutes_span)
    thread = threads.get(key)
    if thread is None:
        thread = {
            'key': key,
            'title': canonical,
            'default_bucket': default_bucket,
            'bucket_scores': {'a': 0, 'b': 0, 'c': 0, 'd': 0},
            'score': 0,
            'scheduled_minutes': 0,
            'source_scores': {},
            'examples': [],
            'title_score': 0,
        }
        threads[key] = thread
    bucket = default_bucket
    thread['bucket_scores'][bucket] += score
    thread['score'] += score
    thread['source_scores'][source] = thread['source_scores'].get(source, 0) + score
    if source in {'weekly_schedule', 'today_schedule', 'calendar_event'}:
        thread['scheduled_minutes'] += minutes_span
    clean = strip_priority_prefix(clean_md(text))
    if clean and clean not in thread['examples']:
        thread['examples'].append(clean)
    if canonical and score >= thread['title_score']:
        thread['title'] = canonical
        thread['title_score'] = score


def final_bucket(thread: dict) -> str:
    bucket_scores = thread['bucket_scores']
    top_bucket = max(bucket_scores, key=lambda key: bucket_scores[key])
    default_bucket = thread['default_bucket']
    if bucket_scores.get(default_bucket, 0) >= bucket_scores.get(top_bucket, 0) - 12:
        return default_bucket
    return top_bucket


def active_schedule_minutes(rows: list[dict]) -> tuple[int, int]:
    active = [row['minutes'] for row in rows if not is_admin_schedule_task(row['task'])]
    return sum(active), max(active, default=0)


def is_heavy_schedule_task(text: str) -> bool:
    clean = strip_priority_prefix(clean_md(text))
    return any(marker in clean for marker in HEAVY_TASK_MARKERS)


def best_large_block(rows: list[dict]) -> dict | None:
    candidates = [
        row for row in rows
        if not is_admin_schedule_task(row['task']) and row['minutes'] >= LONG_BLOCK_THRESHOLD_MINUTES
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda row: (row['minutes'], -row['start']))


def has_fixed_commitment_rows(rows: list[dict]) -> bool:
    for row in rows:
        task = row['task']
        if is_admin_schedule_task(task):
            continue
        if any(marker in task for marker in CALENDAR_SYNC_MARKERS):
            return True
    return False


def calendar_read_succeeded(calendar_source: str) -> bool:
    return calendar_source in {
        'feishu calendar via azai',
        'feishu calendar via azai (no events today)',
        'feishu calendar via lark-cli',
        'feishu calendar via lark-cli (no events today)',
    }


def calendar_source_warning(calendar_source: str) -> str:
    if 'missing scope' in calendar_source:
        return '飞书日历读取还没授权 `calendar:calendar.event:read`，当前只能先按建议时间块排。'
    if 'authorization' in calendar_source:
        return '飞书日历读取授权异常，当前只能先按建议时间块排。'
    if not calendar_read_succeeded(calendar_source):
        return '当前时间安排仍需按真实飞书日历校正，不要把建议块当成最终版。'
    return ''


def schedule_entry_line(entry: dict) -> str:
    slot = f"{minute_label(entry['start'])}-{minute_label(entry['end'])}"
    label = entry.get('label', '').strip()
    task = entry.get('task', '').strip()
    if label and task and label != task:
        return f'{slot} {label} -> {task}'
    return f'{slot} {task or label}'.strip()


def schedule_entry_text(entry: dict) -> str:
    return f"- {schedule_entry_line(entry)}"


def is_lunch_schedule_task(text: str) -> bool:
    return any(marker in text for marker in LUNCH_TASK_MARKERS)


def is_buffer_schedule_task(text: str) -> bool:
    return any(marker in text for marker in BUFFER_TASK_MARKERS)


def is_closeout_schedule_task(text: str) -> bool:
    return any(marker in text for marker in ('收工整理', '复盘', '收口'))


def is_hard_constraint_entry(
    entry: dict,
    calendar_source: str,
    schedule_source: str,
    previous_hard_end: int | None,
) -> bool:
    label = clean_md(entry.get('label', ''))
    task = clean_md(entry.get('task', ''))
    combined = f'{label} {task}'.strip()
    if label == '日历安排':
        return True
    if schedule_source == 'synthetic fallback schedule':
        return False
    if previous_hard_end is not None and is_buffer_schedule_task(combined):
        return 0 <= entry['start'] - previous_hard_end <= 30
    if any(marker in combined for marker in HARD_CONSTRAINT_MARKERS):
        if not label.startswith(('A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3')):
            return True
    if calendar_read_succeeded(calendar_source):
        return False
    return False


def split_schedule_entries(schedule: list[str], calendar_source: str, schedule_source: str = '') -> tuple[list[dict], list[dict]]:
    hard_constraints: list[dict] = []
    planned_entries: list[dict] = []
    previous_hard_end: int | None = None
    for entry in parse_schedule_entries(schedule):
        combined = f"{entry['label']} {entry['task']}".strip()
        if any(marker in combined for marker in MORNING_CALIBRATION_MARKERS):
            previous_hard_end = None
            continue
        if is_lunch_schedule_task(combined):
            previous_hard_end = None
            continue
        if is_hard_constraint_entry(entry, calendar_source, schedule_source, previous_hard_end):
            hard_constraints.append(entry)
            previous_hard_end = entry['end']
            continue
        planned_entries.append(entry)
        previous_hard_end = None
    return hard_constraints, planned_entries


def is_meeting_like(text: str) -> bool:
    clean = strip_priority_prefix(clean_md(text))
    return any(word in clean for word in ['会议', '沟通', '对齐', '协调', '讨论', '评审', '交流'])


def is_displayable_meeting_item(text: str) -> bool:
    clean = strip_priority_prefix(clean_md(text))
    if re.match(r'^(将|整理|完成|形成|推进|沉淀|输出)', clean):
        return False
    return is_meeting_like(clean)


def is_contact_like(text: str) -> bool:
    clean = strip_priority_prefix(clean_md(text))
    low = clean.lower()
    rule = match_stream_rule(clean)
    if rule and rule['key'] == 'customer_pipeline':
        return True
    return any(word in clean for word in ['跟进', '联系', '触达', '回复']) or any(
        word in low for word in ['follow', 'contact']
    )


def is_urgent_like(text: str) -> bool:
    clean = strip_priority_prefix(clean_md(text))
    return any(word in clean for word in ['今天', '尽快', '马上', '立即', '截止', '必须', '风险', '确认', '回复'])


def is_important_like(text: str) -> bool:
    clean = strip_priority_prefix(clean_md(text))
    bucket = infer_bucket(clean)
    return bucket == 'a' and not is_meeting_like(clean) and not is_contact_like(clean)


def inbox_redecision_texts(inbox_items: list[dict], limit: int = 3) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for item in inbox_items:
        raw = clean_md(item.get('raw_text', ''))
        if not meaningful(raw):
            continue
        norm = normalize_match_text(raw)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        items.append(raw)
    return items[:limit]


def choose_lightweight_day_items(
    weekly_goals: list[str],
    monthly_goals: list[str],
    monthly_role_goals: list[str],
    unfinished: list[str],
    tomorrow_first_move: str,
    decided_for_today: list[str],
    inbox_items: list[dict],
    calendar_events: list[dict],
    calendar_source: str,
) -> tuple[list[str], list[str], list[str], list[str]]:
    inbox_texts = inbox_redecision_texts(inbox_items, limit=5)

    a_candidates: list[str] = []
    if meaningful(tomorrow_first_move):
        a_candidates.append(tomorrow_first_move)
    a_candidates.extend(decided_for_today)
    a_candidates.extend(weekly_goals)
    a_candidates.extend(unfinished)
    a_candidates.extend(monthly_goals)
    a_candidates.extend(monthly_role_goals)
    a_items = canonicalize_display_items([item for item in a_candidates if is_important_like(item)], limit=2)
    if not a_items:
        fallback = canonicalize_display_items(weekly_goals + unfinished + monthly_goals + monthly_role_goals, limit=2)
        a_items = fallback or ['待你补充今天最重要的 1-2 个关键结果']

    b_candidates = decided_for_today + unfinished + inbox_texts
    b_items = canonicalize_display_items([item for item in b_candidates if is_urgent_like(item)], limit=2)

    c_candidates = decided_for_today + unfinished + inbox_texts + weekly_goals + monthly_role_goals
    c_items = canonicalize_display_items([item for item in c_candidates if is_contact_like(item)], limit=2)

    d_candidates: list[str] = []
    if calendar_read_succeeded(calendar_source):
        d_candidates.extend(clean_md(str(event.get('title', '')).strip() or '日历事项') for event in calendar_events)
    d_candidates.extend(item for item in decided_for_today + unfinished + inbox_texts + weekly_goals if is_meeting_like(item))
    d_items = canonicalize_display_items(d_candidates, limit=3)
    return a_items, b_items, c_items, d_items


def choose_day_items(
    weekly_goals: list[str],
    monthly_goals: list[str],
    monthly_role_goals: list[str],
    unfinished: list[str],
    tomorrow_first_move: str,
    monthly_hras_items: list[str],
    weekly_hras_items: list[str],
    schedule_rows: list[dict],
    schedule_signal_source: str,
) -> tuple[list[str], list[str], list[str], list[str]]:
    threads: dict[str, dict] = {}
    for item in weekly_goals:
        merge_thread_signal(threads, item, source='weekly_goal')
    if meaningful(tomorrow_first_move):
        merge_thread_signal(threads, tomorrow_first_move, source='tomorrow_first_move')
    for item in unfinished:
        merge_thread_signal(threads, item, source='unfinished')
    for item in monthly_goals:
        merge_thread_signal(threads, item, source='monthly_goal')
    for item in monthly_role_goals:
        merge_thread_signal(threads, item, source='role_goal')
    for item in monthly_hras_items:
        merge_thread_signal(threads, item, source='monthly_hra')
    for item in weekly_hras_items:
        merge_thread_signal(threads, item, source='weekly_hra')
    for row in schedule_rows:
        if is_admin_schedule_task(row['task']):
            continue
        merge_thread_signal(threads, row['task'], source=schedule_signal_source, minutes_span=row['minutes'])

    ranked = sorted(
        threads.values(),
        key=lambda thread: (-thread['score'], -thread['scheduled_minutes'], thread['title']),
    )
    total_active_minutes, dominant_minutes = active_schedule_minutes(schedule_rows)
    a_cap = 2 if dominant_minutes >= 240 and total_active_minutes >= 300 else 3

    a_items = [thread['title'] for thread in ranked if final_bucket(thread) == 'a'][:a_cap]
    c_items = [thread['title'] for thread in ranked if final_bucket(thread) == 'c'][:3]
    d_items = [thread['title'] for thread in ranked if final_bucket(thread) == 'd'][:3]
    return a_items, [], c_items, d_items


def canonicalize_display_items(items: list[str], limit: int | None = None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        if not meaningful(item):
            continue
        _, canonical, _ = canonical_thread(item)
        normalized = normalize_match_text(canonical)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        out.append(canonical)
    return out[:limit] if limit else out


def current_month_monthly_plan(today: date) -> tuple[Path | None, str]:
    prefix = today.strftime('%Y-%m')
    patterns = [
        f'{prefix}_LMI_monthly_plan_complete.md',
        f'{prefix}_LMI_monthly_plan.md',
    ]
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
    patterns = [
        f'{prefix}_role_clarification.md',
    ]
    primary = latest_matching(PRIMARY_MEMORY_DIR, patterns)
    if primary:
        return primary, 'workspace-azai/memory'
    if FALLBACK_MEMORY_DIR is not None:
        fallback = latest_matching(FALLBACK_MEMORY_DIR, patterns)
        if fallback:
            return fallback, 'workspace-main/memory (fallback)'
    return None, 'role clarification missing'


def monthly_top_goals(text: str) -> list[str]:
    items: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('🎯'):
            items.append(clean_md(stripped.lstrip('🎯').strip()))
    if items:
        return dedupe_keep_order(items)[:4]
    capture = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('## Top Personal And Company Goals'):
            capture = True
            continue
        if capture and stripped.startswith('## '):
            break
        if capture and stripped.startswith('- '):
            items.append(clean_md(stripped[2:].strip()))
    return dedupe_keep_order(items)[:4]


def monthly_company_focus_goals(text: str) -> list[str]:
    items: list[str] = []
    for line in section_lines(text, ["## This Month's Company Focus Goals"]):
        stripped = line.strip()
        if stripped.startswith('- '):
            clean = re.sub(r'^- ', '', stripped)
            items.append(clean_md(clean))
    return dedupe_keep_order(items)[:4]


def monthly_hras(text: str) -> list[str]:
    items: list[str] = []
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('## High-Return Activity Items'):
            in_table = True
            continue
        if in_table and stripped.startswith('## '):
            break
        if in_table and stripped.startswith('|') and not stripped.startswith('|---') and '高回报活动' not in stripped:
            parts = [p.strip() for p in stripped.strip('|').split('|')]
            if parts and not all(part.replace('-', '') == '' for part in parts) and meaningful(parts[0]):
                items.append(clean_md(parts[0]))
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
        role_name = normalize_role_name(parts[0])
        pct_match = re.search(r'(\d+)%', parts[2])
        if role_name and pct_match:
            items.append((role_name, int(pct_match.group(1))))
    return items


def role_focus_from_current_month(text: str) -> str:
    weights = role_weights(text)
    if not weights:
        return ''
    weights.sort(key=lambda item: (-item[1], item[0]))
    return weights[0][0]


def role_key_goals(text: str, role_name: str) -> list[str]:
    if not text or not role_name:
        return []
    lines = text.splitlines()
    capture_role = False
    capture_goals = False
    items: list[str] = []
    for line in lines:
        stripped = line.strip()
        role_match = re.match(r'##\s+角色\d+：(.+?)（', stripped)
        if role_match:
            capture_role = normalize_role_name(role_match.group(1)) == normalize_role_name(role_name)
            capture_goals = False
            continue
        if capture_role and stripped.startswith('### 5月关键目标'):
            capture_goals = True
            continue
        if capture_role and capture_goals and stripped.startswith('### '):
            break
        if capture_role and capture_goals:
            goal_match = re.match(r'\d+\.\s+\*\*(.+?)\*\*[:：]?\s*(.*)', stripped)
            if goal_match:
                title = clean_md(goal_match.group(1).strip())
                rest = clean_md(goal_match.group(2).strip())
                items.append(f'{title}：{rest}' if rest else title)
            elif re.match(r'\d+\.\s+', stripped):
                items.append(clean_md(re.sub(r'^\d+\.\s+', '', stripped).strip()))
    return dedupe_keep_order(items)[:3]


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


LOCAL_TIMEZONE = timezone(timedelta(hours=8))


def format_calendar_clock(value) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if re.fullmatch(r'\d{2}:\d{2}', raw):
        return raw
    if raw.isdigit():
        timestamp = int(raw)
        if timestamp > 10**12:
            timestamp //= 1000
        return datetime.fromtimestamp(timestamp, tz=LOCAL_TIMEZONE).strftime('%H:%M')
    try:
        parsed = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=LOCAL_TIMEZONE)
        return parsed.astimezone(LOCAL_TIMEZONE).strftime('%H:%M')
    except ValueError:
        pass
    match = re.search(r'(\d{2}):(\d{2})', raw)
    if match:
        return f'{match.group(1)}:{match.group(2)}'
    return None


def extract_events_from_agenda_payload(payload) -> list[dict]:
    events: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    def maybe_add(node: dict) -> None:
        if not isinstance(node, dict):
            return
        start = (
            format_calendar_clock(node.get('start'))
            or format_calendar_clock(node.get('start_time'))
            or format_calendar_clock(node.get('display_start'))
        )
        end = (
            format_calendar_clock(node.get('end'))
            or format_calendar_clock(node.get('end_time'))
            or format_calendar_clock(node.get('display_end'))
        )
        title = clean_md(
            str(
                node.get('title')
                or node.get('summary')
                or node.get('event_title')
                or node.get('name')
                or ''
            )
        )
        if not start or not end or not title:
            return
        key = (start, end, title)
        if key in seen:
            return
        seen.add(key)
        events.append({'start': start, 'end': end, 'title': title})

    def walk(node) -> None:
        if isinstance(node, dict):
            maybe_add(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    events.sort(key=lambda item: (item['start'], item['end'], item['title']))
    return events


def query_calendar_events(today: date) -> tuple[list[dict], str]:
    if DISABLE_CALENDAR_QUERY:
        return [], 'calendar query disabled by env'
    try:
        result = subprocess.run(
            [
                'lark-cli',
                'calendar',
                '+agenda',
                '--as',
                'user',
                '--start',
                today.isoformat(),
                '--end',
                today.isoformat(),
                '--format',
                'json',
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except Exception as exc:
        return [], f'calendar query failed: {exc}'
    stdout = (result.stdout or '').strip()
    stderr = (result.stderr or '').strip()
    try:
        payload = json.loads(stdout) if stdout else {}
    except Exception:
        payload = {}
    if isinstance(payload, dict) and payload.get('ok') is False:
        error = payload.get('error') or {}
        subtype = str(error.get('subtype', '')).strip()
        message = str(error.get('message', '')).strip()
        if subtype == 'missing_scope' or 'missing required scope' in message.lower():
            return [], f'calendar authorization missing scope: {message}'
        return [], f'calendar authorization error: {message or stderr or "unknown"}'
    events = extract_events_from_agenda_payload(payload)
    if events:
        return events, 'feishu calendar via lark-cli'
    if result.returncode == 0:
        return [], 'feishu calendar via lark-cli (no events today)'
    err = stderr or stdout or 'calendar query command failed'
    return [], f'calendar query failed: {err}'


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
    return labels


def build_focus_suggestions(a_items: list[str], c_items: list[str], schedule: list[str]) -> list[str]:
    primary = a_items[0] if a_items else '今天主结果待补充'
    backup = a_items[1] if len(a_items) > 1 else (c_items[0] if c_items else '今天的下一步待补充')
    rows = parse_schedule_rows(schedule)
    total_active, dominant_minutes = active_schedule_minutes(rows)
    schedule_titles = [row['task'] for row in rows if not is_admin_schedule_task(row['task'])]
    if total_active >= 300 and dominant_minutes >= 180 and schedule_titles:
        hints = [
            f'- 建议把今天主线直接对准：{primary}',
            '- 主线结束后，留 20-30 分钟补记结果、洞察和后续动作。',
        ]
        if len(a_items) > 1:
            hints.append(f'- 如果晚间还有窗口，再推进一个最小下一步：{backup}')
        elif c_items:
            hints.append(f'- 如果主线提前收口，再顺带处理：{backup}')
        return hints
    return [
        f'- 建议先开 50 分钟专注块：{primary}',
        f'- 如果 A1 暂时被卡住，备用专注块：{backup}',
        '- 专注动作示例：`开始 A1 的 50 分钟专注` / `结束本轮专注，记录结果`',
    ]


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
        buffer_minutes = RECOVERY_BUFFER_MINUTES if (end - start) >= LONG_BLOCK_THRESHOLD_MINUTES or is_heavy_schedule_task(title) else 10
        buffer_end = min(end + buffer_minutes, day_end)
        if buffer_end - end >= 10 and not overlaps_lunch(end, buffer_end):
            if any(marker in title for marker in ['会议', '评审', '讨论', '交流', '对齐']):
                buffer_task = '会后沉淀 / 记录 / 恢复缓冲'
            else:
                buffer_task = '恢复 / 收口缓冲'
            schedule.append(f'- {minute_label(end)}-{minute_label(buffer_end)} {buffer_task}')
        cursor = max(cursor, buffer_end)
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


def ensure_closeout_block(schedule: list[str], primary_result: str) -> list[str]:
    if not schedule:
        return schedule
    if any(marker in row for row in schedule for marker in ['收工整理', '复盘', '洞察整理', '收口']):
        return schedule
    rows = parse_schedule_rows(schedule)
    if not rows:
        return schedule
    last_end = max(row['end'] for row in rows)
    day_end = 18 * 60
    if day_end - last_end < 20:
        return schedule
    if '客户活动' in primary_result:
        close_label = '现场收口 -> 整理客户洞察与后续动作'
    else:
        close_label = f'收工整理 -> 收口 {primary_result} 的结果与下一步'
    return schedule + [f'- {minute_label(last_end)}-{minute_label(day_end)} {close_label}']


def schedule_suggestions_without_calendar(rows: list[str], primary_result: str) -> list[str]:
    if not rows:
        return [
            '- 当前未接入自动飞书日历；请先确认今天固定会议后，再排 A1 / A2 的时间块。',
            f'- 优先为 `{primary_result}` 预留今天最完整的 90-180 分钟连续大块，不要塞进碎片时间。',
            f'- 长任务、外出或密集会议后，至少预留 {RECOVERY_BUFFER_MINUTES}-30 分钟恢复 / 收口缓冲。',
            '- 一旦今天的固定会议、外出或关键推进块确认，请同步更新到飞书日历。',
        ]
    suggestions = ['- 当前未接入自动飞书日历；以下仅为建议时间块，需先按真实日历校正。']
    for row in rows[:5]:
        if '->' in row:
            left, right = row.split('->', 1)
            suggestions.append(f'{left}-> 建议：{right.strip()}')
        else:
            suggestions.append(f'{row}（建议）')
    parsed_rows = parse_schedule_rows(rows)
    best_block = best_large_block(parsed_rows)
    if best_block:
        suggestions.append(
            f"- 建议把 `{primary_result}` 放进今天最完整的大块："
            f"{minute_label(best_block['start'])}-{minute_label(best_block['end'])}。"
        )
    if any(
        row['minutes'] >= LONG_BLOCK_THRESHOLD_MINUTES or is_heavy_schedule_task(row['task'])
        for row in parsed_rows
        if not is_admin_schedule_task(row['task'])
    ):
        suggestions.append(
            f'- 若今天有长任务 / 外出 / 密集会议，后面请至少留 {RECOVERY_BUFFER_MINUTES}-30 分钟恢复或收口，不建议重任务无缝连排。'
        )
    if has_fixed_commitment_rows(parsed_rows):
        suggestions.append('- 今天已知的固定承诺一旦确认，请同步写进飞书日历，避免计划与真实安排继续漂移。')
    return suggestions


def build_followups(a_items: list[str], weekly_goals: list[str], weekly_hras_items: list[str]) -> list[str]:
    items: list[str] = []
    source = explode_compound_items(a_items + weekly_goals + weekly_hras_items)
    has_customer_pipeline = False
    for raw in source:
        clean = strip_priority_prefix(raw)
        if not meaningful(clean):
            continue
        if '重点客户进度对齐会' in clean or ('对齐会' in clean and '客户' in clean):
            items.append('确认重点客户进度对齐会的安排、结论与下一步')
        elif '客户' in clean or '跟进' in clean:
            has_customer_pipeline = True
            continue
        elif clean.startswith(('跟进', '联系', '确认')):
            items.append(clean)
        elif clean.startswith('系统跟进'):
            has_customer_pipeline = True
            continue
        elif '客户转化加速' in clean:
            has_customer_pipeline = True
            continue
        elif '提交' in clean and 'Charter' in clean:
            items.append('确认Charter提交状态，并跟进IPMT反馈')
        elif '方案启动' in clean:
            items.append('与相关人对齐新设计方案启动条件与下一步')
        elif '版本更新方向确定' in clean:
            items.append('对齐Charter版本更新方向，并确认责任人与时点')
    if has_customer_pipeline:
        items.insert(0, '推进重点意向客户跟进，推动进入下一阶段')
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


def arranged_sections(schedule: list[str], calendar_source: str, schedule_source: str = '') -> list[tuple[str, list[str]]]:
    _hard_constraints, planned_entries = split_schedule_entries(schedule, calendar_source, schedule_source)
    sections: dict[str, list[str]] = {
        '上午主块': [],
        '下午第一主块': [],
        '下午第二主块': [],
        '弹性块': [],
    }
    afternoon_slots_used = 0
    for entry in planned_entries:
        combined = f"{entry['label']} {entry['task']}".strip()
        if is_closeout_schedule_task(combined):
            sections['弹性块'].append(schedule_entry_text(entry))
            continue
        if entry['start'] < 12 * 60:
            sections['上午主块'].append(schedule_entry_text(entry))
            continue
        if afternoon_slots_used == 0:
            sections['下午第一主块'].append(schedule_entry_text(entry))
            afternoon_slots_used += 1
            continue
        if afternoon_slots_used == 1:
            sections['下午第二主块'].append(schedule_entry_text(entry))
            afternoon_slots_used += 1
            continue
        sections['弹性块'].append(schedule_entry_text(entry))
    return [(title, rows) for title, rows in sections.items() if rows]


def hard_constraint_lines(schedule: list[str], calendar_source: str, schedule_source: str = '') -> list[str]:
    hard_constraints, _planned_entries = split_schedule_entries(schedule, calendar_source, schedule_source)
    return [schedule_entry_text(entry) for entry in hard_constraints]


def build_not_in_mainline_items(
    a_items: list[str],
    b_items: list[str],
    c_items: list[str],
    d_items: list[str],
    unfinished: list[str],
    inbox_items: list[str],
) -> list[str]:
    selected_norms = {
        normalize_match_text(item)
        for item in a_items[:2] + b_items[:1] + c_items[:1] + d_items[:1]
        if meaningful(item)
    }
    candidates = dedupe_keep_order(
        unfinished
        + inbox_items
        + a_items[2:]
        + b_items[1:]
        + c_items[1:]
        + d_items[1:]
    )
    out: list[str] = []
    for item in candidates:
        clean = strip_priority_prefix(item)
        if is_explanatory_note(clean):
            continue
        if normalize_match_text(clean) in selected_norms:
            continue
        out.append(f'{clean}：今天先不抢主位，收工前再决定是否进明天。')
    return out[:3]


def build_plan_logic(
    primary_result: str,
    schedule: list[str],
    calendar_source: str,
    schedule_source: str,
    b_items: list[str],
    c_items: list[str],
    inbox_items: list[str],
) -> list[str]:
    hard_lines = hard_constraint_lines(schedule, calendar_source, schedule_source)
    section_titles = [title for title, _rows in arranged_sections(schedule, calendar_source, schedule_source)]
    notes: list[str] = []
    if hard_lines:
        notes.append('先锁硬约束，再从剩余整块里保护主线，不让会议和切换把主结果打碎。')
    else:
        notes.append('今天暂未识别出已确认硬约束，开工前先核对飞书日历，再最终锁定主线。')
    if primary_result and any(title in section_titles for title in ('上午主块', '下午第一主块')):
        notes.append(f'把 `{primary_result}` 放进今天最完整的大块，先求可讨论版本，再求完整收尾。')
    if any(is_buffer_schedule_task(row) for row in hard_lines):
        notes.append('长会议 / 外出后明确留出沉淀与恢复缓冲，避免硬切到下一件事。')
    if b_items or c_items:
        notes.append('B/C 类事项放在主线之后承接，只解决必要推进，不抢占最好时间。')
    if inbox_items:
        notes.append('Inbox 只作为重决策输入，不自动升级成今天主线。')
    if not calendar_read_succeeded(calendar_source):
        notes.append('当前时间安排仍是建议版，需按真实日历再校正一次。')
    return dedupe_keep_order(notes)[:4]


def build_output(
    today: date,
    yesterday_source: str,
    biggest_progress: str,
    unfinished: list[str],
    decided_for_today: list[str],
    tomorrow_first_move: str,
    carry: list[str],
    weekly_goals: list[str],
    weekly_warning: str,
    inbox_items: list[str],
    schedule_source: str,
    calendar_source: str,
    a_items: list[str],
    b_items: list[str],
    c_items: list[str],
    d_items: list[str],
    schedule: list[str],
) -> str:
    a_display = [strip_priority_prefix(item) for item in a_items if not is_explanatory_note(item)]
    a_norms = {normalize_match_text(item) for item in a_display if meaningful(item)}
    b_display = [strip_priority_prefix(item) for item in b_items if not is_explanatory_note(item) and normalize_match_text(item) not in a_norms]
    c_display = [strip_priority_prefix(item) for item in c_items if not is_explanatory_note(item) and normalize_match_text(item) not in a_norms]
    c_norms = a_norms | {normalize_match_text(item) for item in c_display if meaningful(item)}
    d_display = [
        strip_priority_prefix(item)
        for item in d_items
        if not is_explanatory_note(item)
        and normalize_match_text(item) not in c_norms
        and is_displayable_meeting_item(item)
    ]
    yesterday_progress_display = biggest_progress if meaningful(biggest_progress) else '昨晚未回填昨日进展，建议开工前先快速补一句昨天最重要推进。'
    tomorrow_first_move_display = strip_priority_prefix(tomorrow_first_move) if meaningful(tomorrow_first_move) else '昨晚未回填 Tomorrow First Move，建议先确认今天的第一步。'
    carry_display = carry[:2]
    warning_lines: list[str] = []
    if weekly_warning:
        warning_lines.append(weekly_warning)
    calendar_warning = calendar_source_warning(calendar_source)
    if calendar_warning:
        warning_lines.append(calendar_warning)
    hard_lines = hard_constraint_lines(schedule, calendar_source, schedule_source)
    arranged = arranged_sections(schedule, calendar_source, schedule_source)
    not_in_mainline = build_not_in_mainline_items(
        a_display,
        b_display,
        c_display,
        d_display,
        unfinished,
        inbox_items,
    )
    logic_notes = build_plan_logic(
        a_display[0] if a_display else strip_priority_prefix(tomorrow_first_move),
        schedule,
        calendar_source,
        schedule_source,
        b_display,
        c_display,
        inbox_items,
    )
    out: list[str] = []
    out.append(f'# {today.isoformat()} LMI 日计划草案\n')
    out.append('## 昨日承接\n')
    out.append(f"- 昨日最大推进：{yesterday_progress_display}")
    if decided_for_today:
        out.append("- 昨晚 Inbox 已决策进今天：")
        for item in decided_for_today[:3]:
            out.append(f'  - {item}')
    if unfinished:
        out.append("- 今日待重新决策：")
        for item in unfinished[:3]:
            out.append(f'  - {item}')
    else:
        out.append("- 今日待重新决策：昨晚未回填未完成事项。")
    if inbox_items:
        out.append("- Inbox 待重新决策：")
        for item in inbox_items[:3]:
            out.append(f'  - {item}')
    out.append(f"- 延续到今天的第一步：{tomorrow_first_move_display}")
    out.append('- 今日承接决定：')
    for line in carry_display:
        out.append(f'  {line}')
    if warning_lines:
        out.append('\n## 规划提醒\n')
        for line in warning_lines:
            out.append(f'- {line}')

    out.append('\n## 今日主结果\n')
    out.append(f"- A1: {a_display[0] if a_display else strip_priority_prefix(tomorrow_first_move)}")
    if weekly_goals:
        out.append(f'- 承接本周关键结果：{strip_priority_prefix(weekly_goals[0])}')

    out.append('\n## 硬约束\n')
    if hard_lines:
        out.extend(hard_lines)
    else:
        out.append('- 当前没有已确认硬约束；请先核对飞书日历，再最终锁定主线。')

    out.append('\n## 今日时间安排\n')
    if arranged:
        for title, rows in arranged:
            out.append(f'\n### {title}\n')
            out.extend(rows)
    else:
        out.append('- 当前还没有可执行时间块；请先确认今天的固定安排。')

    out.append('\n## 事项归位\n')
    out.append('\n### A：重要事项\n')
    for i, item in enumerate(a_display, start=1):
        out.append(f'- A{i}: {item}')

    out.append('\n### B：紧要事项\n')
    if b_display and not all('待补充' in item for item in b_display):
        for i, item in enumerate(b_display, start=1):
            out.append(f'- B{i}: {item}')
    else:
        out.append('- 当前无明确紧急事项；如出现临时风险、截止或必须即时响应，再插入今天安排。')

    out.append('\n### C：联络/追踪事项\n')
    if c_display:
        for i, item in enumerate(c_display, start=1):
            out.append(f'- C{i}: {item}')
    else:
        out.append('- 当前无必须单列的联络/追踪事项。')

    out.append('\n### D：会议/讨论/协调事项\n')
    if d_display:
        for i, item in enumerate(d_display, start=1):
            out.append(f'- D{i}: {item}')
    else:
        out.append('- 今天没有需要单列的会议决策项；固定安排已放在硬约束里。')

    out.append('\n## 今天不排入主线\n')
    if not_in_mainline:
        for item in not_in_mainline:
            out.append(f'- {item}')
    else:
        out.append('- 当前没有明显需要刻意压住的不抢主位事项。')

    out.append('\n## 这样排的逻辑\n')
    for note in logic_notes:
        out.append(f'- {note}')

    out.append('\n## 收工前\n')
    out.append('- 回填 1 条完成事项 + 1 句最大推进。')
    out.append('- 重新决策未完成事项，并写明天第一步。')

    out.append('\n## Todays Completed Items\n')
    out.append('- [ ] 待在今天执行后回填')

    out.append('\n## Daily Review\n')
    out.append('- Biggest progress: 待今晚复盘填写')
    out.append('- Main interruption: 待今晚复盘填写')
    out.append('- Work experience: 待今晚复盘填写')
    out.append('- Roll forward or delegate: 今日收工前重新决策未完成事项')
    out.append('- Tomorrow First Move: 待今晚复盘填写')

    out.append('\n## 接下来 1-3 步\n')
    out.append(f"- 先按今日主结果开工：{a_display[0] if a_display else strip_priority_prefix(tomorrow_first_move)}")
    if hard_lines:
        out.append('- 先执行硬约束，再直接进入第一块主线，不在中间重开新题。')
    else:
        out.append('- 先核对飞书日历里的固定安排，再启动第一块主线。')
    if inbox_items:
        out.append('- 把新增事项先收进 Inbox，收工前再决定是否进入明天，不自动塞进主线。')
    elif decided_for_today:
        out.append('- 只承接昨晚已经决策进今天的事项，不再额外扩充主线。')
    else:
        out.append('- 把新增事项先收进 Inbox，再决定是否进入今天。')
    out.append('- 收工前补日复盘，并写下明天第一步。')
    return '\n'.join(out) + '\n'


def persist_daily_file(path: Path, content: str) -> None:
    path.write_text(content, encoding='utf-8')


def latest_weekly_plan(memory_dir: Path) -> Path | None:
    candidates = list(memory_dir.glob('周计划-*.md')) + list(memory_dir.glob('*_weekly_plan.md'))
    candidates = [path for path in candidates if path.is_file()]
    if not candidates:
        return None
    candidates.sort(key=lambda path: (path.stat().st_mtime, path.name))
    return candidates[-1]


def weekly_top_goals(text: str) -> list[str]:
    goals: list[str] = []
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped in WEEKLY_GOAL_HEADINGS:
            in_table = True
            continue
        if in_table and stripped.startswith('## '):
            break
        if in_table and stripped.startswith('|') and not re.fullmatch(r'\|\s*[-:| ]+\|?', stripped):
            parts = [p.strip() for p in stripped.strip('|').split('|')]
            if len(parts) >= 3 and parts[0] not in {'Priority', '优先级'}:
                goal = clean_md(parts[2])
                if goal and meaningful(goal):
                    goals.append(f'{parts[0]} {goal}')
    if goals:
        return goals[:4]
    return goals[:4]


def weekly_hras(text: str) -> list[str]:
    items: list[str] = []
    for line in section_lines(text, list(WEEKLY_HRA_HEADINGS)):
        if line.startswith(('- Activity ', '- 活动')):
            _, right = line.split(':', 1)
            value = clean_md(right.strip())
            if meaningful(value):
                items.append(value)
    return items[:3]


def weekly_role_focus(text: str) -> str:
    m = re.search(r'Role to advance most this week:\s*(.+)', text)
    if m and meaningful(m.group(1)):
        return m.group(1).strip()
    m = re.search(r'-\s*本周主角色[:：]\s*(.+)', text)
    if m and meaningful(m.group(1)):
        return clean_md(m.group(1))
    m = re.search(r'-\s*本周主推进角色[:：]\s*(.+)', text)
    if m and meaningful(m.group(1)):
        return clean_md(m.group(1))
    return ''


WEEKDAY_TO_CN = {
    0: '周一',
    1: '周二',
    2: '周三',
    3: '周四',
    4: '周五',
    5: '周六',
    6: '周日',
}


def structured_weekly_schedule_for_today(payload: dict, today: date) -> list[str]:
    aliases = WEEKDAY_ALIASES[today.weekday()]
    rows: list[str] = []
    for block in payload.get('protected_blocks', []):
        slot = clean_md(str(block.get('slot', '')).strip())
        match = re.match(r'^(?P<label>[A-Za-z\u4e00-\u9fa5]+)\s+(?P<start>\d{2}:\d{2})-(?P<end>\d{2}:\d{2})$', slot)
        if not match:
            continue
        label = match.group('label')
        if label not in aliases:
            continue
        goal = clean_md(str(block.get('goal', '')).strip()) or '待补充'
        kind = clean_md(str(block.get('kind', '')).strip())
        if kind:
            rows.append(f"- {match.group('start')}-{match.group('end')} 周时间承诺 -> {goal}（{kind}）")
        else:
            rows.append(f"- {match.group('start')}-{match.group('end')} 周时间承诺 -> {goal}")
    return rows


def weekly_schedule_for_today(text: str, today: date) -> list[str]:
    lines = text.splitlines()
    weekday_label = WEEKDAY_TO_CN[today.weekday()]
    weekday_aliases = WEEKDAY_ALIASES[today.weekday()]
    in_day = False
    schedule: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('### '):
            in_day = weekday_label in stripped
            continue
        if in_day and stripped.startswith('### '):
            break
        if not in_day:
            continue
        if stripped.startswith('|') and not stripped.startswith('|---') and '时间段' not in stripped:
            parts = [p.strip() for p in stripped.strip('|').split('|')]
            if len(parts) >= 2:
                slot = clean_md(parts[0])
                task = clean_md(parts[1])
                if re.match(r'^\d{2}:\d{2}-\d{2}:\d{2}$', slot):
                    schedule.append(f'- {slot} {task}')
    if schedule:
        return schedule

    in_protected = False
    current_slot: tuple[str, str, str] | None = None
    current_match = False
    current_goal = ''

    def flush_current() -> None:
        nonlocal current_slot, current_match, current_goal
        if current_slot and current_match:
            start_label, end_label, label = current_slot
            task = current_goal or f'周计划保护时间块（{label}）'
            schedule.append(f'- {start_label}-{end_label} 周计划保护块 -> {task}')
        current_slot = None
        current_match = False
        current_goal = ''

    for line in lines:
        stripped = line.strip()
        if stripped == '## 保护时间块':
            in_protected = True
            continue
        if in_protected and stripped.startswith('## '):
            break
        if not in_protected:
            continue
        slot_match = re.match(r'^-\s*时间块\d+:\s*(?P<label>[A-Za-z\u4e00-\u9fa5]+)\s+(?P<start>\d{2}:\d{2})-(?P<end>\d{2}:\d{2})$', stripped)
        if slot_match:
            flush_current()
            label = slot_match.group('label')
            current_slot = (slot_match.group('start'), slot_match.group('end'), label)
            current_match = label == weekday_label or label in weekday_aliases
            continue
        if current_slot and current_match and stripped.startswith('- 关联目标:'):
            current_goal = clean_md(stripped.split(':', 1)[1].strip())
    flush_current()
    return schedule


def weekly_parse_warning(
    weekly_source: str,
    weekly_role: str,
    weekly_goals: list[str],
    weekly_hras_items: list[str],
    weekly_schedule: list[str],
) -> str:
    if weekly_source == 'weekly plan missing':
        return ''
    if weekly_role or weekly_goals or weekly_hras_items or weekly_schedule:
        return ''
    return '已找到本周计划文件，但当前没有解析出本周关键目标 / 高回报活动 / 时间块；今天的 A1/A2 更偏向月目标兜底，不是完整的周 -> 日承接。'


def main() -> None:
    today = date.today()
    yesterday = today - timedelta(days=1)
    today_rel = f'{today.isoformat()}.md'
    yesterday_rel = f'{yesterday.isoformat()}.md'
    today_path, today_source = resolve_memory_file(today_rel)
    yesterday_path, yesterday_source = resolve_memory_file(yesterday_rel)

    today_text = read_text(today_path)
    yesterday_text = read_text(yesterday_path)
    monthly_path, monthly_source = current_month_monthly_plan(today)
    monthly_text = read_text(monthly_path) if monthly_path else ''
    role_path, role_source = current_month_role_file(today)
    role_text = read_text(role_path) if role_path else ''
    weekly_path = latest_weekly_plan(PRIMARY_MEMORY_DIR)
    if weekly_path is None and FALLBACK_MEMORY_DIR is not None:
        weekly_path = latest_weekly_plan(FALLBACK_MEMORY_DIR)
    weekly_text = read_text(weekly_path) if weekly_path else ''
    weekly_source = (
        'workspace-azai/memory'
        if weekly_path and str(weekly_path).startswith(str(PRIMARY_MEMORY_DIR))
        else ('workspace-main/memory (fallback)' if weekly_path and FALLBACK_MEMORY_DIR is not None else 'weekly plan missing')
    )
    weekly_time_commitments, weekly_time_commitment_source = load_weekly_time_commitments(today)

    biggest_progress = extract_progress(yesterday_text)
    unfinished = extract_unfinished(yesterday_text)
    tomorrow_first_move = clean_md(extract_tomorrow_first_move(yesterday_text))

    monthly_goals = monthly_top_goals(monthly_text) or monthly_company_focus_goals(monthly_text)
    monthly_hras_items = monthly_hras(monthly_text)
    monthly_role_focus = normalize_role_name(role_focus_from_current_month(role_text))
    monthly_role_goals = role_key_goals(role_text, monthly_role_focus)
    weekly_goals = weekly_top_goals(weekly_text)
    weekly_hras_items = weekly_hras(weekly_text)
    weekly_role = weekly_role_focus(weekly_text)
    inbox_items, inbox_source, inbox_status = load_inbox_snapshot(limit=5)
    decided_for_today, decided_source = load_tomorrow_carry_items(today)
    if not meaningful(tomorrow_first_move) or is_operational_first_move(tomorrow_first_move):
        fallback_goal = first_meaningful(weekly_goals + monthly_goals + monthly_role_goals)
        tomorrow_first_move = unfinished[0] if unfinished else (fallback_goal or '待从昨天复盘补充')

    exploded_monthly_goals = explode_compound_items(monthly_goals)
    exploded_role_goals = explode_compound_items(monthly_role_goals)
    exploded_weekly_goals = explode_compound_items(weekly_goals)
    exploded_unfinished = explode_compound_items(unfinished)
    exploded_decided_for_today = explode_compound_items(decided_for_today)
    unfinished_display = canonicalize_display_items(exploded_unfinished, limit=5)
    inbox_display = inbox_redecision_texts(inbox_items, limit=3)

    weekly_schedule = structured_weekly_schedule_for_today(weekly_time_commitments, today) or weekly_schedule_for_today(weekly_text, today)
    weekly_warning = weekly_parse_warning(
        weekly_source,
        weekly_role,
        weekly_goals,
        weekly_hras_items,
        weekly_schedule,
    )
    today_file_schedule = today_schedule(today_text)
    calendar_events, calendar_source = query_calendar_events(today)
    schedule_signal_rows = (
        parse_calendar_rows(calendar_events)
        if calendar_read_succeeded(calendar_source) and calendar_events
        else parse_schedule_rows(today_file_schedule or weekly_schedule)
    )
    if schedule_signal_rows:
        a_items, _unused_b_items, c_items, d_items = choose_day_items(
            exploded_weekly_goals,
            exploded_monthly_goals,
            exploded_role_goals,
            exploded_unfinished,
            tomorrow_first_move,
            monthly_hras_items,
            weekly_hras_items,
            schedule_signal_rows,
            'calendar_event' if calendar_read_succeeded(calendar_source) and calendar_events else 'weekly_schedule',
        )
        b_items = build_urgent_items(a_items, exploded_unfinished, exploded_weekly_goals, c_items, d_items)
        if not c_items:
            c_items = build_followups(a_items, weekly_goals, weekly_hras_items)
    else:
        a_items, b_items, c_items, d_items = choose_lightweight_day_items(
            exploded_weekly_goals,
            exploded_monthly_goals,
            exploded_role_goals,
            exploded_unfinished,
            tomorrow_first_move,
            exploded_decided_for_today,
            inbox_items,
            calendar_events,
            calendar_source,
        )

    schedule_source = calendar_source
    if calendar_read_succeeded(calendar_source):
        schedule = schedule_from_calendar(calendar_events, a_items, c_items, d_items)
    else:
        if today_file_schedule:
            schedule = today_file_schedule
            schedule_source = today_source
        elif weekly_schedule:
            schedule = weekly_schedule
            schedule_source = (
                weekly_time_commitment_source
                if weekly_time_commitment_source != 'weekly time commitments missing'
                else weekly_source
            )
        else:
            schedule = fallback_schedule(a_items, c_items, d_items)
            schedule_source = 'synthetic fallback schedule'

    carry = []
    for item in exploded_decided_for_today[:3]:
        carry.append(f'- {item}: 昨晚 Inbox 已决策进今天，先安排到 A/B/C/D 与时间块。')
    for item in unfinished_display[:3]:
        carry.append(f'- {item}: 今日重新决策（继续 / 延后 / 授权 / 删除）')
    if not carry:
        carry = ['- 昨晚未回填未完成事项，建议开工前先确认哪些需要继续、延后、授权或删除。']
    for item in inbox_display[:2]:
        carry.append(f'- {item}: Inbox 重决策（进入今天 / 留在本周 / 仅记录）')

    if not a_items:
        fallback_a = dedupe_keep_order(
            exploded_decided_for_today
            + exploded_weekly_goals
            + ([tomorrow_first_move] if meaningful(tomorrow_first_move) else [])
            + exploded_monthly_goals
            + exploded_role_goals
            + exploded_unfinished
        )
        a_items = fallback_a[:3] if fallback_a else ['待你补充今天最重要的 1-2 个关键结果']

    schedule = ensure_closeout_block(schedule, a_items[0] if a_items else strip_priority_prefix(tomorrow_first_move))

    output = build_output(
        today,
        yesterday_source,
        biggest_progress,
        unfinished_display,
        exploded_decided_for_today,
        tomorrow_first_move,
        carry,
        weekly_goals,
        weekly_warning,
        inbox_display,
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
