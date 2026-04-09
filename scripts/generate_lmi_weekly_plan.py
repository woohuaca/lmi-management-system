#!/usr/bin/env python3
from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

PRIMARY_MEMORY_DIR = Path('/Users/woohuaca/.openclaw/workspace-azai/memory')
FALLBACK_MEMORY_DIR = Path('/Users/woohuaca/.openclaw/workspace-main/memory')


def week_bounds(today: date) -> tuple[date, date]:
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)
    return monday, friday


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


def q2_role_focus(text: str) -> list[tuple[str, str]]:
    focus: list[tuple[str, str]] = []
    current_role = ''
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r'##+ 角色\d+：(.+?)（', line)
        if m:
            current_role = m.group(1)
            continue
        if current_role and line.startswith('| **4月重点** |'):
            parts = [p.strip() for p in line.strip('|').split('|')]
            if len(parts) >= 2:
                focus.append((current_role, parts[1]))
                current_role = ''
    return focus


def q2_milestones(text: str) -> list[str]:
    items: list[str] = []
    for line in text.splitlines():
        if line.startswith('| **4月** |'):
            parts = [p.strip() for p in line.strip('|').split('|')]
            if len(parts) >= 2:
                chunks = [c.strip('- ').strip() for c in parts[1].split('<br>')]
                items.extend([c for c in chunks if c])
    return items[:3]


def role_activities(text: str) -> list[tuple[str, str]]:
    activities: list[tuple[str, str]] = []
    current_role = ''
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r'##+ 角色\d+：(.+?)（', s)
        if m:
            current_role = m.group(1)
            continue
        if current_role and s.startswith('| **主要高回报活动** |'):
            parts = [p.strip() for p in s.strip('|').split('|')]
            if len(parts) >= 2:
                for chunk in parts[1].split('<br>'):
                    item = re.sub(r'^\d+\.\s*', '', chunk).strip()
                    if item:
                        activities.append((current_role, item))
                current_role = ''
    return activities


def extract_latest_weekly_moves(text: str) -> list[str]:
    moves: list[str] = []
    capture = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('### 下周改进行动') or s.startswith('## 🔄 下周改进行动'):
            capture = True
            continue
        if capture and s.startswith('###') or s.startswith('## 📝') or s.startswith('## 📊'):
            break
        if capture and s.startswith('|'):
            cols = [c.strip() for c in s.strip('|').split('|')]
            if len(cols) >= 4 and cols[0] != '序号':
                moves.append(cols[2])
    return moves[:3]


def extract_gps(text: str) -> tuple[str, list[str]]:
    goal = ''
    priorities: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('**Goal:**'):
            goal = s.replace('**Goal:**', '').strip()
        if s.startswith('- A1:') or s.startswith('- A2:') or s.startswith('- B:'):
            priorities.append(s[2:].strip())
    return goal, priorities[:3]


