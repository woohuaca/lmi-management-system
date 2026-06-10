#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from lmi_execution_support import PRIMARY_MEMORY_DIR, load_json
from lmi_time_commitments import (
    active_weekly_calendar_sync_state_path,
    active_weekly_time_commitment_path,
    save_weekly_calendar_sync_state,
    weekly_calendar_sync_state_path,
    weekly_time_commitment_dir,
)

DEFAULT_TIMEZONE = os.environ.get('LMI_CALENDAR_TIMEZONE', 'Asia/Shanghai')
DEFAULT_FEISHU_IDENTITY = os.environ.get('LMI_FEISHU_IDENTITY', 'user')
DEFAULT_CALENDAR_ID = os.environ.get('LMI_FEISHU_CALENDAR_ID', '')
WEEKDAY_TO_OFFSET = {
    'Mon': 0,
    'Tue': 1,
    'Wed': 2,
    'Thu': 3,
    'Fri': 4,
    'Sat': 5,
    'Sun': 6,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Preview or sync LMI weekly time commitments into Feishu calendar.')
    parser.add_argument('--memory-dir', default=str(PRIMARY_MEMORY_DIR), help='Memory directory that contains weekly time commitments.')
    parser.add_argument('--as', dest='identity', default=DEFAULT_FEISHU_IDENTITY, choices=['user', 'bot'], help='Feishu identity type.')
    parser.add_argument('--calendar-id', default=DEFAULT_CALENDAR_ID, help='Optional calendar ID. If omitted, first create falls back to the primary calendar shortcut.')
    parser.add_argument('--apply', action='store_true', help='Execute create/update calls. Default is preview only.')
    parser.add_argument('--force', action='store_true', help='Force update even when the stored fingerprint is unchanged.')
    parser.add_argument('--json', action='store_true', help='Print the preview/result as JSON.')
    return parser


def iso_datetime(date_str: str, hhmm: str, timezone_name: str) -> str:
    target_date = date.fromisoformat(date_str)
    hour, minute = map(int, hhmm.split(':'))
    value = datetime(target_date.year, target_date.month, target_date.day, hour, minute, tzinfo=ZoneInfo(timezone_name))
    return value.isoformat(timespec='minutes')


def unix_timestamp(date_str: str, hhmm: str, timezone_name: str) -> str:
    target_date = date.fromisoformat(date_str)
    hour, minute = map(int, hhmm.split(':'))
    value = datetime(target_date.year, target_date.month, target_date.day, hour, minute, tzinfo=ZoneInfo(timezone_name))
    return str(int(value.timestamp()))


def load_commitment_payload(memory_dir: Path) -> tuple[dict, Path]:
    active_path = active_weekly_time_commitment_path(memory_dir)
    payload = load_json(active_path, {})
    if isinstance(payload, dict) and payload.get('week_start') and payload.get('week_end'):
        return payload, active_path
    dated_candidates = sorted(weekly_time_commitment_dir(memory_dir).glob('周时间承诺-*.json'))
    if dated_candidates:
        latest_path = dated_candidates[-1]
        payload = load_json(latest_path, {})
        if isinstance(payload, dict) and payload.get('week_start') and payload.get('week_end'):
            return payload, latest_path
    raise FileNotFoundError(f'No weekly time commitment payload found under {memory_dir}')


def fallback_calendar_sync_items(payload: dict) -> list[dict[str, str]]:
    week_start = date.fromisoformat(payload['week_start'])
    source_file = payload.get('source_file', '')
    items: list[dict[str, str]] = []
    for idx, block in enumerate(payload.get('protected_blocks', []), start=1):
        slot = block.get('slot', '')
        day_part, _, time_part = slot.partition(' ')
        start_hhmm, _, end_hhmm = time_part.partition('-')
        if day_part not in WEEKDAY_TO_OFFSET or not start_hhmm or not end_hhmm:
            continue
        block_date = week_start + timedelta(days=WEEKDAY_TO_OFFSET[day_part])
        goal = block.get('goal', '未命名时间块').strip()
        items.append(
            {
                'id': f'weekly-block-{idx}-{block_date.isoformat()}',
                'kind': 'protected_block',
                'slot': slot,
                'date': block_date.isoformat(),
                'start_time': start_hhmm,
                'end_time': end_hhmm,
                'timezone': DEFAULT_TIMEZONE,
                'summary': f'LMI 周时间块：{goal}',
                'description': '\n'.join(
                    [
                        'LMI 周计划自动生成时间承诺',
                        f'关联目标：{goal}',
                        f"块型：{block.get('kind', '关键任务保护块')}",
                        f"安排说明：{block.get('note', '')}",
                        f"缓冲建议：{block.get('buffer', '')}",
                        f'来源文件：{source_file}',
                    ]
                ).strip(),
                'goal': goal,
                'note': block.get('note', ''),
                'buffer': block.get('buffer', ''),
            }
        )
    return items


def normalize_calendar_sync_items(payload: dict) -> list[dict[str, str]]:
    raw_items = payload.get('calendar_sync_items')
    if isinstance(raw_items, list) and raw_items:
        items: list[dict[str, str]] = []
        for idx, item in enumerate(raw_items, start=1):
            if not isinstance(item, dict):
                continue
            normalized = dict(item)
            normalized.setdefault('id', f'calendar-sync-{idx}')
            normalized.setdefault('timezone', DEFAULT_TIMEZONE)
            items.append(normalized)
        if items:
            return items
    return fallback_calendar_sync_items(payload)


def state_template(payload: dict) -> dict:
    return {
        'week_start': payload['week_start'],
        'week_end': payload['week_end'],
        'source_file': payload.get('source_file', ''),
        'default_calendar_id': '',
        'items': {},
    }


def load_existing_sync_state(memory_dir: Path, payload: dict) -> dict:
    week_start = date.fromisoformat(payload['week_start'])
    week_end = date.fromisoformat(payload['week_end'])
    dated_path = weekly_calendar_sync_state_path(week_start, week_end, memory_dir)
    active_path = active_weekly_calendar_sync_state_path(memory_dir)
    for path in (active_path, dated_path):
        state = load_json(path, {})
        if (
            isinstance(state, dict)
            and state.get('week_start') == payload['week_start']
            and state.get('week_end') == payload['week_end']
            and isinstance(state.get('items'), dict)
        ):
            return state
    return state_template(payload)


def stable_item_id(item: dict[str, str]) -> str:
    raw = item.get('id') or f"{item.get('date', '')}|{item.get('start_time', '')}|{item.get('end_time', '')}|{item.get('summary', '')}"
    digest = hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]
    return f'lmi-{digest}'


