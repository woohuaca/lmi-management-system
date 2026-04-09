#!/usr/bin/env python3
from __future__ import annotations

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


def latest_weekly_review() -> tuple[Path | None, str]:
    primary = sorted(PRIMARY_MEMORY_DIR.glob('周复盘-*.md'))
    if primary:
        return primary[-1], 'workspace-azai/memory'
    fallback = sorted(FALLBACK_MEMORY_DIR.glob('周复盘-*.md'))
    if fallback:
        return fallback[-1], 'workspace-main/memory (fallback)'
    return None, 'workspace-azai/memory (missing)'


def section(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    out = []
    capture = False
    for line in lines:
        s = line.strip()
        if s.startswith(heading):
            capture = True
            continue
        if capture and s.startswith('## '):
            break
        if capture and s:
            out.append(s)
    return out


def main() -> None:
    today = date.today()
    monday, friday = week_bounds(today)
    week_label = f'{monday.isoformat()} to {friday.isoformat()}'

    review_path, review_source = latest_weekly_review()
    q2_path, q2_source = resolve_memory_file('Q2角色目标-2026.md')
    role_path, role_source = resolve_memory_file('角色澄清表-Q2目标-2026.md')

    review_text = read_text(review_path) if review_path else ''
    q2_text = read_text(q2_path)
    role_text = read_text(role_path)

    plan_vs_actual = section(review_text, '## 📋 计划 vs 实际')
    gap_review = section(review_text, '## 🔍 差距分析')
    lessons = section(review_text, '## 💡 经验提炼')
    next_actions = section(review_text, '## 🔄 下周改进行动')
    observations = section(review_text, '## 📝 其他观察')

    print('# LMI 周复盘草案\n')
    print('## Weekly Snapshot\n')
    print(f'- Review week: {week_label}')
    print(f'- Latest weekly review source: {review_source}')
    print(f'- Q2 source: {q2_source}')
    print(f'- Role source: {role_source}')
    print('- Week theme: 待结合本周实际确认')
    print('- Linked monthly priority: 4月重点 / Q2阶段目标')
    print('- Overall completion level: 待补充')

    print('\n## Plan Vs Actual\n')
    if plan_vs_actual:
        for line in plan_vs_actual[:12]:
            print(f'- {line}')
    else:
        print('- 待补充本周计划与实际对照')

    print('\n## Role Review\n')
    if '角色1' in role_text:
        print('- Best advanced role this week: 待结合本周事实判断')
        print('- Most under-served role this week: 待结合本周事实判断')
        print('- Role that consumed time but created weak return: 待补充')
        print('- Role priority change for next week: 参考Q2角色权重与本周结果调整')
    else:
        print('- Role Review data is missing')

    print('\n## High-Return Activity Review\n')
    if gap_review:
        for line in gap_review[:8]:
            print(f'- {line}')
    else:
        print('- Most effective high-return activity: 待补充')
        print('- Why it worked: 待补充')
        print('- Under-invested high-return activity: 待补充')
        print('- Low-return time spent: 待补充')
        print('- What is worth repeating: 待补充')

    print('\n## Lessons And Insights\n')
    if lessons:
        for line in lessons[:12]:
            print(f'- {line}')
    else:
        print('- Best lesson to keep: 待补充')
        print('- Method or workflow validated: 待补充')
        print('- One thing to stop repeating: 待补充')
        print('- Strategic insight from this week: 待补充')

    print('\n## Carry Forward Decisions\n')
    if next_actions:
        for line in next_actions[:10]:
            print(f'- {line}')
    else:
        print('- Continue: 待补充')
        print('- Start or adjust: 待补充')
        print('- Stop: 待补充')
        print('- Delegate: 待补充')
        print('- Delete instead of rolling over: 待补充')
        print('- Move to next week: 待补充')

    print('\n## Root Cause Review\n')
    if gap_review:
        print('- Target issue: 参考差距分析中的目标合理性判断')
        print('- Execution issue: 参考差距分析中的执行偏差')
        print('- Mechanism issue: 参考是否缺少节奏、跟进、共识或保护时间块')
        print('- Strategic adjustment made this week: 若本周主动转向，需要明确写出')
    else:
        print('- Target issue: 待补充')
        print('- Execution issue: 待补充')
        print('- Mechanism issue: 待补充')
        print('- Strategic adjustment made this week: 待补充')

    print('\n## Next Week GPS Preview\n')
    print('- Goal: 待从本周复盘沉淀为下周唯一主结果')
    print('- Priority:')
    print('  - A1: 待补充')
    print('  - A2: 待补充')
    print('  - B: 待补充')
    print('- Steps:')
    print('  - Step 1: 先保护高回报时间块')
    print('  - Step 2: 明确必须亲自推进与可授权事项')
    print('  - Step 3: 删除不值得滚动的未完成事项')

    print('\n## Other Observations\n')
    if observations:
        for line in observations[:10]:
            print(f'- {line}')
    else:
        print('- 待补充本周精力、情绪、外部变化和战略洞察')

    print('\n## Next 1-3 Moves\n')
    print('- 先做 plan versus actual，而不是普通总结')
    print('- 通过角色视角检查时间投入与结果是否一致')
    print('- 直接把复盘转成下周GPS和保护时间块')


if __name__ == '__main__':
    main()
