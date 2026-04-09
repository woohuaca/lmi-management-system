#!/usr/bin/env python3
from __future__ import annotations

from datetime import date
from pathlib import Path
import re

PRIMARY_MEMORY_DIR = Path('/Users/woohuaca/.openclaw/workspace-azai/memory')
FALLBACK_MEMORY_DIR = Path('/Users/woohuaca/.openclaw/workspace-main/memory')


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


def parse_roles(text: str) -> list[dict[str, str]]:
    roles = []
    current: dict[str, str] | None = None
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r'##+ 角色\d+：(.+?)（(.+?)）', s)
        if m:
            if current:
                roles.append(current)
            current = {'title': m.group(1), 'weight': m.group(2)}
            continue
        if current and s.startswith('| **主要职责** |'):
            current['responsibility'] = [c.strip() for c in s.strip('|').split('|')][1]
        if current and s.startswith('| **Q2关键业绩** |'):
            current['key_results'] = [c.strip() for c in s.strip('|').split('|')][1]
        if current and s.startswith('| **主要高回报活动** |'):
            current['high_return'] = [c.strip() for c in s.strip('|').split('|')][1]
        if current and s.startswith('| **管理机制** |'):
            current['mechanism'] = [c.strip() for c in s.strip('|').split('|')][1]
        if current and s.startswith('| **时间投入** |'):
            current['time'] = [c.strip() for c in s.strip('|').split('|')][1]
    if current:
        roles.append(current)
    return roles


def parse_role_review_rows(text: str) -> list[str]:
    out = []
    capture = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('## 一、目标达成回顾'):
            capture = True
            continue
        if capture and s.startswith('## '):
            break
        if capture and s.startswith('| **'):
            cols = [c.strip() for c in s.strip('|').split('|')]
            if len(cols) >= 6:
                out.append(f'{cols[0].replace("**","")}: {cols[3]} / 达成率 {cols[4]}')
    return out[:4]


def main() -> None:
    today = date.today()
    quarter = ((today.month - 1) // 3) + 1
    period = f'{today.year} Q{quarter} role review checkpoint'

    role_path, role_source = resolve_memory_file('角色澄清表-Q2目标-2026.md')
    role_review_path, role_review_source = resolve_memory_file('3月角色澄清表复盘-2026.md')

    role_text = read_text(role_path)
    role_review_text = read_text(role_review_path)

    roles = parse_roles(role_text)
    review_rows = parse_role_review_rows(role_review_text)
    primary = roles[0] if roles else {}
    current_items = [item.strip() for item in primary.get('high_return', '').split('<br>') if item.strip()]
    secondary_items = [item.strip() for item in roles[1].get('high_return', '').split('<br>') if len(roles) > 1 and item.strip()]
    tertiary_items = [item.strip() for item in roles[2].get('high_return', '').split('<br>') if len(roles) > 2 and item.strip()]

    print('# LMI 角色复盘草案\n')
    print('## Role Snapshot\n')
    print(f'- Review period: {period}')
    print(f'- Role source: {role_source}')
    print(f'- Prior role review source: {role_review_source}')
    print(f'- Role title: {primary.get("title","待补充")}')
    print(f'- Management role: {primary.get("weight","待补充")}')

    print('\n## Responsibility Review\n')
    if roles:
        for idx, role in enumerate(roles[:3], start=1):
            print(f'- Responsibility {idx}: {role.get("title","待补充")} / {role.get("responsibility","待补充")}')
            print('  - still valid: 待结合当前阶段判断')
            print('  - current reality: 参考本季度推进事实与最近周复盘')
    else:
        print('- Responsibility 1: 待补充')
        print('  - still valid: 待补充')
        print('  - current reality: 待补充')

    print('\n## Key Result Review\n')
    if roles:
        for idx, role in enumerate(roles[:3], start=1):
            print(f'- Key result {idx}: {role.get("key_results","待补充")}')
            result = review_rows[idx - 1] if idx - 1 < len(review_rows) else '待结合实际结果填写'
            print(f'  - result: {result}')
            print('  - still the right metric: 待判断是否仍代表该角色价值')
    else:
        print('- Key result 1: 待补充')
        print('  - result: 待补充')
        print('  - still the right metric: 待补充')

    print('\n## Time Investment Review\n')
    if roles:
        print(f'- Time spent mostly on: {", ".join([r.get("title","待补充") for r in roles[:3]])}')
        print(f'- What matches the role: {roles[0].get("time","待补充")}')
        print('- What does not match the role: 待结合最近几周时间投入判断')
    else:
        print('- Time spent mostly on: 待补充')
        print('- What matches the role: 待补充')
        print('- What does not match the role: 待补充')

    print('\n## High-Return Activity Review\n')
    if roles:
        print(f'- Activity to keep: {current_items[0] if current_items else "待补充"}')
        print(f'- Activity to stop: {secondary_items[0] if secondary_items else "待补充并结合现实判断"}')
        print(f'- Activity to strengthen: {tertiary_items[0] if tertiary_items else "待补充"}')
    else:
        print('- Activity to keep: 待补充')
        print('- Activity to stop: 待补充')
        print('- Activity to strengthen: 待补充')

    print('\n## Role Adjustment\n')
    print('- Sharpen role boundary: 哪些职责应继续由当前角色承担，哪些应收缩')
    print('- Delegate or remove: 哪些事项不应继续挂在该角色下')
    print('- New mechanism needed: 参考管理机制与最近复盘暴露的问题')

    print('\n## Next 1-3 Moves\n')
    print('- 对照角色澄清表，确认当前最该强化的 1-2 个角色')
    print('- 把角色复盘结论映射到下月重点和下周计划')
    print('- 对不再匹配角色价值的事项做删除、授权或重新归属')


if __name__ == '__main__':
    main()
