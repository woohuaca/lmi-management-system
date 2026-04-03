#!/usr/bin/env python3
from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

MEMORY_DIR = Path('/Users/woohuaca/.openclaw/workspace-main/memory')


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return ''


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


def extract_progress(yesterday: str) -> str:
    completed = [ln for ln in section_lines(yesterday, ['### 已完成']) if ln.startswith('- [x]')]
    if completed:
        return re.sub(r'^- \[x\]\s*', '', completed[0])
    ongoing = [ln for ln in section_lines(yesterday, ['### 进行中']) if ln.startswith('- ')]
    if ongoing:
        return ongoing[0][2:]
    return '待从昨天记录补充'


def extract_unfinished(yesterday: str) -> list[str]:
    items: list[str] = []
    for line in yesterday.splitlines():
        m = re.match(r'\d+\. \*\*(.+?)\*\*', line.strip())
        if m:
            items.append(m.group(1))
    pending = [ln for ln in section_lines(yesterday, ['### 已完成']) if ln.startswith('- [ ]')]
    for ln in pending:
        txt = re.sub(r'^- \[ \]\s*', '', ln)
        if txt not in items:
            items.append(txt)
    return items[:5]


def classify(items: list[str]) -> tuple[list[str], list[str], list[str], list[str]]:
    a: list[str] = []
    b: list[str] = []
    c: list[str] = []
    d: list[str] = []
    for item in items:
        low = item.lower()
        if any(k in item for k in ['会议', '沟通', '对齐', '协调', '复盘', '公众号']) or any(k in low for k in ['sync', 'meeting']):
            d.append(item)
        elif any(k in item for k in ['跟进', '联系', '触达', '回复']) or any(k in low for k in ['follow', 'contact']):
            c.append(item)
        elif any(k in item for k in ['提交', 'charter', '目标', '方案', '复盘']) or any(k in low for k in ['charter', 'goal']):
            a.append(item)
        else:
            b.append(item)
    return a[:3], b[:3], c[:3], d[:3]


def today_schedule(today_text: str) -> list[str]:
    rows = []
    for line in today_text.splitlines():
        if re.match(r'^\|\s*\d{2}:\d{2}-\d{2}:\d{2}\s*\|', line.strip()):
            parts = [p.strip() for p in line.strip('|').split('|')]
            if len(parts) >= 2:
                rows.append(f'- {parts[0]} {parts[1]}')
    return rows[:6]


def main() -> None:
    today = date.today()
    yesterday = today - timedelta(days=1)
    today_path = MEMORY_DIR / f'{today.isoformat()}.md'
    yesterday_path = MEMORY_DIR / f'{yesterday.isoformat()}.md'

    today_text = read_text(today_path)
    yesterday_text = read_text(yesterday_path)

    biggest_progress = extract_progress(yesterday_text)
    unfinished = extract_unfinished(yesterday_text)
    tomorrow_first_move = unfinished[0] if unfinished else '待从昨天复盘补充'
    a, b, c, d = classify(unfinished)
    schedule = today_schedule(today_text)

    if not schedule:
        schedule = [
            '- 08:30-09:30 Day LMI / 晨间计划梳理',
            '- 09:30-12:00 深度工作时间块',
            '- 14:00-17:00 重点事项推进',
            '- 17:30-18:00 日复盘与明日准备',
        ]

    carry = []
    for item in unfinished[:3]:
        carry.append(f'- {item}: 今日重新决策（继续 / 延后 / 授权 / 删除）')
    if not carry:
        carry = ['- 昨天未完成事项待补充']

    print(f'# {today.isoformat()} LMI 日计划草案\n')
    print('## Imported From Yesterday\n')
    print(f'- Yesterday\'s biggest progress: {biggest_progress}')
    if unfinished:
        print('- Yesterday\'s unfinished items to re-decide:')
        for item in unfinished[:5]:
            print(f'  - {item}')
    else:
        print('- Yesterday\'s unfinished items to re-decide: 待补充')
    print(f'- Yesterday\'s tomorrow first move: {tomorrow_first_move}')
    print('- Carry forward decisions:')
    for line in carry:
        print(f'  {line}')

    print('\n## A：重要事项\n')
    for i, item in enumerate(a or ['待你补充今天最重要的 1-2 个关键结果'], start=1):
        print(f'- A{i}: {item}')

    print('\n## B：紧要事项\n')
    for i, item in enumerate(b or ['待补充今天必须处理的紧急事项'], start=1):
        print(f'- B{i}: {item}')

    print('\n## C：联络/追踪事项\n')
    for i, item in enumerate(c or ['待补充今日需要联络或跟进的人与事项'], start=1):
        print(f'- C{i}: {item}')

    print('\n## D：会议/讨论/协调事项\n')
    for i, item in enumerate(d or ['公众号更新 / 讨论事项 / 会议安排待补充'], start=1):
        print(f'- D{i}: {item}')

    print('\n## Schedule\n')
    for line in schedule:
        print(line)

    print('\n## Todays Completed Items\n')
    print('- [ ] 待在今天执行后回填')

    print('\n## Daily Review\n')
    print('- Biggest progress: 待今晚复盘填写')
    print('- Main interruption: 待今晚复盘填写')
    print('- Roll forward or delegate: 今日收工前重新决策未完成事项')

    print('\n## Next 1-3 Moves\n')
    print(f'- 先确认 A1 是否仍是：{a[0] if a else tomorrow_first_move}')
    print('- 把今日新增事项先分到 A/B/C/D，再决定是否进入今天')
    print('- 收工前补 Daily Review，并写下 Tomorrow First Move')


if __name__ == '__main__':
    main()
