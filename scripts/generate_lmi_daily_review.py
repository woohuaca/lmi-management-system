#!/usr/bin/env python3
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

MEMORY_DIR = Path('/Users/woohuaca/.openclaw/workspace-main/memory')


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return ''


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
        if capture and stripped.startswith('#'):
            break
        if capture and stripped:
            out.append(stripped)
    return out


def plan_items(text: str) -> list[str]:
    items = []
    for line in text.splitlines():
        m = re.match(r'\d+\. \*\*(.+?)\*\*', line.strip())
        if m:
            items.append(m.group(1))
    return items


def completed(text: str) -> list[str]:
    return [re.sub(r'^- \[x\]\s*', '', ln) for ln in lines_under(text, '### 已完成') if ln.startswith('- [x]')]


def in_progress(text: str) -> list[str]:
    return [ln[2:] for ln in lines_under(text, '### 进行中') if ln.startswith('- ')]


def main() -> None:
    today = date.today()
    today_path = MEMORY_DIR / f'{today.isoformat()}.md'
    text = read_text(today_path)

    planned = plan_items(text)
    done = completed(text)
    doing = in_progress(text)
    top = planned[0] if planned else '待补充今日最重要结果'
    happened = '部分推进' if done or doing else '待确认'
    low_value = '待补充今天的低价值投入或注意力漂移'

    print(f'# {today.isoformat()} LMI 日复盘草案\n')
    print('## Daily Snapshot\n')
    print(f'- Date: {today.isoformat()}')
    print(f'- Today\'s most important result: {top}')
    print(f'- Did it happen: {happened}')

    print('\n## Completed Items\n')
    if done:
        for item in done:
            print(f'- {item}')
    else:
        print('- 待补充今天已完成事项')
    if doing:
        print('- In progress:')
        for item in doing:
            print(f'  - {item}')

    print('\n## Attention Drift Review\n')
    print(f'- Biggest interruption: {doing[0] if doing else "待补充今天最大打断"}')
    print(f'- Low-value time: {low_value}')
    print('- What deserved more focus: 最重要结果是否获得了连续时间块')

    print('\n## Adjustment Decisions\n')
    print('- Continue: 把仍然服务本周目标的事项转入明天草案')
    print('- Delay: 不服务明天重点的事项转本周稍后')
    print('- Delegate: 能由他人推进的事项转为跟进')
    print('- Drop: 已不重要的事项直接删除，不自动滚动')

    print('\n## Tomorrow First Move\n')
    if doing:
        print(f'- {doing[0]}')
    elif planned:
        print(f'- {planned[0]}')
    else:
        print('- 待补充明天第一步')

    print('\n## Next 1-3 Moves\n')
    print('- 回填今天完成与未完成的事实')
    print('- 明确明天第一步，并写入明天的 Imported From Yesterday')
    print('- 对未完成事项逐项做继续 / 延后 / 授权 / 删除决策')


if __name__ == '__main__':
    main()
