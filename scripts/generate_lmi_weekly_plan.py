#!/usr/bin/env python3
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from pathlib import Path

PRIMARY_MEMORY_DIR = Path('/Users/woohuaca/.openclaw/workspace-azai/memory')
FALLBACK_MEMORY_DIR = Path('/Users/woohuaca/.openclaw/workspace-main/memory')


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


def latest_file(memory_dir: Path, pattern: str) -> Path | None:
    candidates = sorted(memory_dir.glob(pattern))
    return candidates[-1] if candidates else None


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


def current_month_monthly_plan(today: date) -> tuple[Path | None, str]:
    prefix = today.strftime('%Y-%m')
    patterns = [
        f'{prefix}_LMI_monthly_plan_complete.md',
        f'{prefix}_LMI_monthly_plan.md',
    ]
    primary = latest_matching(PRIMARY_MEMORY_DIR, patterns)
    if primary:
        return primary, 'workspace-azai/memory'
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
    fallback = latest_matching(FALLBACK_MEMORY_DIR, patterns)
    if fallback:
        return fallback, 'workspace-main/memory (fallback)'
    return None, 'role clarification missing'


def latest_weekly_review() -> tuple[Path | None, str]:
    primary = latest_file(PRIMARY_MEMORY_DIR, '周复盘-*.md')
    if primary:
        return primary, 'workspace-azai/memory'
    fallback = latest_file(FALLBACK_MEMORY_DIR, '周复盘-*.md')
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
        if capture_role and stripped.startswith('### 5月关键目标'):
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
        if s.startswith('### 下周改进行动') or s.startswith('## 🔄 下周改进行动') or s.startswith('## Next 1-3 Moves'):
            capture = True
            continue
        if capture and (s.startswith('###') or s.startswith('## ') and not s.startswith('## Next 1-3 Moves')):
            break
        if capture and s.startswith('|'):
            cols = [c.strip() for c in s.strip('|').split('|')]
            if len(cols) >= 4 and cols[0] != '序号':
                moves.append(clean_md(cols[2]))
        elif capture and re.match(r'-\s+(Continue|Start|Stop|Delegate|Delete|Move to next week):', s):
            moves.append(clean_md(s.split(':', 1)[1]))
        elif capture and re.match(r'\d+\.\s+', s):
            moves.append(clean_md(re.sub(r'^\d+\.\s+', '', s)))
    return dedupe_keep_order(moves)[:4]


def build_followups(goals: list[str]) -> tuple[str, str, str]:
    must = goals[0] if goals else '待补充本周必须亲自推进事项'
    delegate = '客户状态整理、纪要整理、文档标准化等可下沉事项'
    follow = '对本周关键客户与关键节点做固定检查，不把所有事项都亲自推进'
    return must, delegate, follow


