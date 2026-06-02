#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path

PRIMARY_MEMORY_DIR = Path('/Users/woohuaca/.openclaw/workspace-azai/memory')


def env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


ALLOW_MAIN_MEMORY_FALLBACK = env_flag('LMI_ALLOW_MAIN_MEMORY_FALLBACK', False)
FALLBACK_MEMORY_DIR = (
    Path(os.environ.get('LMI_FALLBACK_MEMORY_DIR', '/Users/woohuaca/.openclaw/workspace-main/memory')).expanduser()
    if ALLOW_MAIN_MEMORY_FALLBACK
    else None
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


def latest_matching_by_mtime(memory_dir: Path, patterns: list[str]) -> Path | None:
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(path for path in memory_dir.glob(pattern) if path.is_file())
    if not candidates:
        return None
    candidates = sorted(set(candidates), key=lambda path: (path.stat().st_mtime, path.name))
    return candidates[-1]


def latest_file(memory_dir: Path, pattern: str) -> Path | None:
    candidates = sorted(memory_dir.glob(pattern))
    return candidates[-1] if candidates else None


def first_existing(memory_dir: Path, names: list[str]) -> Path | None:
    for name in names:
        path = memory_dir / name
        if path.exists():
            return path
    return None


def shift_week(anchor_date: date, offset_weeks: int) -> date:
    return anchor_date + timedelta(days=7 * offset_weeks)


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


def meaningful(text: str) -> bool:
    value = clean_md(text)
    if not value:
        return False
    bad = ('待补充', '待确认', 'missing', '待启动', '计划中')
    return not any(marker in value for marker in bad)


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


def describe_source(source: str, path: Path | None) -> str:
    if path and path.exists():
        return f'{source} / {path.name}'
    return source


def current_quarter(today: date) -> int:
    return ((today.month - 1) // 3) + 1


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


def latest_monthly_plan_fallback() -> tuple[Path | None, str]:
    latest_primary = latest_matching_by_mtime(PRIMARY_MEMORY_DIR, ['20??-??_LMI_monthly_plan_complete.md', '20??-??_LMI_monthly_plan.md'])
    if latest_primary:
        return latest_primary, 'workspace-azai/memory (latest monthly fallback)'
    if FALLBACK_MEMORY_DIR is not None:
        latest_fallback = latest_matching_by_mtime(FALLBACK_MEMORY_DIR, ['20??-??_LMI_monthly_plan_complete.md', '20??-??_LMI_monthly_plan.md'])
        if latest_fallback:
            return latest_fallback, 'workspace-main/memory (latest monthly fallback)'
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


def latest_role_file_fallback() -> tuple[Path | None, str]:
    latest_primary = latest_matching_by_mtime(PRIMARY_MEMORY_DIR, ['20??-??_role_clarification.md'])
    if latest_primary:
        return latest_primary, 'workspace-azai/memory (latest role fallback)'
    if FALLBACK_MEMORY_DIR is not None:
        latest_fallback = latest_matching_by_mtime(FALLBACK_MEMORY_DIR, ['20??-??_role_clarification.md'])
        if latest_fallback:
            return latest_fallback, 'workspace-main/memory (latest role fallback)'
    return None, 'role clarification missing'


def current_quarter_okr_file(today: date) -> tuple[Path | None, str]:
    quarter = current_quarter(today)
    names = [
        f'Q{quarter}-OKR-{today.year}.md',
    ]
    primary = first_existing(PRIMARY_MEMORY_DIR, names)
    if primary:
        return primary, 'workspace-azai/memory'
    if FALLBACK_MEMORY_DIR is not None:
        fallback = first_existing(FALLBACK_MEMORY_DIR, names)
        if fallback:
            return fallback, 'workspace-main/memory (fallback)'
    return None, 'quarter okr missing'


def current_quarter_role_file(today: date) -> tuple[Path | None, str]:
    quarter = current_quarter(today)
    names = [
        f'角色澄清表-Q{quarter}目标-{today.year}.md',
        f'Q{quarter}角色目标-{today.year}.md',
    ]
    primary = first_existing(PRIMARY_MEMORY_DIR, names)
    if primary:
        return primary, 'workspace-azai/memory'
    if FALLBACK_MEMORY_DIR is not None:
        fallback = first_existing(FALLBACK_MEMORY_DIR, names)
        if fallback:
            return fallback, 'workspace-main/memory (fallback)'
    return None, 'quarter role clarification missing'


def latest_weekly_review() -> tuple[Path | None, str]:
    primary = latest_matching_by_mtime(PRIMARY_MEMORY_DIR, ['周复盘-*.md', '*_weekly_review.md'])
    if primary:
        return primary, 'workspace-azai/memory'
    if FALLBACK_MEMORY_DIR is not None:
        fallback = latest_matching_by_mtime(FALLBACK_MEMORY_DIR, ['周复盘-*.md', '*_weekly_review.md'])
        if fallback:
            return fallback, 'workspace-main/memory (fallback)'
    return None, 'weekly review missing'


def monthly_top_goals(text: str) -> list[str]:
    items: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('🎯'):
            items.append(clean_md(stripped.lstrip('🎯').strip()))
    return dedupe_keep_order(items)[:5]


def objective_titles(text: str) -> list[str]:
    items: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('## Objective'):
            title = stripped.split('：', 1)[-1].strip()
            if meaningful(title):
                items.append(clean_md(title))
    return dedupe_keep_order(items)[:5]


def monthly_hras(text: str) -> list[str]:
    items: list[str] = []
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('## High-Return Activity Items') or stripped.startswith('## 六、High-Return Activity Items'):
            in_table = True
            continue
        if in_table and stripped.startswith('## '):
            break
        if in_table and stripped.startswith('|') and '高回报活动' not in stripped and not stripped.startswith('|---'):
            parts = [p.strip() for p in stripped.strip('|').split('|')]
            if parts and meaningful(parts[0]):
                items.append(clean_md(parts[0]))
    return dedupe_keep_order(items)[:6]


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
    items.sort(key=lambda item: (-item[1], item[0]))
    return items


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
        if capture_role and re.match(r'^###\s*\d{1,2}月关键目标$', stripped):
            capture_goals = True
            continue
        if capture_role and capture_goals and stripped.startswith('### '):
            break
        if capture_role and capture_goals:
            goal_match = re.match(r'\d+\.\s+\*\*(.+?)\*\*[:：]?\s*(.*)', stripped)
            if goal_match:
                title = clean_md(goal_match.group(1))
                rest = clean_md(goal_match.group(2))
                items.append(f'{title}：{rest}' if rest else title)
            elif re.match(r'\d+\.\s+', stripped):
                items.append(clean_md(re.sub(r'^\d+\.\s+', '', stripped)))
    return dedupe_keep_order(items)[:4]


def all_role_goals(text: str) -> list[tuple[str, list[str]]]:
    weighted = role_weights(text)
    out: list[tuple[str, list[str]]] = []
    for role_name, _weight in weighted:
        goals = role_key_goals(text, role_name)
        if goals:
            out.append((role_name, goals))
    return out


def split_rich_items(text: str) -> list[str]:
    raw = text.replace('<br />', '\n').replace('<br/>', '\n').replace('<br>', '\n')
    parts = [clean_md(part) for part in raw.splitlines()]
    if len([part for part in parts if part]) <= 1 and ('；' in raw or ';' in raw):
        parts = [clean_md(part) for part in re.split(r'[；;]+', raw)]
    out: list[str] = []
    for part in parts:
        value = re.sub(r'^\d+[\.\)、]\s*', '', part).strip()
        value = re.sub(r'^-\s*', '', value).strip()
        if meaningful(value):
            out.append(value)
    return dedupe_keep_order(out)


def parse_quarter_role_sections(text: str) -> list[dict[str, object]]:
    roles: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for line in text.splitlines():
        stripped = line.strip()
        role_match = re.match(r'##\s+角色\d+[：:](.+?)（(\d+%)）', stripped)
        if role_match:
            if current:
                roles.append(current)
            current = {
                'title': normalize_role_name(role_match.group(1)),
                'weight': int(role_match.group(2).rstrip('%')),
                'key_results': [],
                'high_return': [],
                'month_focuses': {},
                'mechanism': [],
            }
            continue
        if not current or not stripped.startswith('|') or stripped.startswith('|------'):
            continue
        parts = [p.strip() for p in stripped.strip('|').split('|')]
        if len(parts) < 2:
            continue
        label = clean_md(parts[0]).replace('**', '')
        value = clean_md(parts[1])
        if label == '主要职责':
            current['responsibility'] = value
        elif label == 'Q2关键业绩':
            current['key_results'] = split_rich_items(parts[1])
        elif label == '主要高回报活动':
            current['high_return'] = split_rich_items(parts[1])
        elif label == '管理机制':
            current['mechanism'] = split_rich_items(parts[1])
        elif label == '时间投入':
            current['time'] = value
        elif re.match(r'^\d{1,2}月重点$', label):
            month_focuses = current.setdefault('month_focuses', {})
            if isinstance(month_focuses, dict):
                month_focuses[label] = value
    if current:
        roles.append(current)
    return roles


def quarter_role_weights(text: str) -> list[tuple[str, int]]:
    roles = parse_quarter_role_sections(text)
    items = [(str(role.get('title', '')), int(role.get('weight', 0))) for role in roles if role.get('title')]
    items.sort(key=lambda item: (-item[1], item[0]))
    return items


def quarter_month_focus_goals(text: str, today: date) -> list[str]:
    month_key = f'{today.month}月重点'
    ordered_roles = sorted(parse_quarter_role_sections(text), key=lambda role: (-int(role.get('weight', 0)), str(role.get('title', ''))))
    items: list[str] = []
    for role in ordered_roles:
        month_focuses = role.get('month_focuses', {})
        if isinstance(month_focuses, dict):
            goal = clean_md(str(month_focuses.get(month_key, '')))
            if meaningful(goal):
                items.append(goal)
    return dedupe_keep_order(items)


def quarter_month_activities(text: str) -> list[str]:
    ordered_roles = sorted(parse_quarter_role_sections(text), key=lambda role: (-int(role.get('weight', 0)), str(role.get('title', ''))))
    items: list[str] = []
    for role in ordered_roles:
        activities = role.get('high_return', [])
        if isinstance(activities, list):
            items.extend(str(item) for item in activities if meaningful(str(item)))
    return dedupe_keep_order(items)


def quarter_role_goal_map(text: str, today: date) -> list[tuple[str, list[str]]]:
    month_key = f'{today.month}月重点'
    out: list[tuple[str, list[str]]] = []
    ordered_roles = sorted(parse_quarter_role_sections(text), key=lambda role: (-int(role.get('weight', 0)), str(role.get('title', ''))))
    for role in ordered_roles:
        goals: list[str] = []
        month_focuses = role.get('month_focuses', {})
        if isinstance(month_focuses, dict):
            focus = clean_md(str(month_focuses.get(month_key, '')))
            if meaningful(focus):
                goals.append(focus)
        key_results = role.get('key_results', [])
        if isinstance(key_results, list):
            goals.extend(str(item) for item in key_results if meaningful(str(item)))
        goals = dedupe_keep_order(goals)[:4]
        if goals:
            out.append((str(role.get('title', '')), goals))
    return out


def quarter_activity_pairs(text: str) -> list[tuple[str, str]]:
    ordered_roles = sorted(parse_quarter_role_sections(text), key=lambda role: (-int(role.get('weight', 0)), str(role.get('title', ''))))
    pairs: list[tuple[str, str]] = []
    for role in ordered_roles:
        role_name = str(role.get('title', ''))
        activities = role.get('high_return', [])
        if isinstance(activities, list):
            for item in activities:
                value = str(item)
                if meaningful(value):
                    pairs.append((value, role_name))
    deduped: list[tuple[str, str]] = []
    seen: set[str] = set()
    for activity, role_name in pairs:
        key = clean_md(activity).lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append((activity, role_name))
    return deduped


def quarter_weekly_milestones(role_text: str, today: date, friday: date) -> list[dict]:
    month_label = f'**{today.month}月**'
    capture = False
    milestones: list[dict] = []
    for line in role_text.splitlines():
        stripped = line.strip()
        if stripped.startswith('## Q2关键里程碑汇总'):
            capture = True
            continue
        if capture and stripped.startswith('## '):
            break
        if capture and stripped.startswith('|') and '里程碑' not in stripped and not stripped.startswith('|------'):
            parts = [p.strip() for p in stripped.strip('|').split('|')]
            if len(parts) < 2:
                continue
            when = parts[0]
            milestone_text = parts[1]
            if when != month_label:
                continue
            role_text_value = parts[2] if len(parts) >= 3 else ''
            for item in split_rich_items(milestone_text):
                milestones.append(
                    {
                        'role': clean_md(role_text_value) or '本周主角色',
                        'goal': item,
                        'success': item,
                        'target': friday.isoformat(),
                        'source': 'quarter milestone',
                    }
                )
    seen: set[str] = set()
    out: list[dict] = []
    for item in milestones:
        key = clean_md(item['goal']).lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out[:6]


def quarter_adjustments(text: str) -> list[str]:
    capture = False
    items: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('## Q2调整要点'):
            capture = True
            continue
        if capture and stripped.startswith('## '):
            break
        if capture and stripped.startswith('| **'):
            cols = [p.strip() for p in stripped.strip('|').split('|')]
            if len(cols) >= 2:
                items.append(f"{clean_md(cols[0]).replace('**', '')}：{clean_md(cols[1])}")
    return dedupe_keep_order(items)[:4]


def parse_target_date(text: str) -> date | None:
    match = re.search(r'(20\d{2}-\d{2}-\d{2})', text)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), '%Y-%m-%d').date()
    except ValueError:
        return None


