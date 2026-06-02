#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import date, datetime, time, timedelta
from pathlib import Path

from lmi_execution_support import load_inbox_snapshot, load_tomorrow_carry_items


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
PLACEHOLDER_MARKERS = ('待补充', '待从', 'missing', '待确认', '待今晚', '待在今天')
GUIDANCE_MARKERS = ('当前无明确', '当前无固定', '建议开工前', '建议先补', '建议先快速补')
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
            if line.startswith('  - '):
                item = line[4:].strip()
                if meaningful(item) and item not in items:
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
        task = clean_md(rest.split('->', 1)[-1].strip())
        rows.append({
            'start': start,
            'end': end,
            'minutes': end - start,
            'task': task,
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


def calendar_read_succeeded(calendar_source: str) -> bool:
    return calendar_source in {'feishu calendar via azai', 'feishu calendar via azai (no events today)'}


def is_meeting_like(text: str) -> bool:
    clean = strip_priority_prefix(clean_md(text))
    return any(word in clean for word in ['会议', '沟通', '对齐', '协调', '讨论', '评审', '交流'])


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


def schedule_suggestions_without_calendar(rows: list[str]) -> list[str]:
    if not rows:
        return ['- 当前未接入自动飞书日历；请先确认今天固定会议后，再排 A1 / A2 的时间块。']
    suggestions = ['- 当前未接入自动飞书日历；以下仅为建议时间块，需先按真实日历校正。']
    for row in rows[:5]:
        if '->' in row:
            left, right = row.split('->', 1)
            suggestions.append(f'{left}-> 建议：{right.strip()}')
        else:
            suggestions.append(f'{row}（建议）')
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
    a_display = [strip_priority_prefix(item) for item in a_items]
    b_display = [strip_priority_prefix(item) for item in b_items]
    c_display = [strip_priority_prefix(item) for item in c_items]
    d_display = [strip_priority_prefix(item) for item in d_items]
    yesterday_progress_display = biggest_progress if meaningful(biggest_progress) else '昨晚未回填昨日进展，建议开工前先快速补一句昨天最重要推进。'
    tomorrow_first_move_display = strip_priority_prefix(tomorrow_first_move) if meaningful(tomorrow_first_move) else '昨晚未回填 Tomorrow First Move，建议先确认今天的第一步。'
    show_d_placeholder = bool(d_display) and all('待补充' in item for item in d_display)
    carry_display = carry[:2]
    warning_lines: list[str] = []
    if weekly_warning:
        warning_lines.append(weekly_warning)
    if not calendar_read_succeeded(calendar_source):
        warning_lines.append('当前未接入自动飞书日历，今日日程不是最终版，需要先按真实会议校正。')
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
    out.append(f"- {a_display[0] if a_display else strip_priority_prefix(tomorrow_first_move)}")
    if weekly_goals:
        out.append(f'- 承接本周关键结果：{strip_priority_prefix(weekly_goals[0])}')

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
    if c_display:
        for i, item in enumerate(c_display, start=1):
            out.append(f'- C{i}: {item}')
    else:
        out.append('- 当前无必须单列的联络/追踪事项。')

    out.append('\n## D：会议/讨论/协调事项\n')
    if show_d_placeholder:
        if calendar_read_succeeded(calendar_source) and parse_schedule_rows(schedule):
            out.append('- 今天没有需要单列的会议决策项；固定会议见今日日程。')
        else:
            out.append('- 当前没有明确的会议/讨论/协调事项。')
    else:
        for i, item in enumerate(d_display, start=1):
            out.append(f'- D{i}: {item}')

    out.append('\n## 今日日程\n')
    out.extend(schedule)

    out.append('\n## 收工前\n')
    out.append('- 回填 1 条完成事项 + 1 句最大推进。')
    out.append('- 重新决策未完成事项，并写明天第一步。')

    out.append('\n## 接下来 1-3 步\n')
    out.append(f"- 先按今日主结果开工：{a_display[0] if a_display else strip_priority_prefix(tomorrow_first_move)}")
    if not calendar_read_succeeded(calendar_source):
        out.append('- 先校正今天固定会议，再最终确认时间块。')
    elif inbox_items:
        out.append('- 先把 Inbox 做进明天 / 留本周 / 转项目事实 / 仅记录的判断，不自动塞进 A/B/C/D。')
    elif decided_for_today:
        out.append('- 先把昨晚已承接的 Inbox 项编进今天的 A/B/C/D 和时间块。')
    else:
        out.append('- 把今日新增事项先收进 Inbox，再决定是否进入今天。')
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

    weekly_schedule = weekly_schedule_for_today(weekly_text, today)
    weekly_warning = weekly_parse_warning(
        weekly_source,
        weekly_role,
        weekly_goals,
        weekly_hras_items,
        weekly_schedule,
    )
    today_file_schedule = today_schedule(today_text)
    calendar_events: list[dict] = []
    calendar_source = 'calendar integration disabled'
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
        fallback_rows = today_file_schedule or weekly_schedule
        schedule = schedule_suggestions_without_calendar(fallback_rows)
        schedule_source = today_source if today_file_schedule else weekly_source

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
