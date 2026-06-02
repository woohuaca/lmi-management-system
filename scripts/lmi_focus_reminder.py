#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path

from lmi_execution_support import (
    PRIMARY_MEMORY_DIR,
    ensure_dir,
    focus_entries_for_date,
    load_json,
    now_local,
    open_focus_sessions,
    reminder_state_path,
    save_json,
)

DEFAULT_FEISHU_TARGET = 'ou_04eadea6992a4400a8b7b151fdb101ee'
DEFAULT_FEISHU_ACCOUNT = '1'
DEFAULT_OPENCLAW_BIN = (
    shutil.which('openclaw')
    or '/Users/woohuaca/.local/share/fnm/node-versions/v22.22.0/installation/bin/openclaw'
)
REPO_DIR = Path('/Users/woohuaca/Documents/New project/lmi-management-system')
DAILY_GENERATOR = REPO_DIR / 'scripts' / 'generate_lmi_daily.py'


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Send 2-minute LMI task reminders and pomodoro completion reminders.')
    parser.add_argument('--memory-dir', default=str(PRIMARY_MEMORY_DIR))
    parser.add_argument('--target', default=DEFAULT_FEISHU_TARGET)
    parser.add_argument('--account', default=DEFAULT_FEISHU_ACCOUNT)
    parser.add_argument('--openclaw-bin', default=DEFAULT_OPENCLAW_BIN)
    parser.add_argument('--dry-run', action='store_true')
    return parser


def today_daily_file(memory_dir: Path, target_date: date) -> Path:
    return memory_dir / f'{target_date.isoformat()}.md'


def latest_weekly_plan_file(memory_dir: Path) -> Path | None:
    candidates = list(memory_dir.glob('周计划-*.md')) + list(memory_dir.glob('*_weekly_plan.md'))
    candidates = [path for path in candidates if path.is_file()]
    if not candidates:
        return None
    candidates.sort(key=lambda path: (path.stat().st_mtime, path.name))
    return candidates[-1]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return ''


def section_bullets(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    out: list[str] = []
    capture = False
    for line in lines:
        stripped = line.strip()
        if stripped == heading:
            capture = True
            continue
        if capture and stripped.startswith('## '):
            break
        if capture and stripped.startswith('- '):
            out.append(stripped[2:].strip())
    return out


def normalize(text: str) -> str:
    value = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    value = value.replace('→', ' ').replace('->', ' ')
    value = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]+', ' ', value)
    return re.sub(r'\s+', ' ', value).strip().lower()


def strip_focus_block_label(text: str) -> str:
    value = text.strip().replace('**', '').replace('~~', '')
    value = re.sub(r'^🍅\s*', '', value)
    value = re.sub(r'^当前专注块[:：]\s*', '', value)
    value = re.sub(r'^番茄\s*\d+\s*[:：]\s*', '', value, flags=re.IGNORECASE)
    value = re.sub(r'^专注块\s*\d*\s*[:：]?\s*', '', value, flags=re.IGNORECASE)
    value = re.sub(r'（进行中）$', '', value).strip()
    return value


def parse_priority_items(text: str) -> dict[str, dict]:
    mapping: dict[str, dict] = {}
    role = ''
    week_goal = ''
    month_goal = ''
    role_match = re.search(r'- 本周主角色：(.+)', text)
    if role_match:
        role = role_match.group(1).strip()
    week_match = re.search(r'- 本周关键结果：(.+)', text)
    if week_match:
        week_goal = week_match.group(1).strip()
    month_match = re.search(r'- 本月重点目标：(.+)', text)
    if month_match:
        month_goal = month_match.group(1).strip()
    for heading, task_class in [('## A：重要事项', 'A'), ('## B：紧要事项', 'B')]:
        for bullet in section_bullets(text, heading):
            match = re.match(r'([AB]\d+):\s*(.+)', bullet)
            if not match:
                continue
            code = match.group(1)
            task = match.group(2).strip()
            mapping[code] = {
                'code': code,
                'task': task,
                'task_class': task_class,
                'role': role or '未指定角色',
                'linked_week_goal': week_goal,
                'linked_month_goal': month_goal,
                'high_return': task_class == 'A',
            }
    return mapping


SCHEDULE_RE = re.compile(r'^-\s*(\d{2}:\d{2})-(\d{2}:\d{2})\s+(.+)$')


def parse_schedule_entries(text: str) -> list[dict]:
    entries: list[dict] = []
    for bullet in section_bullets(text, '## Schedule'):
        if '✅' in bullet:
            continue
        cleaned = bullet.replace('**', '').replace('~~', '').strip()
        line = f'- {cleaned}'
        match = SCHEDULE_RE.match(line)
        if not match:
            continue
        start, end, desc = match.groups()
        parts = re.split(r'->|→', desc, maxsplit=1)
        label = parts[0].strip()
        task = parts[1].strip() if len(parts) > 1 else desc.strip()
        entries.append({'start': start, 'end': end, 'label': label, 'task': task, 'raw': bullet})
    return entries