def item_fingerprint(item: dict[str, str]) -> str:
    payload = {
        'summary': item.get('summary', ''),
        'description': item.get('description', ''),
        'date': item.get('date', ''),
        'start_time': item.get('start_time', ''),
        'end_time': item.get('end_time', ''),
        'timezone': item.get('timezone', DEFAULT_TIMEZONE),
    }
    return hashlib.sha1(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()


def command_error(stdout: str, stderr: str) -> dict | None:
    for chunk in (stdout, stderr):
        stripped = (chunk or '').strip()
        if not stripped:
            continue
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            continue
    return None


def run_cli(command: list[str]) -> tuple[int, dict | None, str]:
    result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=120)
    envelope = command_error(result.stdout, result.stderr)
    raw = (result.stdout or result.stderr or '').strip()
    return result.returncode, envelope, raw


def extract_event(envelope: dict | None) -> dict:
    if not isinstance(envelope, dict):
        return {}
    event = envelope.get('event')
    return event if isinstance(event, dict) else {}


def authorization_hint(envelope: dict | None) -> str:
    if not isinstance(envelope, dict):
        return ''
    error = envelope.get('error')
    if not isinstance(error, dict):
        return ''
    if error.get('type') != 'authorization':
        return ''
    scopes = error.get('missing_scopes') or []
    joined = ' '.join(scopes)
    if joined:
        return f'缺少飞书日历权限：{joined}\n可执行：lark-cli auth login --scope "{joined}" --no-wait --json'
    hint = error.get('hint')
    return hint if isinstance(hint, str) else ''


