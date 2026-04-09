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


def objective_titles(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('## Objective'):
            title = s.split('：', 1)[-1].strip()
            out.append(title)
    return out[:4]


def monthly_milestones(text: str, month_token: str) -> list[str]:
    out = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith(f'**{month_token}里程碑**'):
            out.append(s.split('**：', 1)[-1].strip() if '**：' in s else s.split('**:')[-1].strip())
    return out[:4]


def q2_adjustments(text: str) -> list[str]:
    out = []
    capture = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('## 六、4月（Q2）调整建议'):
            capture = True
            continue
        if capture and s.startswith('## '):
            break
        if capture and s.startswith('| **'):
            cols = [c.strip() for c in s.strip('|').split('|')]
            if len(cols) >= 2:
                out.append(f'{cols[0].replace("**", "")}: {cols[1]}')
    return out[:4]


def role_focuses(text: str) -> list[str]:
    out = []
    current_role = ''
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r'##+ 角色\d+：(.+?)（', s)
        if m:
            current_role = m.group(1)
            continue
        if current_role and s.startswith('| **4月重点** |'):
            cols = [c.strip() for c in s.strip('|').split('|')]
            if len(cols) >= 2:
                out.append(f'{current_role}: {cols[1]}')
                current_role = ''
    return out[:6]


def main() -> None:
    today = date.today()
    month_label = f'{today.year}-{today.month:02d}'

    okr_path, okr_source = resolve_memory_file('Q2-OKR-2026.md')
    role_path, role_source = resolve_memory_file('角色澄清表-Q2目标-2026.md')
    role_review_path, role_review_source = resolve_memory_file('3月角色澄清表复盘-2026.md')

    okr_text = read_text(okr_path)
    role_text = read_text(role_path)
    role_review_text = read_text(role_review_path)

    obj_titles = objective_titles(okr_text)
    milestones = monthly_milestones(okr_text, '4月')
    adjustments = q2_adjustments(role_review_text)
    role_items = role_focuses(role_text)

    print('# LMI 月复盘草案\n')
    print('## Monthly Snapshot\n')
    print(f'- Month: {month_label}')
    print('- Monthly theme: 4月重点 / Q2启动月')
    print(f'- OKR source: {okr_source}')
    print(f'- Role source: {role_source}')
    print(f'- Prior role review source: {role_review_source}')

    print('\n## Personal Focus Review\n')
    if role_items:
        labels = [
            'Family or ethics',
            'Career or finance',
            'Mind or education',
            'Body or health',
            'Social or culture',
            'Spirit or character',
        ]
        for idx, label in enumerate(labels):
            value = role_items[idx] if idx < len(role_items) else '待补充'
            print(f'- {label}: {value}')
    else:
        print('- Family or ethics: 待补充')
        print('- Career or finance: 待补充')
        print('- Mind or education: 待补充')
        print('- Body or health: 待补充')
        print('- Social or culture: 待补充')
        print('- Spirit or character: 待补充')

    print('\n## Company Focus Review\n')
    if milestones:
        for i, item in enumerate(milestones[:3], start=1):
            print(f'- Company focus goal {i}: {item}')
    elif obj_titles:
        for i, item in enumerate(obj_titles[:3], start=1):
            print(f'- Company focus goal {i}: {item}')
    else:
        print('- Company focus goal 1: 待补充')
        print('- Company focus goal 2: 待补充')
        print('- Company focus goal 3: 待补充')

    print('\n## High-Return Activity Review\n')
    if adjustments:
        print(f'- Most effective activity: {adjustments[0]}')
        print(f'- Under-invested activity: {adjustments[2] if len(adjustments) > 2 else "待补充"}')
        print(f'- Low-return activity to reduce: {adjustments[1] if len(adjustments) > 1 else "待补充"}')
    else:
        print('- Most effective activity: 待补充')
        print('- Under-invested activity: 待补充')
        print('- Low-return activity to reduce: 待补充')

    print('\n## Mechanism Review\n')
    print('- Mechanism that worked: 参考角色目标中的管理机制与周复盘沉淀')
    print('- Mechanism that failed or was missing: 待结合本月执行事实填写')

    print('\n## Root Cause Review\n')
    print('- Target issue: 本月目标是否过多、过散或偏乐观')
    print('- Execution issue: 哪些事项没有被真正推进')
    print('- Mechanism issue: 哪些节奏、跟进、保护时间块没有落地')

    print('\n## Next Month Adjustment\n')
    if adjustments:
        for line in adjustments:
            print(f'- {line}')
    else:
        print('- Keep: 待补充')
        print('- Stop: 待补充')
        print('- Strengthen: 待补充')
        print('- Redesign: 待补充')

    print('\n## Next 1-3 Moves\n')
    print('- 对照 4 月里程碑回看哪些结果真正发生')
    print('- 从周复盘中抽出本月最稳定的高回报活动')
    print('- 把月复盘结论沉到下月角色重点和周计划中')


if __name__ == '__main__':
    main()