def weekly_milestones_from_monthly(text: str, monday: date, friday: date) -> list[dict]:
    milestones: list[dict] = []
    current_role = ''
    for line in text.splitlines():
        stripped = line.strip()
        role_match = re.match(r'###\s+角色\d+:\s*(.+?)（', stripped)
        if role_match:
            current_role = normalize_role_name(role_match.group(1))
            continue
        if stripped.startswith('|') and not stripped.startswith('|---') and '里程碑' not in stripped:
            parts = [p.strip() for p in stripped.strip('|').split('|')]
            if len(parts) >= 3:
                title = clean_md(parts[0])
                target_text = clean_md(parts[1])
                output = clean_md(parts[2])
                target = parse_target_date(target_text)
                if title and target and monday <= target <= friday:
                    milestones.append(
                        {
                            'role': current_role or '本周主角色',
                            'goal': title,
                            'success': output or '形成明确产出',
                            'target': target_text,
                            'source': 'monthly milestone',
                        }
                    )
    urgent_section = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('## Urgent Items Plan') or stripped.startswith('## 七、紧急事项计划'):
            urgent_section = True
            continue
        if urgent_section and stripped.startswith('## '):
            break
        if urgent_section and stripped.startswith('|') and '事项' not in stripped and not stripped.startswith('|---'):
            parts = [p.strip() for p in stripped.strip('|').split('|')]
            if len(parts) >= 3:
                goal = clean_md(parts[0])
                target_text = clean_md(parts[1])
                status = clean_md(parts[-1])
                target = parse_target_date(target_text)
                if goal and target and monday <= target <= friday:
                    milestones.append(
                        {
                            'role': '本周截止事项',
                            'goal': goal,
                            'success': status or '按期处理',
                            'target': target_text,
                            'source': 'monthly urgent',
                        }
                    )
    seen: set[str] = set()
    out: list[dict] = []
    for item in milestones:
        key = item['goal'].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out[:6]