def create_via_shortcut(item: dict[str, str], *, identity: str, calendar_id: str) -> tuple[int, dict | None, str]:
    start_iso = iso_datetime(item['date'], item['start_time'], item.get('timezone', DEFAULT_TIMEZONE))
    end_iso = iso_datetime(item['date'], item['end_time'], item.get('timezone', DEFAULT_TIMEZONE))
    command = [
        'lark-cli',
        'calendar',
        '+create',
        '--as',
        identity,
        '--summary',
        item['summary'],
        '--start',
        start_iso,
        '--end',
        end_iso,
        '--description',
        item.get('description', ''),
        '--json',
    ]
    if calendar_id:
        command.extend(['--calendar-id', calendar_id])
    return run_cli(command)


def update_via_shortcut(item: dict[str, str], state_item: dict, *, identity: str, calendar_id: str) -> tuple[int, dict | None, str]:
    start_iso = iso_datetime(item['date'], item['start_time'], item.get('timezone', DEFAULT_TIMEZONE))
    end_iso = iso_datetime(item['date'], item['end_time'], item.get('timezone', DEFAULT_TIMEZONE))
    command = [
        'lark-cli',
        'calendar',
        '+update',
        '--as',
        identity,
        '--event-id',
        state_item['event_id'],
        '--summary',
        item['summary'],
        '--start',
        start_iso,
        '--end',
        end_iso,
        '--description',
        item.get('description', ''),
        '--json',
    ]
    if calendar_id:
        command.extend(['--calendar-id', calendar_id])
    return run_cli(command)


def create_via_api(item: dict[str, str], *, identity: str, calendar_id: str, item_id: str) -> tuple[int, dict | None, str]:
    params = {
        'calendar_id': calendar_id,
        'idempotency_key': item_id,
    }
    data = {
        'summary': item['summary'],
        'description': item.get('description', ''),
        'start_time': {
            'timestamp': unix_timestamp(item['date'], item['start_time'], item.get('timezone', DEFAULT_TIMEZONE)),
            'timezone': item.get('timezone', DEFAULT_TIMEZONE),
        },
        'end_time': {
            'timestamp': unix_timestamp(item['date'], item['end_time'], item.get('timezone', DEFAULT_TIMEZONE)),
            'timezone': item.get('timezone', DEFAULT_TIMEZONE),
        },
        'vchat': {'vc_type': 'no_meeting'},
        'free_busy_status': 'busy',
        'reminders': [{'minutes': 10}],
    }
    command = [
        'lark-cli',
        'calendar',
        'events',
        'create',
        '--as',
        identity,
        '--params',
        json.dumps(params, ensure_ascii=False),
        '--data',
        json.dumps(data, ensure_ascii=False),
        '--json',
    ]
    return run_cli(command)


def update_via_api(item: dict[str, str], state_item: dict, *, identity: str, calendar_id: str) -> tuple[int, dict | None, str]:
    params = {
        'calendar_id': calendar_id,
        'event_id': state_item['event_id'],
    }
    data = {
        'summary': item['summary'],
        'description': item.get('description', ''),
        'start_time': {
            'timestamp': unix_timestamp(item['date'], item['start_time'], item.get('timezone', DEFAULT_TIMEZONE)),
            'timezone': item.get('timezone', DEFAULT_TIMEZONE),
        },
        'end_time': {
            'timestamp': unix_timestamp(item['date'], item['end_time'], item.get('timezone', DEFAULT_TIMEZONE)),
            'timezone': item.get('timezone', DEFAULT_TIMEZONE),
        },
        'vchat': {'vc_type': 'no_meeting'},
        'reminders': [{'minutes': 10}],
    }
    command = [
        'lark-cli',
        'calendar',
        'events',
        'patch',
        '--as',
        identity,
        '--params',
        json.dumps(params, ensure_ascii=False),
        '--data',
        json.dumps(data, ensure_ascii=False),
        '--json',
    ]
    return run_cli(command)


