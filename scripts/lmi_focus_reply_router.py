#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from lmi_execution_support import (
    PRIMARY_MEMORY_DIR,
    append_focus_end,
    append_focus_start,
    focus_entries_for_date,
    load_json,
    now_local,
    open_focus_sessions,
    reminder_state_path,
    save_json,
)

START_MARKER_RE = re.compile(r'LMI_FOCUS_START_JSON:\s*(\{.*\})')
END_MARKER_RE = re.compile(r'LMI_FOCUS_END_JSON:\s*(\{.*\})')


def parse_marker(reply_context: str, pattern: re.Pattern[str]) -> dict | None:
    match = pattern.search(reply_context)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except Exception:
        return None


def normalize_message(text: str) -> str:
    return re.sub(r'\s+', '', text.strip().lower())


def is_start_command(text: str) -> bool:
    normalized = normalize_message(text)
    return normalized in {'开始', '开始专注', 'start', 'focusstart'}


def is_complete_command(text: str) -> bool:
    normalized = normalize_message(text)
    return (
        normalized.startswith('完成')
        or normalized.startswith('做完')
        or normalized.endswith('完成了')
        or normalized.endswith('做完了')
        or normalized in {'结束了', '结束', '已完成', '搞定了'}
    )


def is_interrupt_command(text: str) -> bool:
    normalized = normalize_message(text)
    return normalized.startswith('中断') or normalized.startswith('暂停')


def extract_detail(text: str, prefixes: list[str]) -> str:
    stripped = text.strip()
    for prefix in prefixes:
        if stripped.startswith(prefix):
            tail = stripped[len(prefix):].lstrip('：: ')
            return tail.strip()
    return ''


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Route a Feishu reply to LMI focus start/end actions.')
    parser.add_argument('--message', required=True, help='User message body, e.g. 开始 / 1 / 完成：xxx')
    parser.add_argument('--reply-context', default='', help='Optional replied message body containing legacy reminder markers.')
    parser.add_argument('--memory-dir', default=str(PRIMARY_MEMORY_DIR))
    return parser


def load_state(memory_dir: Path) -> dict:
    path = reminder_state_path(memory_dir)
    state = load_json(path, {})
    if not isinstance(state, dict):
        state = {}
    state.setdefault('pending_start', None)
    state.setdefault('pending_setup', None)
    state.setdefault('pending_end', None)
    state.setdefault('pending_continue', None)
    return state


def save_state(memory_dir: Path, state: dict) -> None:
    save_json(reminder_state_path(memory_dir), state)


def pending_recent(item: dict | None, *, minutes: int = 60) -> bool:
    if not item or not item.get('sent_at'):
        return False
    sent_at = datetime.fromisoformat(item['sent_at'])
    return (now_local() - sent_at).total_seconds() <= minutes * 60


def parse_pomodoro_count(text: str) -> int | None:
    stripped = text.strip()
    if '.' in stripped or '．' in stripped or '点' in stripped:
        return None
    normalized = normalize_message(text)
    if normalized in {'默认', '默认1个', '默认一个', '1', '1个', '一个', '1个番茄', '一个番茄', '25', '25分钟'}:
        return 1
    if normalized in {'2', '2个', '两个', '2个番茄', '两个番茄', '50', '50分钟'}:
        return 2
    if normalized in {'3', '3个', '三个', '3个番茄', '三个番茄', '75', '75分钟'}:
        return 3
    match = re.fullmatch(r'([123])', normalized)
    if match:
        return int(match.group(1))
    return None


def compose_focus_entry(task: str, minutes: int, count: int) -> str:
    eta = (datetime.now().astimezone() + timedelta(minutes=minutes)).strftime('%H:%M')
    if count == 1:
        count_text = '1 个番茄'
    else:
        count_text = f'{count} 个番茄'
    return '\n'.join([
        f'已进入专注：{task}',
        f'- 专注设置：{count_text}（{minutes} 分钟）',
        f'- 预计收口：{eta}',
        '- 现在先做 3 个动作：关掉无关窗口、静音不必要提醒、把这一轮要产出的 1 句话写下来。',
        '- 然后只做这一件事，我会在时间到时叫你收口。',
    ])