def infer_role_for_goal(goal: str, weighted_roles: list[tuple[str, int]]) -> str:
    clean = clean_md(goal)
    rules = [
        (['客户', '漏斗', '装备制造', '轨道交通', '市场'], '新机会发现者'),
        (['charter', 'skill', 'pic'], 'CDT项目管理者'),
        (['prd', '需求', '原型', '设计'], '产品概念定义'),
        (['验证', 'poc', '价值'], '概念价值验证'),
    ]
    low = clean.lower()
    for keywords, role in rules:
        if any(keyword in clean or keyword in low for keyword in keywords):
            return role
    return weighted_roles[0][0] if weighted_roles else '本周主角色'


def milestone_for_goal(goal: str, milestones: list[dict]) -> dict | None:
    goal_tokens = set(re.findall(r'[\u4e00-\u9fffA-Za-z0-9→]+', clean_md(goal).lower()))
    best: dict | None = None
    best_score = 0
    for item in milestones:
        item_tokens = set(re.findall(r'[\u4e00-\u9fffA-Za-z0-9→]+', clean_md(item['goal']).lower()))
        score = len(goal_tokens & item_tokens)
        if score > best_score:
            best_score = score
            best = item
    return best if best_score > 0 else None


def weekly_rhythm(text: str) -> list[str]:
    rows: list[str] = []
    capture = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('### 每周节奏'):
            capture = True
            continue
        if capture and stripped.startswith('### '):
            break
        if capture and stripped.startswith('- '):
            rows.append(clean_md(stripped[2:]))
    return rows[:3]