def preview_payload(payload: dict, state: dict, items: list[dict[str, str]], *, force: bool) -> dict:
    preview_items: list[dict[str, str]] = []
    summary = {'create': 0, 'update': 0, 'skip': 0}
    for item in items:
        item_id = stable_item_id(item)
        stored = state.get('items', {}).get(item_id, {})
        fingerprint = item_fingerprint(item)
        if stored.get('event_id') and stored.get('fingerprint') == fingerprint and not force:
            action = 'skip'
        elif stored.get('event_id'):
            action = 'update'
        else:
            action = 'create'
        summary[action] += 1
        preview_items.append(
            {
                'id': item_id,
                'action': action,
                'summary': item.get('summary', ''),
                'date': item.get('date', ''),
                'start_time': item.get('start_time', ''),
                'end_time': item.get('end_time', ''),
                'slot': item.get('slot', ''),
                'goal': item.get('goal', ''),
            }
        )
    return {
        'week_start': payload['week_start'],
        'week_end': payload['week_end'],
        'source_file': payload.get('source_file', ''),
        'summary': summary,
        'items': preview_items,
    }


def sync_items(
    payload: dict,
    state: dict,
    items: list[dict[str, str]],
    *,
    memory_dir: Path,
    identity: str,
    calendar_id: str,
    force: bool,
) -> dict:
    result_items: list[dict[str, str]] = []
    result_summary = {'create': 0, 'update': 0, 'skip': 0}
    next_state = state_template(payload)
    next_state['items'] = dict(state.get('items', {}))
    resolved_calendar_id = calendar_id or state.get('default_calendar_id', '')

    for item in items:
        item_id = stable_item_id(item)
        stored = next_state['items'].get(item_id, {})
        fingerprint = item_fingerprint(item)
        had_resolved_calendar_id = bool(resolved_calendar_id or stored.get('calendar_id'))
        if stored.get('event_id') and stored.get('fingerprint') == fingerprint and not force:
            result_summary['skip'] += 1
            result_items.append(
                {
                    'id': item_id,
                    'action': 'skip',
                    'summary': item.get('summary', ''),
                    'event_id': stored.get('event_id', ''),
                }
            )
            continue

        if stored.get('event_id'):
            if resolved_calendar_id or stored.get('calendar_id'):
                code, envelope, raw = update_via_api(
                    item,
                    stored,
                    identity=identity,
                    calendar_id=resolved_calendar_id or stored.get('calendar_id', ''),
                )
            else:
                code, envelope, raw = update_via_shortcut(item, stored, identity=identity, calendar_id='')
            action = 'update'
        else:
            if resolved_calendar_id:
                code, envelope, raw = create_via_api(item, identity=identity, calendar_id=resolved_calendar_id, item_id=item_id)
            else:
                code, envelope, raw = create_via_shortcut(item, identity=identity, calendar_id='')
            action = 'create'

        if code != 0:
            hint = authorization_hint(envelope)
            raise RuntimeError(f'{action} 失败：{item.get("summary", "")}\n{hint or raw}')

        event = extract_event(envelope)
        event_id = event.get('event_id', '')
        event_calendar_id = event.get('organizer_calendar_id') or event.get('calendar_id') or resolved_calendar_id or stored.get('calendar_id', '')
        if not event_id:
            raise RuntimeError(f'{action} 返回缺少 event_id：{item.get("summary", "")}\n{raw}')

        if action == 'create' and not had_resolved_calendar_id and event_calendar_id:
            normalize_state = {'event_id': event_id}
            normalize_code, normalize_envelope, normalize_raw = update_via_api(
                item,
                normalize_state,
                identity=identity,
                calendar_id=event_calendar_id,
            )
            if normalize_code != 0:
                hint = authorization_hint(normalize_envelope)
                raise RuntimeError(f'create 后标准化失败：{item.get("summary", "")}\n{hint or normalize_raw}')
            patched_event = extract_event(normalize_envelope)
            if patched_event:
                event = patched_event

        resolved_calendar_id = event_calendar_id or resolved_calendar_id
        next_state['default_calendar_id'] = resolved_calendar_id
        next_state['items'][item_id] = {
            'event_id': event_id,
            'calendar_id': event_calendar_id,
            'fingerprint': fingerprint,
            'summary': item.get('summary', ''),
            'date': item.get('date', ''),
            'start_time': item.get('start_time', ''),
            'end_time': item.get('end_time', ''),
            'app_link': event.get('app_link', ''),
            'synced_at': datetime.now().astimezone().isoformat(timespec='seconds'),
        }
        result_summary[action] += 1
        result_items.append(
            {
                'id': item_id,
                'action': action,
                'summary': item.get('summary', ''),
                'event_id': event_id,
                'calendar_id': event_calendar_id,
            }
        )

    next_state['source_file'] = payload.get('source_file', '')
    save_weekly_calendar_sync_state(memory_dir, next_state)
    return {
        'week_start': payload['week_start'],
        'week_end': payload['week_end'],
        'source_file': payload.get('source_file', ''),
        'summary': result_summary,
        'items': result_items,
        'default_calendar_id': next_state.get('default_calendar_id', ''),
    }


