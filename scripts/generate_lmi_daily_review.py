#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

PRIMARY_MEMORY_DIR = Path('/Users/woohuaca/.openclaw/workspace-azai/memory')
FALLBACK_MEMORY_DIR = Path('/Users/woohuaca/.openclaw/workspace-main/memory')
AZAI_SESSION_DIR = Path('/Users/woohuaca/.openclaw/agents/azai/sessions')
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


def latest_session_daily_plan(today: date) -> dict | None:
    target = f'今日 LMI 计划 | {today.isoformat()}'
    best: dict | None = None
    best_ts = ''
    if not AZAI_SESSION_DIR.exists():
        return None
    for path in sorted(AZAI_SESSION_DIR.glob('*.jsonl')):
        try:
            lines = path.read_text(encoding='utf-8').splitlines()
        except Exception:
            continue
        for raw in lines:
            try:
                row = json.loads(raw)
            except Exception:
                continue
            if row.get('type') != 'message':
                continue
            msg = row.get('message') or {}
            if msg.get('role') != 'assistant':
                continue
            texts: list[str] = []
            for part in msg.get('content') or []:
                if part.get('type') == 'text':
                    texts.append(part.get('text', ''))
            text = '\n'.join(texts)
            if target not in text:
                continue
            ts = row.get('timestamp', '')
            if ts >= best_ts:
                best_ts = ts
                best = {'timestamp': ts, 'path': str(path), 'text': text}
    return best


def parse_final_plan_rows(text: str) -> list[dict]:
    rows: list[dict] = []
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('|') and '优先级' in stripped and '事项' in stripped and '状态' in stripped:
            in_table = True
            continue
        if in_table and stripped.startswith('|--------'):
            continue
        if in_table and stripped.startswith('|'):
            cells = [c.strip() for c in stripped.strip('|').split('|')]
            if len(cells) >= 5:
                rows.append(
                    {
                        'priority': cells[0],
                        'item': cells[1],
                        'goal': cells[2],
                        'time': cells[3],
                        'status': cells[4],
                    }
                )
            continue
        if in_table and (not stripped or stripped.startswith('### ')):
            break
    return rows


def normalize_table_item(item: str) -> str:
    clean = re.sub(r'【.*?】', '', item).strip()
    clean = re.sub(r'\s+', ' ', clean)
    return clean


def plan_rows_from_session(today: date) -> list[dict]:
    session_plan = latest_session_daily_plan(today)
    if not session_plan:
        return []
    return parse_final_plan_rows(session_plan['text'])


def section_bullets(text: str, heading: str) -> list[str]:
    items: list[str] = []
    for line in lines_under(text, heading):
        stripped = line.strip()
        if stripped.startswith('- '):
            items.append(stripped[2:].strip())
    return items


def anchor_value(text: str, label: str) -> str:
    pattern = rf'-\s+{re.escape(label)}：\s*(.+)'
    match = re.search(pattern, text)
    if match:
        return match.group(1).strip()
    return ''


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


def session_completed(rows: list[dict]) -> list[str]:
    out: list[str] = []
    for row in rows:
        status = row.get('status', '')
        item = normalize_table_item(row.get('item', ''))
        if item and '✅' in status:
            out.append(item)
    return dedupe_keep_order(out)


def session_in_progress(rows: list[dict]) -> list[str]:
    out: list[str] = []
    for row in rows:
        status = row.get('status', '')
        item = normalize_table_item(row.get('item', ''))
        if item and ('⏳' in status or '待开始' in status or '即将开始' in status):
            out.append(item)
    return dedupe_keep_order(out)


def session_unfinished(rows: list[dict]) -> list[str]:
    out: list[str] = []
    for row in rows:
        status = row.get('status', '')
        item = normalize_table_item(row.get('item', ''))
        if not item or '✅' in status:
            continue
        out.append(item)
    return dedupe_keep_order(out)


def session_top(rows: list[dict]) -> str:
    for row in rows:
        priority = row.get('priority', '')
        item = normalize_table_item(row.get('item', ''))
        if item and 'A1' in priority:
            return item
    for row in rows:
        item = normalize_table_item(row.get('item', ''))
        if item:
            return item
    return ''


def pick_tomorrow_first_move(existing_value: str, unfinished: list[str], top: str, done: list[str]) -> str:
    if meaningful(existing_value):
        if unfinished and existing_value in unfinished:
            return existing_value
        if top and existing_value == top and top not in done:
            return existing_value
    if unfinished:
        return unfinished[0]
    return top or '待补充明天第一步'


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
    session_rows = plan_rows_from_session(today)
    month_role = anchor_value(text, '本月主角色')
    month_goals = anchor_value(text, '本月重点目标')
    week_role = anchor_value(text, '本周主角色')
    week_goals = anchor_value(text, '本周关键结果')

    planned = plan_items(text)
    done = session_completed(session_rows) or completed(text)
    doing = session_in_progress(session_rows) or concrete_in_progress(text)
    unfinished = session_unfinished(session_rows) or unfinished_candidates(text)
    top = session_top(session_rows) or (planned[0] if planned else (unfinished[0] if unfinished else '待补充今日最重要结果'))
    happened = '已完成' if done else ('部分推进' if existing_review_value(text, 'Biggest progress') else '待确认')
    biggest_progress = existing_review_value(text, 'Biggest progress') or (done[0] if done else '待补充今天最重要进展')
    main_interruption = existing_review_value(text, 'Main interruption') or '待补充今天最大打断'
    work_experience = existing_review_value(text, 'Work experience') or '待补充今天整体工作的体验与原因'
    low_value = '待补充今天的低价值投入或注意力漂移'
    existing_tomorrow_first_move = existing_review_value(text, 'Tomorrow First Move')
    tomorrow_first_move = pick_tomorrow_first_move(existing_tomorrow_first_move, unfinished, top, done)
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
    if session_rows:
        print('- Final day plan source: latest azai Feishu session update')
    print(f'- Today\'s most important result: {top}')
    print(f'- Did it happen: {happened}')
    if month_role or month_goals or week_role or week_goals:
        print('- Anchor context:')
        if month_role:
            print(f'  - Monthly main role: {month_role}')
        if month_goals:
            print(f'  - Monthly top goals: {month_goals}')
        if week_role:
            print(f'  - Weekly main role: {week_role}')
        if week_goals:
            print(f'  - Weekly key results: {week_goals}')

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