def monthly_next_moves(text: str) -> list[str]:
    rows: list[str] = []
    capture = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('## Next 1-3 Moves'):
            capture = True
            continue
        if capture and stripped.startswith('## '):
            break
        if capture and re.match(r'\d+\.\s+', stripped):
            rows.append(clean_md(re.sub(r'^\d+\.\s+', '', stripped)))
    return rows[:3]


def extract_latest_weekly_moves(text: str) -> list[str]:
    moves: list[str] = []
    capture = False
    for line in text.splitlines():
        s = line.strip()
        if (
            s.startswith('### 下周改进行动')
            or s.startswith('## 🔄 下周改进行动')
            or s.startswith('## 延续与调整决策')
            or s.startswith('## Carry Forward Decisions')
            or s.startswith('## Next 1-3 Moves')
        ):
            capture = True
            continue
        if capture and (s.startswith('###') or s.startswith('## ') and not s.startswith('## Next 1-3 Moves')):
            break
        if capture and s.startswith('|'):
            cols = [c.strip() for c in s.strip('|').split('|')]
            if len(cols) >= 4 and cols[0] != '序号':
                moves.append(clean_md(cols[2]))
        elif capture and re.match(r'-\s+(Continue|Start or adjust|Stop|Delegate|Delete instead of rolling over|Move to next week|继续|启动或调整|停止|授权/委托|不滚动直接删除|转入下周):', s):
            moves.append(clean_md(s.split(':', 1)[1]))
        elif capture and re.match(r'\d+\.\s+', s):
            moves.append(clean_md(re.sub(r'^\d+\.\s+', '', s)))
    return dedupe_keep_order(moves)[:4]