def choose_priority_for_schedule(task: str, priority_items: dict[str, dict]) -> dict | None:
    task_norm = normalize(task)
    best = None
    best_score = 0
    for item in priority_items.values():
        item_norm = normalize(item['task'])
        score = 0
        if task_norm and task_norm in item_norm:
            score = len(task_norm)
        elif item_norm and item_norm in task_norm:
            score = len(item_norm)
        else:
            task_tokens = set(task_norm.split())
            item_tokens = set(item_norm.split())
            overlap = task_tokens & item_tokens
            score = len(overlap)
        if score > best_score:
            best_score = score
            best = item
    if best_score > 0:
        return best
    if any(marker in task_norm for marker in ('番茄', '专注块', '深度推进', '重点推进', 'focus')):
        a_items = sorted(
            (item for item in priority_items.values() if item['task_class'] == 'A'),
            key=lambda item: item['code'],
        )
        if a_items:
            return a_items[0]
        fallback_items = sorted(priority_items.values(), key=lambda item: item['code'])
        if fallback_items:
            return fallback_items[0]
    return None


def planned_minutes(item: dict, entry: dict | None = None) -> int:
    if entry:
        start_dt = datetime.strptime(entry['start'], '%H:%M')
        end_dt = datetime.strptime(entry['end'], '%H:%M')
        delta = int((end_dt - start_dt).total_seconds() // 60)
        if 10 <= delta <= 120:
            return delta
    if item['task_class'] == 'A':
        return 50
    return 25


def format_display_task(entry: dict, item: dict) -> str:
    label = entry.get('label', '').strip()
    task = entry.get('task', '').strip()
    if any(marker in normalize(label) for marker in ('番茄', '专注块', 'deep', 'focus', '推进')):
        cleaned_task = strip_focus_block_label(task)
        cleaned_label = strip_focus_block_label(label)
        return cleaned_task or cleaned_label or strip_focus_block_label(item['task'])
    return strip_focus_block_label(task or item['task'])


def load_state(memory_dir: Path) -> dict:
    path = reminder_state_path(memory_dir)
    state = load_json(path, {})
    today_key = now_local().date().isoformat()
    if state.get('date') != today_key:
        state = {
            'date': today_key,
            'prestart_sent': {},
            'pomodoro_end_sent': {},
            'pending_start': None,
            'pending_setup': None,
            'pending_end': None,
            'pending_continue': None,
        }
    state.setdefault('prestart_sent', {})
    state.setdefault('pomodoro_end_sent', {})
    state.setdefault('pending_start', None)
    state.setdefault('pending_setup', None)
    state.setdefault('pending_end', None)
    state.setdefault('pending_continue', None)
    return state


def save_state(memory_dir: Path, state: dict) -> None:
    path = reminder_state_path(memory_dir)
    ensure_dir(path.parent)
    save_json(path, state)


def send_message(message: str, *, target: str, account: str, openclaw_bin: str, dry_run: bool) -> None:
    if dry_run:
        print(message)
        return
    env = os.environ.copy()
    bin_dir = str(Path(openclaw_bin).expanduser().resolve().parent)
    current_path = env.get('PATH', '')
    env['PATH'] = f'{bin_dir}:{current_path}' if current_path else bin_dir
    subprocess.run(
        [
            openclaw_bin,
            'message',
            'send',
            '--channel',
            'feishu',
            '--account',
            account,
            '--target',
            target,
            '--message',
            message,
        ],
        check=True,
        env=env,
    )


def refresh_daily_if_stale(memory_dir: Path) -> bool:
    today_path = today_daily_file(memory_dir, now_local().date())
    weekly_path = latest_weekly_plan_file(memory_dir)
    if not today_path.exists() or not weekly_path:
        return False
    try:
        if weekly_path.stat().st_mtime <= today_path.stat().st_mtime:
            return False
    except FileNotFoundError:
        return False
    result = subprocess.run(
        ['python3', str(DAILY_GENERATOR)],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    return result.returncode == 0


def maybe_send_prestart_reminders(memory_dir: Path, target: str, account: str, openclaw_bin: str, dry_run: bool, state: dict) -> list[str]:
    now = now_local()
    refresh_daily_if_stale(memory_dir)
    text = read_text(today_daily_file(memory_dir, now.date()))
    if not text:
        return []
    for state_key, minutes in (
        ('pending_start', 90),
        ('pending_setup', 90),
        ('pending_end', 180),
        ('pending_continue', 180),
    ):
        pending = state.get(state_key) or {}
        if pending.get('sent_at'):
            try:
                pending_dt = datetime.fromisoformat(pending['sent_at'])
                if (now - pending_dt).total_seconds() <= minutes * 60:
                    return []
            except Exception:
                pass
    open_sessions, _ = open_focus_sessions(now.date(), primary_memory_dir=memory_dir, fallback_memory_dir=None)
    if open_sessions:
        return []
    priority_items = parse_priority_items(text)
    schedule_entries = parse_schedule_entries(text)
    valid_keys: set[str] = set()
    for entry in schedule_entries:
        item = choose_priority_for_schedule(entry['task'], priority_items)
        if item:
            valid_keys.add(f"{now.date().isoformat()}|{entry['start']}|{item['code']}")
    for state_key in ('pending_start', 'pending_setup'):
        pending = state.get(state_key) or {}
        pending_key = pending.get('key')
        if pending_key and pending_key not in valid_keys:
            state[state_key] = None
    sent: list[str] = []
    for entry in schedule_entries:
        start_dt = datetime.combine(now.date(), datetime.strptime(entry['start'], '%H:%M').time(), now.tzinfo)
        delta = (start_dt - now).total_seconds() / 60
        if delta < 0 or delta > 2.1:
            continue
        item = choose_priority_for_schedule(entry['task'], priority_items)
        if not item:
            continue
        key = f"{now.date().isoformat()}|{entry['start']}|{item['code']}"
        if state['prestart_sent'].get(key):
            continue
        minutes = planned_minutes(item, entry)
        display_task = format_display_task(entry, item)
        msg = '\n'.join([
            f"⏰ LMI 关键事项提醒（提前 2 分钟）",
            f"- 时间：{entry['start']}",
            f"- 当前块：{display_task}",
            f"- 归属目标：{item['code']} {item['task']}",
            f"- 建议范围：1-3 个番茄（默认建议 {minutes} 分钟）",
            "- 直接回复这条消息：`开始` 或 `开始专注`。",
            "- 我会先问你这块想用几个番茄，再帮你进入专注环境。",
        ])
        send_message(msg, target=target, account=account, openclaw_bin=openclaw_bin, dry_run=dry_run)
        state['prestart_sent'][key] = now.isoformat()
        state['pending_start'] = {
            'sent_at': now.isoformat(),
            'key': key,
            'display_task': display_task,
            'task': display_task,
            'parent_goal': f"{item['code']} {item['task']}",
            'task_class': item['task_class'],
            'role': item['role'],
            'suggested_minutes': minutes,
            'linked_week_goal': item['linked_week_goal'],
            'linked_month_goal': item['linked_month_goal'],
            'high_return': item['high_return'],
        }
        sent.append(key)
    return sent


def maybe_send_focus_end_reminders(memory_dir: Path, target: str, account: str, openclaw_bin: str, dry_run: bool, state: dict) -> list[str]:
    now = now_local()
    entries, _ = focus_entries_for_date(now.date(), primary_memory_dir=memory_dir, fallback_memory_dir=None)
    starts: dict[str, dict] = {}
    ended_ids: set[str] = set()
    for entry in entries:
        if entry['type'] == 'start':
            starts[entry['session_id']] = entry
        elif entry['type'] == 'end':
            ended_ids.add(entry['session_id'])
    sent: list[str] = []
    for session_id, start in starts.items():
        if session_id in ended_ids:
            continue
        if state['pomodoro_end_sent'].get(session_id):
            continue
        started_at = datetime.fromisoformat(start['details']['started_at'])
        minutes = int(start['minutes'])
        due = started_at + timedelta(minutes=minutes)
        if now < due:
            continue
        msg = '\n'.join([
            "🍅 LMI 番茄时间到",
            f"- 事项：{start['task']}",
            f"- 计划时长：{minutes} 分钟",
            "- 直接回复这条消息：`完成：结果` / `中断：原因` / `继续1个` / `继续2个` / `收口`。",
            "- 先用一句话收成果，再决定继续还是切换，不急着马上冲下一轮。",
        ])
        send_message(msg, target=target, account=account, openclaw_bin=openclaw_bin, dry_run=dry_run)
        state['pomodoro_end_sent'][session_id] = now.isoformat()
        state['pending_start'] = None
        state['pending_setup'] = None
        state['pending_end'] = {
            'sent_at': now.isoformat(),
            'session_id': session_id,
            'task': start['task'],
            'minutes': minutes,
        }
        sent.append(session_id)
    return sent


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    memory_dir = Path(args.memory_dir).expanduser()
    state = load_state(memory_dir)
    pre = maybe_send_prestart_reminders(memory_dir, args.target, args.account, args.openclaw_bin, args.dry_run, state)
    end = maybe_send_focus_end_reminders(memory_dir, args.target, args.account, args.openclaw_bin, args.dry_run, state)
    if not args.dry_run:
        save_state(memory_dir, state)
    print(json.dumps({'prestart_sent': pre, 'pomodoro_end_sent': end}, ensure_ascii=False))


if __name__ == '__main__':
    main()
