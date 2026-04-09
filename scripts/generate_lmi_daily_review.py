#!/usr/bin/env python3
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

PRIMARY_MEMORY_DIR = Path('/Users/woohuaca/.openclaw/workspace-azai/memory')
FALLBACK_MEMORY_DIR = Path('/Users/woohuaca/.openclaw/workspace-main/memory')
PLACEHOLDER_MARKERS = ('待补充', '待今晚', '待确认')
GUIDANCE_MARKERS = ('当前无明确', '当前无固定', '建议开工前', '建议先补', '请至少补', '请补 1')


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


def section_bullets(text: str, heading: str) -> list[str]:
    items: list[str] = []
    for line in lines_under(text, heading):
        stripped = line.strip()
        if stripped.startswith('- '):
            items.append(stripped[2:].strip())
    return items


def strip_code_prefix(item: str) -> str:
    item = re.sub(r'^[A-D]\d+:\s*', '', item).strip()
    item = re.sub(r'^\[.\]\s*', '', item).strip()
    return item


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


def meaningful(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return False
    return not any(marker in stripped for marker in PLACEHOLDER_MARKERS + GUIDANCE_MARKERS)


def plan_items(text: str) -> list[str]:
    items: list[str] = []
    for heading in ['## A：重要事项', '## B：紧要事项', '## C：联络/追踪事项', '## D：会议/讨论/协调事项']:
        for item in section_bullets(text, heading):
            clean = strip_code_prefix(item)
            if meaningful(clean):
                items.append(clean)
    return items


def completed(text: str) -> list[str]:
    items: list[str] = []
    for item in section_bullets(text, '## Todays Completed Items'):
        if item.startswith('[x]'):
            clean = strip_code_prefix(item)
            if meaningful(clean):
                items.append(clean)
    return items


def in_progress(text: str) -> list[str]:
    items: list[str] = []
    for heading in ['## A：重要事项']:
        for item in section_bullets(text, heading):
            clean = strip_code_prefix(item)
            if meaningful(clean):
                items.append(clean)
    return items[:2]


def concrete_in_progress(text: str) -> list[str]:
    return dedupe_keep_order([item for item in in_progress(text) if meaningful(item)])[:2]


def existing_review_value(text: str, key: str) -> str:
    m = re.search(rf'{re.escape(key)}:\s*(.+)', text)
    if m and meaningful(m.group(1)):
        return m.group(1).strip()
    return ''


def unfinished_candidates(text: str) -> list[str]:
    items: list[str] = []
    for heading in ['## A：重要事项', '## B：紧要事项', '## C：联络/追踪事项', '## D：会议/讨论/协调事项']:
        for item in section_bullets(text, heading):
            clean = strip_code_prefix(item)
            if meaningful(clean):
                items.append(clean)
    done = set(completed(text))
    doing = concrete_in_progress(text)
    out: list[str] = []
    for item in items:
        if item not in done and item not in out:
            out.append(item)
    for item in doing:
        if item not in out:
            out.append(item)
    return out[:6]

def update_daily_file(path: Path, biggest_progress: str, main_interruption: str, work_experience: str, tomorrow_first_move: str, unfinished: list[str]) -> None:
    text = read_text(path)
    if not text:
        return

    def repl(pattern: str, replacement: str, src: str) -> str:
        if re.search(pattern, src):
            return re.sub(pattern, replacement, src, count=1)
        return src

    updated = text
    updated = repl(r'Biggest progress:\s*.*', f'Biggest progress: {biggest_progress}', updated)
    updated = repl(r'Main interruption:\s*.*', f'Main interruption: {main_interruption}', updated)
    updated = repl(r'Work experience:\s*.*', f'Work experience: {work_experience}', updated)
    updated = repl(r'Tomorrow First Move:\s*.*', f'Tomorrow First Move: {tomorrow_first_move}', updated)
    roll_line = '；'.join(unfinished[:3]) if unfinished else '今日收工前重新决策未完成事项'
    updated = repl(r'Roll forward or delegate:\s*.*', f'Roll forward or delegate: {roll_line}', updated)

    snapshot_block = [
        '',
        '## LMI Review Snapshot',
        '',
        f'- Biggest progress: {biggest_progress}',
        f'- Main interruption: {main_interruption}',
        f'- Work experience: {work_experience}',
        '- Unfinished items to re-decide:',
    ]
    if unfinished:
        snapshot_block.extend([f'  - {item}' for item in unfinished[:5]])
    else:
        snapshot_block.append('  - 待补充')
    snapshot_block.append(f'- Tomorrow First Move: {tomorrow_first_move}')
    snapshot_text = '\n'.join(snapshot_block)

    if '## LMI Review Snapshot' in updated:
        updated = re.sub(r'\n## LMI Review Snapshot[\s\S]*$', snapshot_text + '\n', updated)
    else:
        updated = updated.rstrip() + '\n' + snapshot_text + '\n'

    if updated != text:
        path.write_text(updated, encoding='utf-8')


def main() -> None:
    today = date.today()
    today_rel = f'{today.isoformat()}.md'
    today_path, today_source = resolve_memory_file(today_rel)
    text = read_text(today_path)

    planned = plan_items(text)
    done = completed(text)
    doing = concrete_in_progress(text)
    unfinished = unfinished_candidates(text)
    top = planned[0] if planned else (unfinished[0] if unfinished else '待补充今日最重要结果')
    happened = '已完成' if done else ('部分推进' if existing_review_value(text, 'Biggest progress') else '待确认')
    biggest_progress = existing_review_value(text, 'Biggest progress') or (done[0] if done else '待补充今天最重要进展')
    main_interruption = existing_review_value(text, 'Main interruption') or '待补充今天最大打断'
    work_experience = existing_review_value(text, 'Work experience') or '待补充今天整体工作的体验与原因'
    low_value = '待补充今天的低价值投入或注意力漂移'
    tomorrow_first_move = existing_review_value(text, 'Tomorrow First Move') or (unfinished[0] if unfinished else top)
    completed_prompt = '请至少补 1 条今天已完成事项，优先填最接近 A1/A2 的结果。'
    progress_prompt = '请补 1 句今天最重要推进，哪怕只是部分推进也可以。'
    interruption_prompt = '请补 1 个今天最大的打断或分心来源。'
    experience_prompt = '请补 1 句今天整体工作的体验，比如顺、卡、累、兴奋，并写出最主要原因。'
    low_value_prompt = '请补 1 个今天明显偏低价值的投入或注意力漂移。'

    update_daily_file(today_path, biggest_progress, main_interruption, work_experience, tomorrow_first_move, unfinished)

    print(f'# {today.isoformat()} LMI 日复盘草案\n')
    print('## Daily Snapshot\n')
    print(f'- Date: {today.isoformat()}')
    print(f'- Review source: {today_source}')
    print(f'- Today\'s most important result: {top}')
    print(f'- Did it happen: {happened}')

    print('\n## Completed Items\n')
    if done:
        for item in done:
            print(f'- {item}')
    else:
        print(f'- {completed_prompt}')
    if doing:
        print('- In progress:')
        for item in doing:
            print(f'  - {item}')

    print('\n## Attention Drift Review\n')
    print(f"- Biggest progress: {biggest_progress if meaningful(biggest_progress) else progress_prompt}")
    print(f"- Biggest interruption: {main_interruption if meaningful(main_interruption) else interruption_prompt}")
    print(f"- Low-value time: {low_value if meaningful(low_value) else low_value_prompt}")
    print(f"- What deserved more focus: {top} 是否获得了连续时间块")

    print('\n## Work Experience Feedback\n')
    print(f"- Today felt: {work_experience if meaningful(work_experience) else experience_prompt}")
    print('- What gave energy: 今天哪种工作节奏、推进方式或反馈最给你能量。')
    print('- What caused friction: 今天最卡的地方是什么，是任务本身、协作还是切换过多。')
    print('- What to keep tomorrow: 明天想保留的一个工作方式或节奏。')

    print('\n## Adjustment Decisions\n')
    continue_item = unfinished[0] if unfinished else top
    delay_item = unfinished[1] if len(unfinished) > 1 else '不服务明天重点的事项'
    delegate_item = unfinished[2] if len(unfinished) > 2 else '可由他人推进的跟进事项'
    print(f'- Continue: {continue_item} 若仍服务本周目标，转入明天草案')
    print(f'- Delay: {delay_item} 若不服务明天重点，转本周稍后')
    print(f'- Delegate: {delegate_item} 若适合交给他人推进，转为跟进')
    print('- Drop: 已不重要或已失去窗口的事项直接删除，不自动滚动')

    print('\n## Tomorrow First Move\n')
    print(f'- {tomorrow_first_move}')

    print('\n## Next 1-3 Moves\n')
    print('- 先补 1 条今天已完成事项，再补 1 条今天最大推进')
    print('- 明确明天第一步，并写入明天的 Imported From Yesterday')
    print('- 对未完成事项逐项做继续 / 延后 / 授权 / 删除决策')


if __name__ == '__main__':
    main()