def render_text(report: dict, *, applied: bool) -> str:
    title = 'LMI 周时间承诺已同步到飞书日历' if applied else 'LMI 周时间承诺飞书日历同步预览'
    lines = [
        title,
        f"周次：{report['week_start']} -> {report['week_end']}",
        f"来源：{report.get('source_file', '') or 'unknown'}",
        f"创建 {report['summary']['create']} 个，更新 {report['summary']['update']} 个，跳过 {report['summary']['skip']} 个",
    ]
    for item in report.get('items', []):
        window = f"{item.get('date', '')} {item.get('start_time', '')}-{item.get('end_time', '')}".strip()
        if item['action'] == 'skip':
            lines.append(f"- [{item['action']}] {item.get('summary', '')} ({item.get('event_id', '')})")
        elif window:
            lines.append(f"- [{item['action']}] {window} -> {item.get('summary', '')}")
        else:
            lines.append(f"- [{item['action']}] {item.get('summary', '')}")
    return '\n'.join(lines)


def main() -> int:
    args = build_parser().parse_args()
    memory_dir = Path(args.memory_dir).expanduser()
    payload, payload_path = load_commitment_payload(memory_dir)
    state = load_existing_sync_state(memory_dir, payload)
    items = normalize_calendar_sync_items(payload)
    if not items:
        empty_report = {
            'week_start': payload['week_start'],
            'week_end': payload['week_end'],
            'source_file': payload.get('source_file', ''),
            'summary': {'create': 0, 'update': 0, 'skip': 0},
            'items': [],
        }
        print(json.dumps(empty_report, ensure_ascii=False, indent=2) if args.json else render_text(empty_report, applied=False))
        return 0

    if args.apply:
        report = sync_items(
            payload,
            state,
            items,
            memory_dir=memory_dir,
            identity=args.identity,
            calendar_id=args.calendar_id,
            force=args.force,
        )
    else:
        report = preview_payload(payload, state, items, force=args.force)

    report['payload_path'] = str(payload_path)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report, applied=args.apply))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