def main() -> None:
    today = date.today()
    monday, friday = week_bounds(today)
    week_label = f'{monday.isoformat()} to {friday.isoformat()}'

    q2_path, q2_source = resolve_memory_file('Q2角色目标-2026.md')
    role_path, role_source = resolve_memory_file('角色澄清表-Q2目标-2026.md')
    latest_weekly_path, weekly_source = resolve_memory_file('周复盘-2026-03-24-28.md')

    q2_text = read_text(q2_path)
    role_text = read_text(role_path)
    weekly_text = read_text(latest_weekly_path)

    role_focus = q2_role_focus(role_text)
    milestones = q2_milestones(q2_text)
    last_moves = extract_latest_weekly_moves(weekly_text)
    gps_goal, gps_priorities = extract_gps(weekly_text)

    main_role = role_focus[0][0] if role_focus else '待补充本周主推进角色'
    week_theme = milestones[0] if milestones else '待补充本周主题'
    success_def = gps_goal or week_theme

    top_goals = []
    for idx, (role, focus) in enumerate(role_focus[:3], start=1):
        top_goals.append((f'A{idx}', role, focus))
    if milestones:
        for m in milestones:
            if len(top_goals) >= 5:
                break
            if m not in [g[2] for g in top_goals]:
                label = 'B' if len(top_goals) == 3 else 'C'
                top_goals.append((label, main_role, m))

    print('# LMI 周计划草案\n')
    print('## Weekly Snapshot\n')
    print(f'- Plan week: {week_label}')
    print(f'- Q2 source: {q2_source}')
    print(f'- Role source: {role_source}')
    print(f'- Latest review source: {weekly_source}')
    print(f'- Week theme: {week_theme}')
    print('- Linked monthly priority: 4月重点 / Q2阶段目标')
    print(f'- Main linked role: {main_role}')
    print(f'- Weekly success definition: {success_def}')

    print('\n## Weekly Top Goals\n')
    print('| Priority | Role | Weekly goal | Success definition | Target day | Notes |')
    print('| --- | --- | --- | --- | --- | --- |')
    if top_goals:
        for pri, role, goal in top_goals:
            print(f'| {pri} | {role} | {goal} | 明确可见进展或交付 | Fri | 基于Q2角色目标提取 |')
    else:
        print('| A1 | 待补充 | 待补充 | 待补充 | Fri | 需要先确认本周核心目标 |')

    print('\n## Role Focus\n')
    if role_focus:
        print(f'- Role to advance most this week: {role_focus[0][0]}')
        print(f'- Role that can accept lower attention this week: {role_focus[-1][0]}')
        print('- Role that needs clearer boundary or delegation: 待结合本周实际安排确认')
    else:
        print('- Role to advance most this week: 待补充')
        print('- Role that can accept lower attention this week: 待补充')
        print('- Role that needs clearer boundary or delegation: 待补充')

    print('\n## High-Return Activities\n')
    activities = role_activities(role_text)
    picked = activities[:3]
    if picked:
        for i, (role, item) in enumerate(picked, start=1):
            linked = top_goals[min(i - 1, len(top_goals) - 1)][2] if top_goals else '待补充'
            print(f'- Activity {i}: {item}')
            print(f'  - linked role: {role}')
            print(f'  - linked goal: {linked}')
            print('  - why it matters: 对角色目标和周结果产生直接杠杆')
    else:
        print('- Activity 1: 待补充本周高回报活动')
        print('  - linked goal: 待补充')
        print('  - why it matters: 待补充')

    print('\n## Delegation And Follow-Up\n')
    if last_moves:
        print(f'- Must personally drive: {last_moves[0]}')
        print(f'- Delegate: {last_moves[1] if len(last_moves) > 1 else "待补充"}')
        print(f'- Follow up only: {last_moves[2] if len(last_moves) > 2 else "待补充"}')
    else:
        print('- Must personally drive: 待补充')
        print('- Delegate: 待补充')
        print('- Follow up only: 待补充')

    print('\n## Protected Time Blocks\n')
    print(f'- Block 1: Mon 09:30-12:00\n  - linked goal: {top_goals[0][2] if top_goals else "待补充"}')
    print(f'- Block 2: Tue 14:00-17:00\n  - linked goal: {top_goals[1][2] if len(top_goals) > 1 else "待补充"}')
    print(f'- Block 3: Thu 09:30-12:00\n  - linked goal: {top_goals[2][2] if len(top_goals) > 2 else "待补充"}')

    print('\n## Week-End Review Hooks\n')
    print(f'- What must be true by Friday: {success_def}')
    print('- Likely unfinished item to delete instead of roll over: 待周中判断')
    print('- Weekly question to answer in review: 本周时间是否真正投在最重要角色与高回报活动上？')

    print('\n## Next Week GPS Preview Inputs\n')
    print(f'- Last weekly GPS goal: {gps_goal or "待补充"}')
    if gps_priorities:
        for item in gps_priorities:
            print(f'- {item}')
    else:
        print('- 待补充上次复盘中的GPS优先级')

    print('\n## Next 1-3 Moves\n')
    print('- 先确认 A1 / A2 是否仍与本周最重要角色一致')
    print('- 把本周固定会议与高回报活动放进时间块')
    print('- 周五复盘时回到 plan versus actual，不要写成普通周总结')


if __name__ == '__main__':
    main()