def compose_partial_followup(task: str, result: str) -> str:
    detail = result.strip() or '这轮已有初步推进。'
    return '\n'.join([
        f'收到，这轮先推进到了：{detail}',
        f'- 当前专注块：{task}',
        '- 先停 3-5 分钟，喝水、站起来、把脑子从刚才的专注里缓一缓。',
        '- 然后回复：`继续1个` / `继续2个` / `收口`。',
        f'- 如果继续，我会沿着这个专注块 `{task}` 接着推进。',
    ])


def session_meta_for(session_id: str, memory_dir: Path) -> dict:
    entries, _ = focus_entries_for_date(now_local().date(), primary_memory_dir=memory_dir, fallback_memory_dir=None)
    for entry in entries:
        if entry.get('type') == 'start' and entry.get('session_id') == session_id:
            linked_week_goal = entry.get('details', {}).get('linked_week_goal', entry.get('task', '当前专注事项'))
            return {
                'task': entry.get('task', '当前专注事项'),
                'task_class': entry.get('task_class', 'A'),
                'role': entry.get('role', '未指定角色'),
                'parent_goal': entry.get('details', {}).get('parent_goal', linked_week_goal),
                'linked_week_goal': linked_week_goal,
                'linked_month_goal': entry.get('details', {}).get('linked_month_goal', entry.get('task', '当前专注事项')),
                'high_return': entry.get('details', {}).get('high_return') == 'yes',
            }
    return {
        'task': '当前专注事项',
        'task_class': 'A',
        'role': '未指定角色',
        'parent_goal': '当前专注事项',
        'linked_week_goal': '当前专注事项',
        'linked_month_goal': '当前专注事项',
        'high_return': True,
    }


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    memory_dir = Path(args.memory_dir).expanduser()
    raw_message = args.message.strip()
    normalized = normalize_message(raw_message)
    state = load_state(memory_dir)
    ack_only = normalized in {'好的', '好', '收到', 'ok', 'okay', 'okk'}

    start_meta = parse_marker(args.reply_context, START_MARKER_RE)
    if not start_meta and pending_recent(state.get('pending_start')):
        start_meta = state['pending_start']
    if start_meta and is_start_command(raw_message):
        open_sessions, _ = open_focus_sessions(now_local().date(), primary_memory_dir=memory_dir, fallback_memory_dir=None)
        if open_sessions:
            current = open_sessions[0]
            eta = (
                datetime.fromisoformat(current['details']['started_at']) +
                timedelta(minutes=int(current['minutes']))
            ).strftime('%H:%M')
            print(f'当前已有进行中的番茄钟：{current["task"]}。预计 {eta} 收口，本次不重复启动。')
            return
        state['pending_setup'] = {
            'sent_at': now_local().isoformat(),
            'display_task': start_meta.get('display_task') or start_meta.get('task', '未命名事项'),
            'task': start_meta.get('task', '未命名事项'),
            'parent_goal': start_meta.get('parent_goal', ''),
            'task_class': start_meta.get('task_class', 'A'),
            'role': start_meta.get('role', '未指定角色'),
            'suggested_minutes': int(start_meta.get('suggested_minutes') or start_meta.get('minutes', 25)),
            'linked_week_goal': start_meta.get('linked_week_goal', ''),
            'linked_month_goal': start_meta.get('linked_month_goal', ''),
            'high_return': bool(start_meta.get('high_return', True)),
        }
        state['pending_start'] = None
        save_state(memory_dir, state)
        lines = [
            f'准备开始专注：{state["pending_setup"]["display_task"]}',
        ]
        if state["pending_setup"].get("parent_goal"):
            lines.append(f'- 归属目标：{state["pending_setup"]["parent_goal"]}')
        lines.extend([
            '- 这块你想用几个番茄？回复：`1` / `2` / `3`。',
            '- 参考：1=25 分钟，2=50 分钟，3=75 分钟。',
            '- 先不支持 `2.5` 这种小数，先用完整番茄保护专注。',
            '- 如果你不想想太多，直接回 `1` 就行。',
        ])
        print('\n'.join(lines))
        return

    pending_setup = state.get('pending_setup')
    count = parse_pomodoro_count(raw_message) if pending_recent(pending_setup) else None
    if pending_setup and count is None and pending_recent(pending_setup):
        if ack_only:
            print('\n'.join([
                '这一步我先不把 `好的` 当成时长选择，避免和普通确认混在一起。',
                '- 如果你要继续，请直接回复：`1` / `2` / `3`。',
                '- 参考：1=25 分钟，2=50 分钟，3=75 分钟。',
            ]))
            return
        print('\n'.join([
            '这一步先只支持完整番茄数：`1` / `2` / `3`。',
            '- 1 = 25 分钟',
            '- 2 = 50 分钟',
            '- 3 = 75 分钟',
            '- 如果你只是想先试一下，直接回 `1` 就行。',
        ]))
        return
    if pending_setup and count:
        task = pending_setup.get('display_task') or pending_setup.get('task', '未命名事项')
        planned_minutes = count * 25
        task_class = pending_setup.get('task_class', 'A')
        role = pending_setup.get('role', '未指定角色')
        week_goal = pending_setup.get('linked_week_goal', task)
        month_goal = pending_setup.get('linked_month_goal', week_goal)
        high_return = bool(pending_setup.get('high_return', task_class == 'A'))
        _, session_id = append_focus_start(
            task,
            task_class=task_class,
            role=role,
            planned_minutes=planned_minutes,
            parent_goal=pending_setup.get('parent_goal', week_goal or task),
            linked_week_goal=week_goal,
            linked_month_goal=month_goal,
            high_return=high_return,
            memory_dir=memory_dir,
        )
        state['pending_setup'] = None
        save_state(memory_dir, state)
        print(compose_focus_entry(task, planned_minutes, count))
        return

    if ack_only and (
        pending_recent(state.get('pending_start'))
        or pending_recent(state.get('pending_setup'))
        or pending_recent(state.get('pending_continue'), minutes=180)
    ):
        print('\n'.join([
            '我先不把 `好的` 当成专注触发词，避免和普通确认混在一起。',
            '- 如果你现在要进入专注模式，请直接回复：`开始` 或 `开始专注`。',
            '- 如果是在选择时长，就直接回复：`1` / `2` / `3`。',
        ]))
        return

    end_meta = parse_marker(args.reply_context, END_MARKER_RE)
    if not end_meta and pending_recent(state.get('pending_end'), minutes=180):
        end_meta = state['pending_end']
    open_sessions, _ = open_focus_sessions(now_local().date(), primary_memory_dir=memory_dir, fallback_memory_dir=None)
    latest_open = open_sessions[0] if open_sessions else None
    latest_open_due = False
    if latest_open:
        started_at = datetime.fromisoformat(latest_open['details']['started_at'])
        latest_open_due = now_local() >= started_at + timedelta(minutes=int(latest_open['minutes']))
    if not end_meta and (is_complete_command(raw_message) or is_interrupt_command(raw_message) or latest_open_due):
        if latest_open:
            current = latest_open
            end_meta = {
                'session_id': current['session_id'],
                'task': current['task'],
                'task_class': current.get('task_class', 'A'),
                'role': current.get('role', '未指定角色'),
                'parent_goal': current.get('details', {}).get('linked_week_goal', current['task']),
                'linked_week_goal': current.get('details', {}).get('linked_week_goal', current['task']),
                'linked_month_goal': current.get('details', {}).get('linked_month_goal', current['task']),
                'high_return': current.get('details', {}).get('high_return') == 'yes',
            }
    if end_meta:
        session_id = end_meta.get('session_id')
        task = end_meta.get('task', '当前专注事项')
        meta = session_meta_for(session_id, memory_dir) if session_id else {
            'task': task,
            'task_class': end_meta.get('task_class', 'A'),
            'role': end_meta.get('role', '未指定角色'),
            'linked_week_goal': end_meta.get('linked_week_goal', task),
            'linked_month_goal': end_meta.get('linked_month_goal', task),
            'high_return': bool(end_meta.get('high_return', True)),
        }
        if is_complete_command(raw_message):
            result = extract_detail(raw_message, ['完成', 'done', '做完', '结束'])
            if not result or result in {'了', '这个任务', '任务'}:
                result = f'已完成：{task}'
            append_focus_end(
                session_id=session_id,
                result=result,
                status='completed',
                memory_dir=memory_dir,
            )
            state['pending_end'] = None
            state['pending_continue'] = {
                'sent_at': now_local().isoformat(),
                **meta,
            }
            save_state(memory_dir, state)
            lines = [
                f'已记录完成：{task}',
                f'- 本轮产出：{result}',
                '- 现在先收口 3 分钟：保存结果、写下下一步、让大脑离开刚才的高专注。',
                '- 然后你可以回复：`继续1个` / `继续2个` / `收口` / `切换任务`。',
            ]
            if meta.get('parent_goal'):
                lines.insert(1, f'- 归属目标：{meta["parent_goal"]}')
            print('\n'.join(lines))
            return
        if is_interrupt_command(raw_message):
            reason = extract_detail(raw_message, ['中断', 'interrupt', '暂停']) or '用户主动中断'
            append_focus_end(
                session_id=session_id,
                result='本轮未完成，待后续继续',
                status='interrupted',
                interruption_reason=reason,
                memory_dir=memory_dir,
            )
            state['pending_end'] = None
            state['pending_continue'] = {
                'sent_at': now_local().isoformat(),
                **meta,
            }
            save_state(memory_dir, state)
            print(f'已记录本轮中断：{task}。原因：{reason}')
            return
        result = raw_message.strip()
        append_focus_end(
            session_id=session_id,
            result=result,
            status='partial',
            memory_dir=memory_dir,
        )
        state['pending_end'] = None
        state['pending_continue'] = {
            'sent_at': now_local().isoformat(),
            **meta,
        }
        save_state(memory_dir, state)
        print(compose_partial_followup(task, result))
        return

    pending_continue = state.get('pending_continue')
    continue_count = parse_pomodoro_count(raw_message) if pending_recent(pending_continue, minutes=180) else None
    if pending_continue and continue_count and ('继续' in raw_message or normalize_message(raw_message) in {'1', '2', '3'}):
        task = pending_continue.get('task', '当前专注事项')
        planned_minutes = continue_count * 25
        _, session_id = append_focus_start(
            task,
            task_class=pending_continue.get('task_class', 'A'),
            role=pending_continue.get('role', '未指定角色'),
            planned_minutes=planned_minutes,
            parent_goal=pending_continue.get('parent_goal', pending_continue.get('linked_week_goal', task)),
            linked_week_goal=pending_continue.get('linked_week_goal', task),
            linked_month_goal=pending_continue.get('linked_month_goal', task),
            high_return=bool(pending_continue.get('high_return', True)),
            memory_dir=memory_dir,
        )
        state['pending_continue'] = None
        save_state(memory_dir, state)
        print(compose_focus_entry(task, planned_minutes, continue_count))
        return
    if pending_continue and any(token in raw_message for token in ('收口', '切换', '休息')):
        state['pending_continue'] = None
        save_state(memory_dir, state)
        print('\n'.join([
            '好，这轮先收口。',
            '- 先用 3-5 分钟保存结果、清空桌面、补一句下一步。',
            '- 如果这件事已经完成，顺手把计划状态改成完成；如果只是阶段收口，再保留下一步动作。',
            '- 如果稍后要继续，再直接回复：`开始` 或 `继续1个`。',
        ]))
        return

    print('未识别到可执行的专注动作。你可以回复：`开始` / `开始专注`，或 `1` / `2` / `3`，也可以回复 `完成：结果` / `中断：原因` / `继续1个` / `收口`。')


if __name__ == '__main__':
    main()