def build_followups(goals: list[str]) -> tuple[str, str, str]:
    must = goals[0] if goals else '待补充本周必须亲自推进事项'
    delegate = '客户状态整理、纪要整理、文档标准化等可下沉事项'
    follow = '对本周关键客户与关键节点做固定检查，不把所有事项都亲自推进'
    return must, delegate, follow


def build_weekly_plan(
    anchor_date: date | None = None,
    target_week_offset: int = 0,
    title: str = 'LMI 周计划草案',
    weekly_review_text_override: str | None = None,
    weekly_review_source_override: str | None = None,
) -> tuple[str, Path, Path]:
    base_date = anchor_date or date.today()
    target_date = shift_week(base_date, target_week_offset)
    monday, friday = week_bounds(target_date)
    week_label = f'{monday.isoformat()} to {friday.isoformat()}'

    monthly_path, monthly_source = current_month_monthly_plan(target_date)
    role_path, role_source = current_month_role_file(target_date)
    quarter_okr_path, quarter_okr_source = current_quarter_okr_file(target_date)
    quarter_role_path, quarter_role_source = current_quarter_role_file(target_date)
    latest_review_path, weekly_source = latest_weekly_review()

    monthly_text = read_text(monthly_path)
    role_text = read_text(role_path)
    quarter_okr_text = read_text(quarter_okr_path)
    quarter_role_text = read_text(quarter_role_path)
    weekly_text = weekly_review_text_override if weekly_review_text_override is not None else read_text(latest_review_path)
    if weekly_review_source_override is not None:
        weekly_source = weekly_review_source_override

    using_quarter_goal_fallback = False
    using_quarter_role_fallback = False

    if monthly_text:
        monthly_goals = monthly_top_goals(monthly_text)
        monthly_activities = monthly_hras(monthly_text)
        milestones = weekly_milestones_from_monthly(monthly_text, monday, friday)
        rhythm = weekly_rhythm(monthly_text)
        monthly_moves = monthly_next_moves(monthly_text)
    elif quarter_okr_text or quarter_role_text:
        using_quarter_goal_fallback = True
        monthly_goals = quarter_month_focus_goals(quarter_role_text, target_date)
        if not monthly_goals:
            monthly_goals = objective_titles(quarter_okr_text)
        monthly_activities = quarter_month_activities(quarter_role_text)
        milestones = quarter_weekly_milestones(quarter_role_text, target_date, friday)
        rhythm = []
        monthly_moves = quarter_adjustments(quarter_role_text)
        monthly_source = f'{quarter_okr_source} (quarter fallback)' if quarter_okr_text else f'{quarter_role_source} (quarter role fallback)'
    else:
        monthly_fallback_path, monthly_fallback_source = latest_monthly_plan_fallback()
        monthly_text = read_text(monthly_fallback_path)
        monthly_goals = monthly_top_goals(monthly_text)
        monthly_activities = monthly_hras(monthly_text)
        milestones = weekly_milestones_from_monthly(monthly_text, monday, friday)
        rhythm = weekly_rhythm(monthly_text)
        monthly_moves = monthly_next_moves(monthly_text)
        monthly_source = monthly_fallback_source

    if role_text:
        weighted_roles = role_weights(role_text)
        role_goal_map = all_role_goals(role_text)
    elif quarter_role_text:
        using_quarter_role_fallback = True
        weighted_roles = quarter_role_weights(quarter_role_text)
        role_goal_map = quarter_role_goal_map(quarter_role_text, target_date)
        role_source = f'{quarter_role_source} (quarter fallback)'
    else:
        role_fallback_path, role_fallback_source = latest_role_file_fallback()
        role_text = read_text(role_fallback_path)
        weighted_roles = role_weights(role_text)
        role_goal_map = all_role_goals(role_text)
        role_source = role_fallback_source

    last_moves = extract_latest_weekly_moves(weekly_text)

    main_role = weighted_roles[0][0] if weighted_roles else '待补充本周主推进角色'
    lower_role = weighted_roles[-1][0] if weighted_roles else '待补充'
    role_boundary = weighted_roles[1][0] if len(weighted_roles) > 1 else main_role
    week_theme = monthly_goals[0] if monthly_goals else (milestones[0]['goal'] if milestones else '待补充本周主题')

    top_goals: list[dict] = []
    priority_labels = ['A1', 'A2', 'A3', 'B1', 'B2']
    primary_goal_records: list[dict[str, str]] = []
    if using_quarter_role_fallback and role_goal_map:
        for role_name, goals in role_goal_map:
            if not goals:
                continue
            primary_goal_records.append({'goal': goals[0], 'role': role_name})
            if len(primary_goal_records) >= 3:
                break
    else:
        for goal in monthly_goals[:3]:
            primary_goal_records.append({'goal': goal, 'role': ''})
    if not primary_goal_records:
        for role_name, goals in role_goal_map:
            for goal in goals:
                primary_goal_records.append({'goal': goal, 'role': role_name})
                if len(primary_goal_records) >= 3:
                    break
            if len(primary_goal_records) >= 3:
                break
    for goal_record in primary_goal_records[:3]:
        goal = goal_record['goal']
        linked_milestone = milestone_for_goal(goal, milestones)
        note = 'quarter-derived month goal' if using_quarter_goal_fallback else 'monthly top goal'
        top_goals.append(
            {
                'priority': priority_labels[len(top_goals)],
                'role': goal_record['role'] or infer_role_for_goal(goal, weighted_roles),
                'goal': goal,
                'success': linked_milestone['success'] if linked_milestone else '形成本周可见推进或交付',
                'target': linked_milestone['target'] if linked_milestone else friday.isoformat(),
                'notes': note,
            }
        )

    for item in milestones:
        if len(top_goals) >= 5:
            break
        if any(clean_md(item['goal']) == clean_md(existing['goal']) for existing in top_goals):
            continue
        top_goals.append(
            {
                'priority': priority_labels[len(top_goals)],
                'role': infer_role_for_goal(item['goal'], weighted_roles),
                'goal': item['goal'],
                'success': item['success'],
                'target': item['target'],
                'notes': item['source'],
            }
        )

    if not top_goals:
        top_goals.append(
            {
                'priority': 'A1',
                'role': main_role,
                'goal': '待补充本周最重要结果',
                'success': '待补充',
                'target': friday.isoformat(),
                'notes': 'need confirmation',
            }
        )

    success_def = '；'.join([item['goal'] for item in top_goals[:2]])

    selected_goal_texts = [goal['goal'] for goal in top_goals]
    must_drive, delegate_item, follow_up_item = build_followups(selected_goal_texts)
    activity_pairs: list[tuple[str, str, str]] = []
    if using_quarter_role_fallback and quarter_role_text:
        quarter_pairs = quarter_activity_pairs(quarter_role_text)
        for idx, (activity, role_name) in enumerate(quarter_pairs[:4]):
            linked_goal = selected_goal_texts[min(idx, len(selected_goal_texts) - 1)] if selected_goal_texts else '待补充'
            activity_pairs.append((activity, role_name or main_role, linked_goal))
    else:
        for idx, activity in enumerate(monthly_activities[:4]):
            linked_goal = selected_goal_texts[min(idx, len(selected_goal_texts) - 1)] if selected_goal_texts else '待补充'
            linked_role = top_goals[min(idx, len(top_goals) - 1)]['role'] if top_goals else main_role
            activity_pairs.append((activity, linked_role, linked_goal))

    preview_inputs = last_moves or monthly_moves
    protected_defaults = [
        'Mon 09:30-12:00',
        'Tue 14:00-17:00',
        'Thu 09:30-12:00',
    ]

    out: list[str] = []
    out.append(f'# {title}\n')
    out.append('## 周计划概览\n')
    out.append(f'- 计划周期: {week_label}')
    if using_quarter_goal_fallback:
        out.append('- 月度承接逻辑: 从季度目标承接到本周')
        out.append(f'- 季度目标来源: {describe_source(quarter_okr_source, quarter_okr_path)}')
    out.append(f'- 月计划来源: {describe_source(monthly_source, monthly_path)}')
    if using_quarter_role_fallback:
        out.append('- 角色承接逻辑: 从季度角色澄清承接到本周')
        out.append(f'- 季度角色澄清来源: {describe_source(quarter_role_source, quarter_role_path)}')
    out.append(f'- 角色澄清来源: {describe_source(role_source, role_path)}')
    out.append(f'- 上周复盘来源: {describe_source(weekly_source, latest_review_path)}')
    out.append(f'- 本周主题: {week_theme}')
    out.append(f'- 关联月目标: {"；".join(monthly_goals[:2]) if monthly_goals else "待补充"}')
    out.append(f'- 本周主推进角色: {main_role}')
    out.append(f'- 本周成功定义: {success_def}')

    out.append('\n## 月度锚点\n')
    if weighted_roles:
        out.append(f'- 本月最高权重角色: {main_role}')
        out.append(f'- 本周可降低关注的角色: {lower_role}')
    if monthly_goals:
        out.append(f'- 需要拆解到本周的月重点目标: {"；".join(monthly_goals[:3])}')
    if monthly_activities:
        out.append(f'- 本月需要继续保护的高回报活动: {"；".join(monthly_activities[:3])}')

    out.append('\n## 本周关键目标\n')
    out.append('| 优先级 | 角色 | 本周目标 | 成功定义 | 截止日 | 备注 |')
    out.append('| --- | --- | --- | --- | --- | --- |')
    if top_goals:
        for goal in top_goals:
            out.append(f"| {goal['priority']} | {goal['role']} | {goal['goal']} | {goal['success']} | {goal['target']} | {goal['notes']} |")
    else:
        out.append('| A1 | 待补充 | 待补充 | 待补充 | Fri | 需要先确认本周核心目标 |')

    out.append('\n## 角色聚焦\n')
    out.append(f'- 本周主推进角色: {main_role}')
    out.append(f'- 本周可降低关注的角色: {lower_role}')
    out.append(f'- 需要更清晰边界或授权的角色: {role_boundary}')

    out.append('\n## 高回报活动\n')
    if activity_pairs:
        for i, (activity, role_name, linked_goal) in enumerate(activity_pairs, start=1):
            out.append(f'- 活动{i}: {activity}')
            out.append(f'  - 关联角色: {role_name}')
            out.append(f'  - 关联目标: {linked_goal}')
            out.append('  - 为什么重要: 这是本月已定义的高回报活动，本周需要转成受保护时间块')
    else:
        out.append('- 活动1: 待补充本周高回报活动')
        out.append('  - 关联角色: 待补充')
        out.append('  - 关联目标: 待补充')
        out.append('  - 为什么重要: 待补充')

    out.append('\n## 授权与跟进\n')
    out.append(f'- 必须亲自推进: {must_drive}')
    out.append(f'- 可以授权: {delegate_item}')
    out.append(f'- 重点跟进即可: {follow_up_item}')

    out.append('\n## 保护时间块\n')
    for idx, block in enumerate(protected_defaults, start=1):
        linked_goal = selected_goal_texts[idx - 1] if len(selected_goal_texts) >= idx else (selected_goal_texts[-1] if selected_goal_texts else '待补充')
        out.append(f'- 时间块{idx}: {block}')
        out.append(f'  - 关联目标: {linked_goal}')
    if rhythm:
        out.append(f'- 每周节奏提醒: {"；".join(rhythm)}')

    out.append('\n## 周末复盘钩子\n')
    out.append(f'- 到周五必须成立的结果: {success_def}')
    out.append('- 更可能直接删除而不是滚动的事项: 不再服务本周主角色与月目标的事项')
    out.append('- 周复盘必须回答的问题: 本周时间是否真正投在最高权重角色、关键结果和高回报活动上？')

    out.append('\n## 下周 GPS 预览输入\n')
    if preview_inputs:
        for item in preview_inputs[:3]:
            out.append(f'- {item}')
    else:
        out.append('- 待补充本周复盘中的关键承接项')

    out.append('\n## Next 1-3 Moves（接下来 1-3 步）\n')
    out.append('- 先确认 A1 / A2 是否仍服务本月最高权重角色与本周里程碑')
    out.append('- 把高回报活动放进本周真实时间块，优先保护晨间深度块')
    out.append('- 周五复盘时直接回到计划与实际对照，并决定哪些事项继续 / 延后 / 授权 / 删除')

    content = '\n'.join(out) + '\n'
    canonical_path = PRIMARY_MEMORY_DIR / f'周计划-{monday.isoformat()}-{friday.strftime("%d")}.md'
    compatibility_path = PRIMARY_MEMORY_DIR / f'{monday.isoformat()}_weekly_plan.md'
    return content, canonical_path, compatibility_path


def main() -> None:
    content, canonical_path, compatibility_path = build_weekly_plan()
    canonical_path.write_text(content, encoding='utf-8')
    compatibility_path.write_text(content, encoding='utf-8')
    print(content, end='')


if __name__ == '__main__':
    main()