def build_weekly_plan() -> tuple[str, Path, Path]:
    today = date.today()
    monday, friday = week_bounds(today)
    week_label = f'{monday.isoformat()} to {friday.isoformat()}'

    monthly_path, monthly_source = current_month_monthly_plan(today)
    role_path, role_source = current_month_role_file(today)
    latest_review_path, weekly_source = latest_weekly_review()

    monthly_text = read_text(monthly_path)
    role_text = read_text(role_path)
    weekly_text = read_text(latest_review_path)

    monthly_goals = monthly_top_goals(monthly_text)
    monthly_activities = monthly_hras(monthly_text)
    weighted_roles = role_weights(role_text)
    role_goal_map = all_role_goals(role_text)
    milestones = weekly_milestones_from_monthly(monthly_text, monday, friday)
    rhythm = weekly_rhythm(monthly_text)
    monthly_moves = monthly_next_moves(monthly_text)
    last_moves = extract_latest_weekly_moves(weekly_text)

    main_role = weighted_roles[0][0] if weighted_roles else '待补充本周主推进角色'
    lower_role = weighted_roles[-1][0] if weighted_roles else '待补充'
    role_boundary = weighted_roles[1][0] if len(weighted_roles) > 1 else main_role
    week_theme = monthly_goals[0] if monthly_goals else (milestones[0]['goal'] if milestones else '待补充本周主题')

    top_goals: list[dict] = []
    priority_labels = ['A1', 'A2', 'A3', 'B1', 'B2']
    primary_goal_pool = monthly_goals[:3]
    if not primary_goal_pool:
        for role_name, goals in role_goal_map:
            primary_goal_pool.extend(goals)
            if len(primary_goal_pool) >= 3:
                break
    for goal in primary_goal_pool[:3]:
        linked_milestone = milestone_for_goal(goal, milestones)
        top_goals.append(
            {
                'priority': priority_labels[len(top_goals)],
                'role': infer_role_for_goal(goal, weighted_roles),
                'goal': goal,
                'success': linked_milestone['success'] if linked_milestone else '形成本周可见推进或交付',
                'target': linked_milestone['target'] if linked_milestone else friday.isoformat(),
                'notes': 'monthly top goal',
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
    out.append('# LMI 周计划草案\n')
    out.append('## Weekly Snapshot\n')
    out.append(f'- Plan week: {week_label}')
    out.append(f'- Monthly source: {monthly_source}')
    out.append(f'- Role source: {role_source}')
    out.append(f'- Latest review source: {weekly_source}')
    out.append(f'- Week theme: {week_theme}')
    out.append(f'- Linked monthly priority: {"；".join(monthly_goals[:2]) if monthly_goals else "待补充"}')
    out.append(f'- Main linked role: {main_role}')
    out.append(f'- Weekly success definition: {success_def}')

    out.append('\n## Monthly Anchors\n')
    if weighted_roles:
        out.append(f'- Highest-weight role this month: {main_role}')
        out.append(f'- Lower-attention role this week can be: {lower_role}')
    if monthly_goals:
        out.append(f'- Monthly top goals to translate this week: {"；".join(monthly_goals[:3])}')
    if monthly_activities:
        out.append(f'- Monthly high-return activities to protect: {"；".join(monthly_activities[:3])}')

    out.append('\n## Weekly Top Goals\n')
    out.append('| Priority | Role | Weekly goal | Success definition | Target day | Notes |')
    out.append('| --- | --- | --- | --- | --- | --- |')
    if top_goals:
        for goal in top_goals:
            out.append(f"| {goal['priority']} | {goal['role']} | {goal['goal']} | {goal['success']} | {goal['target']} | {goal['notes']} |")
    else:
        out.append('| A1 | 待补充 | 待补充 | 待补充 | Fri | 需要先确认本周核心目标 |')

    out.append('\n## Role Focus\n')
    out.append(f'- Role to advance most this week: {main_role}')
    out.append(f'- Role that can accept lower attention this week: {lower_role}')
    out.append(f'- Role that needs clearer boundary or delegation: {role_boundary}')

    out.append('\n## High-Return Activities\n')
    if activity_pairs:
        for i, (activity, role_name, linked_goal) in enumerate(activity_pairs, start=1):
            out.append(f'- Activity {i}: {activity}')
            out.append(f'  - linked role: {role_name}')
            out.append(f'  - linked goal: {linked_goal}')
            out.append('  - why it matters: 这是本月已定义的高回报活动，本周需要转成受保护时间块')
    else:
        out.append('- Activity 1: 待补充本周高回报活动')
        out.append('  - linked role: 待补充')
        out.append('  - linked goal: 待补充')
        out.append('  - why it matters: 待补充')

    out.append('\n## Delegation And Follow-Up\n')
    out.append(f'- Must personally drive: {must_drive}')
    out.append(f'- Delegate: {delegate_item}')
    out.append(f'- Follow up only: {follow_up_item}')

    out.append('\n## Protected Time Blocks\n')
    for idx, block in enumerate(protected_defaults, start=1):
        linked_goal = selected_goal_texts[idx - 1] if len(selected_goal_texts) >= idx else (selected_goal_texts[-1] if selected_goal_texts else '待补充')
        out.append(f'- Block {idx}: {block}')
        out.append(f'  - linked goal: {linked_goal}')
    if rhythm:
        out.append(f'- Weekly rhythm reminder: {"；".join(rhythm)}')

    out.append('\n## Week-End Review Hooks\n')
    out.append(f'- What must be true by Friday: {success_def}')
    out.append('- Likely unfinished item to delete instead of roll over: 不再服务本周主角色与月目标的事项')
    out.append('- Weekly question to answer in review: 本周时间是否真正投在最高权重角色、关键结果和高回报活动上？')

    out.append('\n## Next Week GPS Preview Inputs\n')
    if preview_inputs:
        for item in preview_inputs[:3]:
            out.append(f'- {item}')
    else:
        out.append('- 待补充本周复盘中的关键承接项')

    out.append('\n## Next 1-3 Moves\n')
    out.append('- 先确认 A1 / A2 是否仍服务 5 月最高权重角色与本周里程碑')
    out.append('- 把高回报活动放进本周真实时间块，优先保护晨间深度块')
    out.append('- 周五复盘时直接回到 plan versus actual，并决定哪些事项继续 / 延后 / 授权 / 删除')

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
