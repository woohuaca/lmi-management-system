#!/usr/bin/env python3
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

DEFAULT_PRIMARY_MEMORY_DIR = Path.home() / '.openclaw' / 'workspace-azai' / 'memory'
DEFAULT_FALLBACK_MEMORY_DIR = Path.home() / '.openclaw' / 'workspace-main' / 'memory'
INBOX_PLACEHOLDER = '当前没有待处理 Inbox 项'
INBOX_DECISIONS = {'tomorrow', 'this_week', 'project_fact_candidate', 'discard'}
INBOX_WORKING_TITLE = '# LMI Inbox'
INBOX_CAPTURE_TITLE = '# Inbox Capture Log'
INBOX_ARCHIVE_TITLE = '# Inbox Archive'
WEEKLY_INPUT_TITLE = '# 本周待跟进输入'
PROJECT_FACT_CANDIDATE_TITLE = '# Inbox 项目事实候选'
TOMORROW_CARRY_HEADING = '## 昨日 Inbox 决策承接'
TOMORROW_CARRY_TITLE = '# LMI Tomorrow Inbox Carryover'
OPS_LOG_FILE = 'inbox-ops.jsonl'


def env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


PRIMARY_MEMORY_DIR = Path(os.environ.get('LMI_PRIMARY_MEMORY_DIR', str(DEFAULT_PRIMARY_MEMORY_DIR))).expanduser()
ALLOW_MAIN_MEMORY_FALLBACK = env_flag('LMI_ALLOW_MAIN_MEMORY_FALLBACK', False)
FALLBACK_MEMORY_DIR = (
    Path(os.environ.get('LMI_FALLBACK_MEMORY_DIR', str(DEFAULT_FALLBACK_MEMORY_DIR))).expanduser()
    if ALLOW_MAIN_MEMORY_FALLBACK
    else None
)


def memory_source_label(memory_dir: Path, default_dir: Path, default_label: str, *, missing: bool = False) -> str:
    expanded = memory_dir.expanduser()
    default = default_dir.expanduser()
    try:
        is_default = expanded.resolve() == default.resolve()
    except OSError:
        is_default = expanded == default
    label = default_label if is_default else str(expanded)
    return f'{label} (missing)' if missing else label


def read_text(path: Path | None) -> str:
    if not path:
        return ''
    try:
        return path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return ''



def now_local() -> datetime:
    return datetime.now().astimezone()



def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


@contextmanager
def file_lock(lock_path: Path):
    ensure_dir(lock_path.parent)
    with lock_path.open('a+', encoding='utf-8') as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)



def atomic_write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    tmp_path = path.with_name(f'.{path.name}.tmp-{os.getpid()}')
    with tmp_path.open('w', encoding='utf-8') as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    tmp_path.replace(path)



def reminder_state_path(memory_dir: Path = PRIMARY_MEMORY_DIR) -> Path:
    return memory_dir / '.lmi-focus-reminder-state.json'



def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default



def save_json(path: Path, payload) -> None:
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + '\n')



def clear_json_key(path: Path, key: str) -> None:
    payload = load_json(path, {})
    if isinstance(payload, dict) and key in payload:
        payload.pop(key, None)
        save_json(path, payload)



def inbox_path(memory_dir: Path = PRIMARY_MEMORY_DIR) -> Path:
    return memory_dir / 'inbox.md'



def inbox_lock_path(memory_dir: Path = PRIMARY_MEMORY_DIR) -> Path:
    return memory_dir / '.inbox.lock'



def inbox_capture_dir(memory_dir: Path = PRIMARY_MEMORY_DIR) -> Path:
    return memory_dir / 'inbox-capture'



def inbox_capture_path(target_date: date, memory_dir: Path = PRIMARY_MEMORY_DIR) -> Path:
    return inbox_capture_dir(memory_dir) / f'{target_date.isoformat()}.md'



def inbox_archive_dir(memory_dir: Path = PRIMARY_MEMORY_DIR) -> Path:
    return memory_dir / 'inbox-archive'



def inbox_archive_path(target_date: date, memory_dir: Path = PRIMARY_MEMORY_DIR) -> Path:
    return inbox_archive_dir(memory_dir) / f'{target_date.strftime("%Y-%m")}-inbox-archive.md'



def inbox_operation_log_path(memory_dir: Path = PRIMARY_MEMORY_DIR) -> Path:
    return memory_dir / OPS_LOG_FILE



def weekly_input_path(memory_dir: Path = PRIMARY_MEMORY_DIR) -> Path:
    return memory_dir / '本周待跟进输入.md'



def project_fact_candidate_path(memory_dir: Path = PRIMARY_MEMORY_DIR) -> Path:
    return memory_dir / '项目事实' / 'Inbox-项目事实候选.md'



def focus_log_path(target_date: date, memory_dir: Path = PRIMARY_MEMORY_DIR) -> Path:
    return memory_dir / 'focus-log' / f'{target_date.strftime("%Y-%m")}-focus-log.md'



def ensure_inbox_file(memory_dir: Path = PRIMARY_MEMORY_DIR) -> Path:
    ensure_dir(memory_dir)
    ensure_dir(inbox_capture_dir(memory_dir))
    ensure_dir(inbox_archive_dir(memory_dir))
    ensure_dir(project_fact_candidate_path(memory_dir).parent)
    path = inbox_path(memory_dir)
    if not path.exists():
        atomic_write_text(path, '# LMI Inbox\n\n## Unprocessed\n\n- 当前没有待处理 Inbox 项\n\n## Decided\n')
    return path



def ensure_focus_log_file(target_date: date, memory_dir: Path = PRIMARY_MEMORY_DIR) -> Path:
    log_dir = memory_dir / 'focus-log'
    ensure_dir(log_dir)
    path = focus_log_path(target_date, memory_dir)
    if not path.exists():
        month_label = target_date.strftime('%Y-%m')
        atomic_write_text(path, f'# {month_label} Focus Log\n')
    return path



def _inbox_sections(text: str) -> tuple[list[str], list[str]]:
    current = None
    unprocessed: list[str] = []
    decided: list[str] = []
    for raw in text.splitlines():
        stripped = raw.rstrip()
        if stripped == '## Unprocessed':
            current = 'unprocessed'
            continue
        if stripped == '## Decided':
            current = 'decided'
            continue
        if stripped.startswith('#'):
            continue
        if current == 'unprocessed' and stripped:
            unprocessed.append(stripped)
        elif current == 'decided' and stripped:
            decided.append(stripped)
    return unprocessed, decided


INBOX_TOKENS_RE = re.compile(r'^-\s+(?P<tokens>(?:\[[^\]]*\])+)?\s*(?P<raw_text>.*)$')
INBOX_LEGACY_BULLET_RE = re.compile(r'^- (?P<raw_text>.+)$')



def _parse_token_block(line: str) -> tuple[list[str], str] | None:
    match = INBOX_TOKENS_RE.match(line.strip())
    if not match:
        return None
    tokens_blob = match.group('tokens') or ''
    tokens = re.findall(r'\[([^\]]*)\]', tokens_blob)
    raw_text = (match.group('raw_text') or '').strip()
    return tokens, raw_text



def _normalize_status(value: str, default: str = 'unprocessed') -> str:
    cleaned = value.replace('status=', '').strip().lower()
    if cleaned in {'unprocessed', 'decided', 'captured'}:
        return cleaned
    return default



def parse_inbox_line(line: str, *, section: str = 'unprocessed') -> dict | None:
    parsed = _parse_token_block(line)
    if not parsed:
        return None
    tokens, raw_text = parsed
    if not tokens:
        legacy = INBOX_LEGACY_BULLET_RE.match(line.strip())
        if not legacy:
            return None
        raw_text = legacy.group('raw_text').strip()
        if raw_text.startswith('['):
            return None
        if not raw_text or raw_text == INBOX_PLACEHOLDER:
            return None
        stable_id = hashlib.sha1(raw_text.encode('utf-8')).hexdigest()[:10]
        return {
            'id': f'legacy-{stable_id}',
            'kind': 'idea',
            'role': '未指定角色',
            'horizon': 'weekly',
            'captured_at': 'legacy',
            'status': section,
            'raw_text': raw_text,
            'decision': '',
            'decided_at': '',
            'target': '',
            'source': 'legacy',
        }

    if len(tokens) < 5:
        return None

    item = {
        'id': tokens[0],
        'kind': tokens[1] or 'idea',
        'role': tokens[2] or '未指定角色',
        'horizon': tokens[3] or 'weekly',
        'captured_at': tokens[4] or 'legacy',
        'status': section,
        'raw_text': raw_text,
        'decision': '',
        'decided_at': '',
        'target': '',
        'source': '',
    }
    if len(tokens) >= 6:
        item['status'] = _normalize_status(tokens[5], default=section)
    if len(tokens) >= 7:
        item['decision'] = tokens[6].replace('decision=', '').strip()
    if len(tokens) >= 8:
        item['decided_at'] = tokens[7].replace('decided_at=', '').strip()
    if len(tokens) >= 9:
        item['target'] = tokens[8].replace('target=', '').strip()
    if len(tokens) >= 10:
        item['source'] = tokens[9].replace('source=', '').strip()

    if (
        'YYYY' in item['id']
        or item['role'] in {'角色名', '未指定角色示例'}
        or 'YYYY' in item['captured_at']
        or '在这里记录新的想法' in item['raw_text']
    ):
        return None
    return item



def render_inbox_item(item: dict) -> str:
    base_tokens = [
        item['id'],
        item.get('kind', 'idea') or 'idea',
        item.get('role', '未指定角色') or '未指定角色',
        item.get('horizon', 'weekly') or 'weekly',
        item.get('captured_at', 'legacy') or 'legacy',
        item.get('status', 'unprocessed') or 'unprocessed',
    ]
    if item.get('status') == 'decided':
        base_tokens.extend([
            item.get('decision', ''),
            item.get('decided_at', ''),
            item.get('target', ''),
            item.get('source', ''),
        ])
    token_blob = ''.join(f'[{token}]' for token in base_tokens)
    return f'- {token_blob} {item.get("raw_text", "").strip()}'



def _load_inbox_state(text: str) -> tuple[list[dict], list[dict]]:
    raw_unprocessed, raw_decided = _inbox_sections(text)
    unprocessed = [item for item in (parse_inbox_line(line, section='unprocessed') for line in raw_unprocessed) if item]
    decided = [item for item in (parse_inbox_line(line, section='decided') for line in raw_decided) if item]
    return unprocessed, decided



def render_inbox_document(unprocessed: list[dict], decided: list[dict]) -> str:
    lines = [INBOX_WORKING_TITLE, '', '## Unprocessed', '']
    if unprocessed:
        lines.extend(render_inbox_item(item) for item in unprocessed)
    else:
        lines.append(f'- {INBOX_PLACEHOLDER}')
    lines.extend(['', '## Decided', ''])
    if decided:
        lines.extend(render_inbox_item(item) for item in decided)
    return '\n'.join(lines).rstrip() + '\n'



def _next_sequential_id(existing_ids: list[str], prefix: str) -> str:
    current = 0
    for item_id in existing_ids:
        if not item_id.startswith(prefix):
            continue
        tail = item_id.rsplit('-', 1)[-1]
        if tail.isdigit():
            current = max(current, int(tail))
    return f'{prefix}-{current + 1:03d}'


def migrate_legacy_unprocessed_items(
    items: list[dict],
    *,
    memory_dir: Path = PRIMARY_MEMORY_DIR,
    migrated_at: datetime | None = None,
) -> list[dict]:
    if not items:
        return items
    pivot = migrated_at or now_local()
    migrated: list[dict] = []
    changed = False
    for idx, item in enumerate(items):
        if item.get('captured_at') != 'legacy':
            migrated.append(item)
            continue
        changed = True
        upgraded = {
            **item,
            'captured_at': (pivot + timedelta(seconds=idx)).isoformat(),
            'source': 'legacy-migration',
        }
        append_capture_log_item(upgraded, memory_dir=memory_dir)
        migrated.append(upgraded)
    return migrated if changed else items


def append_inbox_item(
    raw_text: str,
    *,
    kind: str = 'idea',
    role: str = '未指定角色',
    horizon: str = 'weekly',
    memory_dir: Path = PRIMARY_MEMORY_DIR,
    captured_at: datetime | None = None,
) -> tuple[Path, str]:
    captured = captured_at or now_local()
    path = ensure_inbox_file(memory_dir)
    with file_lock(inbox_lock_path(memory_dir)):
        unprocessed, decided = _load_inbox_state(read_text(path))
        unprocessed = migrate_legacy_unprocessed_items(unprocessed, memory_dir=memory_dir, migrated_at=captured)
        existing_ids = [item['id'] for item in unprocessed + decided]
        item_id = _next_sequential_id(existing_ids, f'inbox-{captured.date().isoformat()}')
        item = {
            'id': item_id,
            'kind': kind,
            'role': role,
            'horizon': horizon,
            'captured_at': captured.isoformat(),
            'status': 'unprocessed',
            'raw_text': raw_text.strip(),
            'decision': '',
            'decided_at': '',
            'target': '',
            'source': 'capture',
        }
        append_capture_log_item(item, memory_dir=memory_dir)
        unprocessed.insert(0, item)
        atomic_write_text(path, render_inbox_document(unprocessed, decided))
    append_inbox_operation_log(
        action='capture',
        item_id=item_id,
        source_file=str(path),
        target_file=str(path),
        result='ok',
        memory_dir=memory_dir,
        details={'kind': kind, 'role': role, 'horizon': horizon},
    )
    return path, item_id



def _capture_log_lines(path: Path) -> list[str]:
    text = read_text(path)
    return [line.rstrip() for line in text.splitlines() if line.rstrip()]



def append_capture_log_item(item: dict, *, memory_dir: Path = PRIMARY_MEMORY_DIR) -> Path:
    target_date = datetime.fromisoformat(item['captured_at']).date() if item['captured_at'] != 'legacy' else now_local().date()
    path = inbox_capture_path(target_date, memory_dir)
    ensure_dir(path.parent)
    lock_path = path.with_suffix(path.suffix + '.lock')
    with file_lock(lock_path):
        lines = _capture_log_lines(path)
        if not lines:
            lines = [f'{INBOX_CAPTURE_TITLE} {target_date.isoformat()}']
        lines.append(render_inbox_item({**item, 'status': 'captured'}))
        atomic_write_text(path, '\n'.join(lines).rstrip() + '\n')
    return path



def append_inbox_archive_item(item: dict, *, memory_dir: Path = PRIMARY_MEMORY_DIR) -> Path:
    decided_at = item.get('decided_at') or now_local().isoformat()
    target_date = datetime.fromisoformat(decided_at).date()
    path = inbox_archive_path(target_date, memory_dir)
    ensure_dir(path.parent)
    lock_path = path.with_suffix(path.suffix + '.lock')
    with file_lock(lock_path):
        lines = _capture_log_lines(path)
        if not lines:
            lines = [f'{INBOX_ARCHIVE_TITLE} {target_date.strftime("%Y-%m") }']
        rendered = render_inbox_item({**item, 'status': 'decided'})
        if rendered not in lines:
            lines.append(rendered)
        atomic_write_text(path, '\n'.join(lines).rstrip() + '\n')
    return path



def append_inbox_operation_log(
    *,
    action: str,
    item_id: str,
    source_file: str,
    target_file: str,
    result: str,
    memory_dir: Path = PRIMARY_MEMORY_DIR,
    details: dict | None = None,
) -> Path:
    path = inbox_operation_log_path(memory_dir)
    ensure_dir(path.parent)
    payload = {
        'timestamp': now_local().isoformat(),
        'action': action,
        'item_id': item_id,
        'source_file': source_file,
        'target_file': target_file,
        'result': result,
    }
    if details:
        payload['details'] = details
    lock_path = path.with_suffix(path.suffix + '.lock')
    with file_lock(lock_path):
        existing = read_text(path)
        existing += json.dumps(payload, ensure_ascii=False) + '\n'
        atomic_write_text(path, existing)
    return path



def resolve_inbox_source(
    primary_memory_dir: Path = PRIMARY_MEMORY_DIR,
    fallback_memory_dir: Path | None = FALLBACK_MEMORY_DIR,
) -> tuple[Path | None, str]:
    primary = inbox_path(primary_memory_dir)
    primary_source = memory_source_label(primary_memory_dir, DEFAULT_PRIMARY_MEMORY_DIR, 'workspace-azai/memory')
    if primary.exists():
        return primary, primary_source
    if fallback_memory_dir is not None:
        fallback = inbox_path(fallback_memory_dir)
        fallback_source = memory_source_label(
            fallback_memory_dir,
            DEFAULT_FALLBACK_MEMORY_DIR,
            'workspace-main/memory (fallback)',
        )
        if fallback.exists():
            return fallback, fallback_source
    return primary, memory_source_label(primary_memory_dir, DEFAULT_PRIMARY_MEMORY_DIR, 'workspace-azai/memory', missing=True)



def load_inbox_snapshot(
    limit: int | None = None,
    *,
    primary_memory_dir: Path = PRIMARY_MEMORY_DIR,
    fallback_memory_dir: Path | None = FALLBACK_MEMORY_DIR,
) -> tuple[list[dict], str, str]:
    path, source = resolve_inbox_source(primary_memory_dir, fallback_memory_dir)
    if not path or not path.exists():
        return [], source, 'missing'
    unprocessed, _decided = _load_inbox_state(read_text(path))
    limited = unprocessed[:limit] if limit else unprocessed
    if limited:
        return limited, source, 'connected'
    return [], source, 'empty'



def load_unprocessed_inbox_items(
    limit: int | None = None,
    *,
    primary_memory_dir: Path = PRIMARY_MEMORY_DIR,
    fallback_memory_dir: Path | None = FALLBACK_MEMORY_DIR,
) -> tuple[list[dict], str]:
    items, source, _ = load_inbox_snapshot(limit=limit, primary_memory_dir=primary_memory_dir, fallback_memory_dir=fallback_memory_dir)
    return items, source



def load_all_decided_inbox_items(
    *,
    primary_memory_dir: Path = PRIMARY_MEMORY_DIR,
    fallback_memory_dir: Path | None = FALLBACK_MEMORY_DIR,
) -> tuple[list[dict], str]:
    items: dict[str, dict] = {}
    sources: list[str] = []
    path, source = resolve_inbox_source(primary_memory_dir, fallback_memory_dir)
    if path and path.exists():
        _, decided = _load_inbox_state(read_text(path))
        for item in decided:
            items[item['id']] = item
        sources.append(source)
    source_pairs = [
        (primary_memory_dir, memory_source_label(primary_memory_dir, DEFAULT_PRIMARY_MEMORY_DIR, 'workspace-azai/memory')),
    ]
    if fallback_memory_dir is not None:
        source_pairs.append((
            fallback_memory_dir,
            memory_source_label(fallback_memory_dir, DEFAULT_FALLBACK_MEMORY_DIR, 'workspace-main/memory (fallback)'),
        ))
    for memory_dir, label in source_pairs:
        if memory_dir is None:
            continue
        archive_dir = inbox_archive_dir(memory_dir)
        if not archive_dir.exists():
            continue
        for archive_path in sorted(archive_dir.glob('*.md')):
            for line in read_text(archive_path).splitlines():
                parsed = parse_inbox_line(line, section='decided')
                if parsed:
                    items.setdefault(parsed['id'], parsed)
            sources.append(f'{label}:{archive_path.name}')
    decided_items = sorted(items.values(), key=lambda item: (item.get('decided_at', ''), item['id']), reverse=True)
    return decided_items, '；'.join(sources) if sources else 'no decided inbox items'



def decided_inbox_items_in_range(
    start_date: date,
    end_date: date,
    *,
    primary_memory_dir: Path = PRIMARY_MEMORY_DIR,
    fallback_memory_dir: Path | None = FALLBACK_MEMORY_DIR,
) -> tuple[list[dict], str]:
    decided, source = load_all_decided_inbox_items(primary_memory_dir=primary_memory_dir, fallback_memory_dir=fallback_memory_dir)
    out: list[dict] = []
    for item in decided:
        decided_at = item.get('decided_at', '')
        if not decided_at:
            continue
        try:
            decided_day = datetime.fromisoformat(decided_at).date()
        except ValueError:
            continue
        if start_date <= decided_day <= end_date:
            out.append(item)
    return out, source



def inbox_items_captured_on(target_date: date) -> tuple[list[dict], str]:
    items, source = load_unprocessed_inbox_items(limit=None)
    prefix = target_date.isoformat()
    return [item for item in items if item['captured_at'].startswith(prefix)], source



def _append_bullets_under_heading(path: Path, title: str, heading: str, bullets: list[str]) -> None:
    ensure_dir(path.parent)
    existing_text = read_text(path).strip()
    if not existing_text:
        lines = [title, '', heading, '']
    else:
        lines = existing_text.splitlines()
    if heading not in lines:
        if lines and lines[-1].strip():
            lines.append('')
        lines.extend([heading, ''])
    idx = lines.index(heading)
    insert_at = idx + 1
    while insert_at < len(lines) and not lines[insert_at].startswith('## '):
        insert_at += 1
    current_section = set(line.strip() for line in lines[idx + 1:insert_at] if line.strip().startswith('- '))
    additions = [bullet for bullet in bullets if bullet.strip() and bullet.strip() not in current_section]
    new_lines = lines[:insert_at]
    if new_lines and new_lines[-1].strip():
        new_lines.append('')
    new_lines.extend(additions)
    if insert_at < len(lines) and new_lines and new_lines[-1].strip():
        new_lines.append('')
    new_lines.extend(lines[insert_at:])
    atomic_write_text(path, '\n'.join(new_lines).rstrip() + '\n')



def week_bounds(target_day: date) -> tuple[date, date]:
    monday = target_day - timedelta(days=target_day.weekday())
    friday = monday + timedelta(days=4)
    return monday, friday



def append_tomorrow_carry_items(target_date: date, items: list[dict], *, memory_dir: Path = PRIMARY_MEMORY_DIR) -> Path:
    path = memory_dir / f'{target_date.isoformat()}.md'
    bullets = [f'- {item["raw_text"]}' for item in items]
    lock_path = path.with_suffix(path.suffix + '.lock')
    with file_lock(lock_path):
        _append_bullets_under_heading(path, f'# {target_date.isoformat()}', TOMORROW_CARRY_HEADING, bullets)
    return path



def append_weekly_input_items(decision_date: date, items: list[dict], *, memory_dir: Path = PRIMARY_MEMORY_DIR) -> Path:
    monday, friday = week_bounds(decision_date)
    heading = f'## {monday.isoformat()} ~ {friday.isoformat()}'
    path = weekly_input_path(memory_dir)
    bullets = [f'- [{item["id"]}] {item["raw_text"]}' for item in items]
    lock_path = path.with_suffix(path.suffix + '.lock')
    with file_lock(lock_path):
        _append_bullets_under_heading(path, WEEKLY_INPUT_TITLE, heading, bullets)
    return path



def append_project_fact_candidate_items(decision_date: date, items: list[dict], *, memory_dir: Path = PRIMARY_MEMORY_DIR) -> Path:
    heading = f'## {decision_date.isoformat()}'
    path = project_fact_candidate_path(memory_dir)
    bullets = [f'- [{item["id"]}] {item["raw_text"]}' for item in items]
    lock_path = path.with_suffix(path.suffix + '.lock')
    with file_lock(lock_path):
        _append_bullets_under_heading(path, PROJECT_FACT_CANDIDATE_TITLE, heading, bullets)
    return path



def load_tomorrow_carry_items(
    target_date: date,
    *,
    primary_memory_dir: Path = PRIMARY_MEMORY_DIR,
    fallback_memory_dir: Path | None = FALLBACK_MEMORY_DIR,
) -> tuple[list[str], str]:
    source_pairs = [
        (primary_memory_dir, memory_source_label(primary_memory_dir, DEFAULT_PRIMARY_MEMORY_DIR, 'workspace-azai/memory')),
    ]
    if fallback_memory_dir is not None:
        source_pairs.append((
            fallback_memory_dir,
            memory_source_label(fallback_memory_dir, DEFAULT_FALLBACK_MEMORY_DIR, 'workspace-main/memory (fallback)'),
        ))
    for memory_dir, source in source_pairs:
        if memory_dir is None:
            continue
        path = memory_dir / f'{target_date.isoformat()}.md'
        if not path.exists():
            continue
        lines = read_text(path).splitlines()
        capture = False
        items: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped == TOMORROW_CARRY_HEADING:
                capture = True
                continue
            if capture and stripped.startswith('## '):
                break
            if capture and stripped.startswith('- '):
                value = stripped[2:].strip()
                if value:
                    items.append(value)
        return items, source
    return [], memory_source_label(primary_memory_dir, DEFAULT_PRIMARY_MEMORY_DIR, 'workspace-azai/memory', missing=True) + ' carryover'



def suggest_inbox_decision(item: dict) -> str:
    kind = (item.get('kind') or 'idea').strip().lower()
    horizon = (item.get('horizon') or 'weekly').strip().lower()
    raw_text = (item.get('raw_text') or '').strip()
    if kind == 'insight':
        return 'project_fact_candidate'
    if kind == 'question' and any(word in raw_text for word in ['为什么', '如何', '是否', '判断', '策略']):
        return 'project_fact_candidate'
    if kind in {'todo', 'followup', 'risk'}:
        return 'tomorrow' if horizon in {'today', 'weekly'} else 'this_week'
    if horizon == 'today':
        return 'tomorrow'
    if len(raw_text) <= 4 or raw_text in {'主动推进', '继续跟进', '回头再看'}:
        return 'discard'
    if horizon in {'monthly', 'later'}:
        return 'this_week'
    return 'this_week'



def preview_inbox_cleanup(
    *,
    memory_dir: Path = PRIMARY_MEMORY_DIR,
) -> dict:
    items, source = load_unprocessed_inbox_items(limit=None, primary_memory_dir=memory_dir, fallback_memory_dir=None)
    groups = {decision: [] for decision in INBOX_DECISIONS}
    for item in items:
        groups[suggest_inbox_decision(item)].append(item)
    return {
        'source': source,
        'unprocessed': items,
        'groups': groups,
    }



def apply_inbox_decisions(
    decisions: dict[str, str],
    *,
    memory_dir: Path = PRIMARY_MEMORY_DIR,
    decision_time: datetime | None = None,
    tomorrow_date: date | None = None,
) -> dict:
    when = decision_time or now_local()
    tomorrow = tomorrow_date or (when.date() + timedelta(days=1))
    invalid = {item_id: decision for item_id, decision in decisions.items() if decision not in INBOX_DECISIONS}
    if invalid:
        raise ValueError(f'Unsupported inbox decisions: {invalid}')

    path = ensure_inbox_file(memory_dir)
    with file_lock(inbox_lock_path(memory_dir)):
        unprocessed, decided = _load_inbox_state(read_text(path))
        unprocessed = migrate_legacy_unprocessed_items(unprocessed, memory_dir=memory_dir, migrated_at=when)
        moved_by_decision = {decision: [] for decision in INBOX_DECISIONS}
        new_unprocessed: list[dict] = []
        new_decided: list[dict] = []
        for item in unprocessed:
            decision = decisions.get(item['id'])
            if not decision:
                new_unprocessed.append(item)
                continue
            target = ''
            if decision == 'tomorrow':
                target = f'{tomorrow.isoformat()}.md#昨日 Inbox 决策承接'
            elif decision == 'this_week':
                target = weekly_input_path(memory_dir).name
            elif decision == 'project_fact_candidate':
                target = str(project_fact_candidate_path(memory_dir).relative_to(memory_dir))
            elif decision == 'discard':
                target = '仅记录 / Archive'
            decided_item = {
                **item,
                'status': 'decided',
                'decision': decision,
                'decided_at': when.isoformat(),
                'target': target,
                'source': 'daily-review-inbox-cleanup',
            }
            moved_by_decision[decision].append(decided_item)
            new_decided.append(decided_item)
        decided = new_decided + decided
        atomic_write_text(path, render_inbox_document(new_unprocessed, decided))

    target_paths: dict[str, Path | None] = {}
    if moved_by_decision['tomorrow']:
        target_paths['tomorrow'] = append_tomorrow_carry_items(tomorrow, moved_by_decision['tomorrow'], memory_dir=memory_dir)
    if moved_by_decision['this_week']:
        target_paths['this_week'] = append_weekly_input_items(when.date(), moved_by_decision['this_week'], memory_dir=memory_dir)
    if moved_by_decision['project_fact_candidate']:
        target_paths['project_fact_candidate'] = append_project_fact_candidate_items(when.date(), moved_by_decision['project_fact_candidate'], memory_dir=memory_dir)
    target_paths['discard'] = None

    archive_paths: list[str] = []
    for decision, items in moved_by_decision.items():
        for item in items:
            archive_path = append_inbox_archive_item(item, memory_dir=memory_dir)
            archive_paths.append(str(archive_path))
            append_inbox_operation_log(
                action=f'inbox_{decision}',
                item_id=item['id'],
                source_file=str(path),
                target_file=str(target_paths.get(decision) or archive_path),
                result='ok',
                memory_dir=memory_dir,
                details={'raw_text': item['raw_text'], 'decision': decision},
            )
    return {
        'inbox_path': path,
        'groups': moved_by_decision,
        'target_paths': target_paths,
        'archive_paths': archive_paths,
    }



def rebuild_inbox_preview(memory_dir: Path = PRIMARY_MEMORY_DIR) -> str:
    captured_items: dict[str, dict] = {}
    capture_dir = inbox_capture_dir(memory_dir)
    if capture_dir.exists():
        for path in sorted(capture_dir.glob('*.md')):
            for line in read_text(path).splitlines():
                parsed = parse_inbox_line(line, section='captured')
                if not parsed:
                    continue
                if parsed.get('status') != 'captured':
                    continue
                parsed['status'] = 'unprocessed'
                captured_items[parsed['id']] = parsed
    decided_items, _ = load_all_decided_inbox_items(primary_memory_dir=memory_dir, fallback_memory_dir=None)
    decided_ids = {item['id'] for item in decided_items}
    current_unprocessed, _current_decided = _load_inbox_state(read_text(ensure_inbox_file(memory_dir)))
    for item in current_unprocessed:
        captured_items.setdefault(item['id'], item)
    unprocessed = [item for item_id, item in sorted(captured_items.items()) if item_id not in decided_ids]
    return render_inbox_document(unprocessed, decided_items)



def _append_block_to_day_section(path: Path, section_date: date, block_lines: list[str]) -> None:
    text = read_text(path).rstrip()
    day_heading = f'## {section_date.isoformat()}'
    if not text:
        text = f'# {section_date.strftime("%Y-%m")} Focus Log'
    lines = text.splitlines()
    if day_heading not in lines:
        if lines and lines[-1].strip():
            lines.append('')
        lines.extend([day_heading, ''])
        lines.extend(block_lines)
        atomic_write_text(path, '\n'.join(lines).rstrip() + '\n')
        return

    insert_index = len(lines)
    start_index = lines.index(day_heading)
    for idx in range(start_index + 1, len(lines)):
        if lines[idx].startswith('## '):
            insert_index = idx
            break
    new_lines = lines[:insert_index]
    if new_lines and new_lines[-1].strip():
        new_lines.append('')
    new_lines.extend(block_lines)
    if insert_index < len(lines) and new_lines and new_lines[-1].strip():
        new_lines.append('')
    new_lines.extend(lines[insert_index:])
    atomic_write_text(path, '\n'.join(new_lines).rstrip() + '\n')


FOCUS_START_RE = re.compile(
    r'^- \[(?P<session_id>[^\]]+)\]\[start\] (?P<clock>\d{2}:\d{2}) \| planned (?P<minutes>\d+) min \| (?P<task_class>[A-D]) \| (?P<role>[^|]+) \| (?P<task>.+)$'
)
FOCUS_END_RE = re.compile(
    r'^- \[(?P<session_id>[^\]]+)\]\[end\] (?P<clock>\d{2}:\d{2}) \| (?P<status>[^|]+) \| actual (?P<minutes>\d+) min$'
)



def _parse_focus_entries(text: str) -> list[dict]:
    entries: list[dict] = []
    current_date = ''
    current: dict | None = None
    for raw in text.splitlines():
        stripped = raw.rstrip()
        if stripped.startswith('## '):
            if current:
                entries.append(current)
                current = None
            current_date = stripped[3:].strip()
            continue
        if stripped.startswith('- [focus-'):
            if current:
                entries.append(current)
            start_match = FOCUS_START_RE.match(stripped)
            end_match = FOCUS_END_RE.match(stripped)
            if start_match:
                data = start_match.groupdict()
                current = {
                    'date': current_date,
                    'type': 'start',
                    'session_id': data['session_id'],
                    'clock': data['clock'],
                    'minutes': int(data['minutes']),
                    'task_class': data['task_class'].strip(),
                    'role': data['role'].strip(),
                    'task': data['task'].strip(),
                    'details': {},
                }
            elif end_match:
                data = end_match.groupdict()
                current = {
                    'date': current_date,
                    'type': 'end',
                    'session_id': data['session_id'],
                    'clock': data['clock'],
                    'minutes': int(data['minutes']),
                    'status': data['status'].strip(),
                    'details': {},
                }
            else:
                current = None
            continue
        if current and stripped.startswith('  - '):
            detail = stripped[4:]
            if ': ' in detail:
                key, value = detail.split(': ', 1)
                current['details'][key.strip()] = value.strip()
    if current:
        entries.append(current)
    return entries



def focus_entries_for_date(
    target_date: date,
    *,
    primary_memory_dir: Path = PRIMARY_MEMORY_DIR,
    fallback_memory_dir: Path | None = FALLBACK_MEMORY_DIR,
) -> tuple[list[dict], str]:
    primary = focus_log_path(target_date, primary_memory_dir)
    primary_source = memory_source_label(primary_memory_dir, DEFAULT_PRIMARY_MEMORY_DIR, 'workspace-azai/memory')
    if primary.exists():
        return [entry for entry in _parse_focus_entries(read_text(primary)) if entry.get('date') == target_date.isoformat()], primary_source
    if fallback_memory_dir is not None:
        fallback = focus_log_path(target_date, fallback_memory_dir)
        fallback_source = memory_source_label(
            fallback_memory_dir,
            DEFAULT_FALLBACK_MEMORY_DIR,
            'workspace-main/memory (fallback)',
        )
    else:
        fallback = None
        fallback_source = ''
    if fallback and fallback.exists():
        return [entry for entry in _parse_focus_entries(read_text(fallback)) if entry.get('date') == target_date.isoformat()], fallback_source
    return [], memory_source_label(primary_memory_dir, DEFAULT_PRIMARY_MEMORY_DIR, 'workspace-azai/memory', missing=True)



def append_focus_start(
    task: str,
    *,
    task_class: str = 'A',
    role: str = '未指定角色',
    planned_minutes: int = 50,
    parent_goal: str = '',
    linked_week_goal: str = '',
    linked_month_goal: str = '',
    high_return: bool = False,
    memory_dir: Path = PRIMARY_MEMORY_DIR,
    started_at: datetime | None = None,
) -> tuple[Path, str]:
    started = started_at or now_local()
    path = ensure_focus_log_file(started.date(), memory_dir)
    existing_entries = _parse_focus_entries(read_text(path))
    prefix = f'focus-{started.date().isoformat()}'
    existing_ids = [entry['session_id'] for entry in existing_entries if entry.get('session_id')]
    session_id = _next_sequential_id(existing_ids, prefix)
    block = [
        f'- [{session_id}][start] {started.strftime("%H:%M")} | planned {int(planned_minutes)} min | {task_class.upper()} | {role} | {task.strip()}',
        f'  - started_at: {started.isoformat()}',
        f'  - parent_goal: {parent_goal or linked_week_goal or task.strip()}',
        f'  - linked_week_goal: {linked_week_goal or task.strip()}',
        f'  - linked_month_goal: {linked_month_goal or linked_week_goal or task.strip()}',
        f'  - high_return: {"yes" if high_return else "no"}',
    ]
    _append_block_to_day_section(path, started.date(), block)
    return path, session_id



def _find_latest_open_session(target_date: date, *, memory_dir: Path = PRIMARY_MEMORY_DIR) -> tuple[dict | None, str]:
    entries, source = focus_entries_for_date(target_date, primary_memory_dir=memory_dir, fallback_memory_dir=None)
    starts: dict[str, dict] = {}
    ended_ids: set[str] = set()
    for entry in entries:
        if entry['type'] == 'start':
            starts[entry['session_id']] = entry
        elif entry['type'] == 'end':
            ended_ids.add(entry['session_id'])
    open_starts = [entry for session_id, entry in starts.items() if session_id not in ended_ids]
    if not open_starts:
        return None, source
    open_starts.sort(key=lambda item: item['details'].get('started_at', ''), reverse=True)
    return open_starts[0], source



def append_focus_end(
    *,
    session_id: str | None = None,
    result: str = '',
    status: str = 'completed',
    interruption_reason: str = '',
    focus_score: int | None = None,
    memory_dir: Path = PRIMARY_MEMORY_DIR,
    ended_at: datetime | None = None,
) -> tuple[Path, str]:
    ended = ended_at or now_local()
    start_entry = None
    if session_id:
        entries, _ = focus_entries_for_date(ended.date(), primary_memory_dir=memory_dir, fallback_memory_dir=None)
        for entry in entries:
            if entry.get('type') == 'start' and entry.get('session_id') == session_id:
                start_entry = entry
                break
    else:
        start_entry, _ = _find_latest_open_session(ended.date(), memory_dir=memory_dir)
    if not start_entry:
        raise ValueError('No open focus session found to end.')
    session_id = start_entry['session_id']
    started_at = datetime.fromisoformat(start_entry['details']['started_at'])
    actual_minutes = max(int((ended - started_at).total_seconds() // 60), 1)
    path = ensure_focus_log_file(ended.date(), memory_dir)
    block = [
        f'- [{session_id}][end] {ended.strftime("%H:%M")} | {status} | actual {actual_minutes} min',
        f'  - ended_at: {ended.isoformat()}',
        f'  - result: {result or "待补充本轮产出"}',
        f'  - interruption: {interruption_reason or "none"}',
        f'  - focus_score: {focus_score if focus_score is not None else ""}',
    ]
    _append_block_to_day_section(path, ended.date(), block)
    return path, session_id



def summarize_focus_day(
    target_date: date,
    *,
    primary_memory_dir: Path = PRIMARY_MEMORY_DIR,
    fallback_memory_dir: Path | None = FALLBACK_MEMORY_DIR,
) -> tuple[dict, str]:
    entries, source = focus_entries_for_date(target_date, primary_memory_dir=primary_memory_dir, fallback_memory_dir=fallback_memory_dir)
    starts: dict[str, dict] = {}
    ends: dict[str, dict] = {}
    for entry in entries:
        if entry['type'] == 'start':
            starts[entry['session_id']] = entry
        elif entry['type'] == 'end':
            ends[entry['session_id']] = entry
    sessions: list[dict] = []
    for session_id, start in starts.items():
        end = ends.get(session_id)
        details = start['details']
        end_details = end['details'] if end else {}
        actual_minutes = end['minutes'] if end else 0
        session = {
            'session_id': session_id,
            'task': start['task'],
            'task_class': start['task_class'],
            'role': start['role'],
            'planned_minutes': start['minutes'],
            'actual_minutes': actual_minutes,
            'status': (end['status'] if end else 'open'),
            'result': end_details.get('result', ''),
            'interruption': end_details.get('interruption', ''),
            'focus_score': int(end_details['focus_score']) if end_details.get('focus_score', '').isdigit() else None,
            'high_return': details.get('high_return') == 'yes',
            'linked_week_goal': details.get('linked_week_goal', ''),
            'linked_month_goal': details.get('linked_month_goal', ''),
        }
        sessions.append(session)
    total_minutes = sum(session['actual_minutes'] for session in sessions)
    by_role: dict[str, int] = {}
    by_class: dict[str, int] = {}
    high_return_minutes = 0
    interrupted_sessions = 0
    for session in sessions:
        by_role[session['role']] = by_role.get(session['role'], 0) + session['actual_minutes']
        by_class[session['task_class']] = by_class.get(session['task_class'], 0) + session['actual_minutes']
        if session['high_return']:
            high_return_minutes += session['actual_minutes']
        if session['status'] == 'interrupted' or (session['interruption'] and session['interruption'] != 'none'):
            interrupted_sessions += 1
    best_session = None
    closed_sessions = [session for session in sessions if session['actual_minutes'] > 0]
    if closed_sessions:
        best_session = sorted(
            closed_sessions,
            key=lambda item: ((item['focus_score'] or 0), item['actual_minutes']),
            reverse=True,
        )[0]
    return {
        'sessions': sessions,
        'total_minutes': total_minutes,
        'completed_sessions': sum(1 for session in sessions if session['status'] == 'completed'),
        'open_sessions': sum(1 for session in sessions if session['status'] == 'open'),
        'interrupted_sessions': interrupted_sessions,
        'best_session': best_session,
        'by_role': by_role,
        'by_class': by_class,
        'high_return_minutes': high_return_minutes,
    }, source



def summarize_focus_range(
    start_date: date,
    end_date: date,
    *,
    primary_memory_dir: Path = PRIMARY_MEMORY_DIR,
    fallback_memory_dir: Path | None = FALLBACK_MEMORY_DIR,
) -> tuple[dict, str]:
    cursor = start_date
    combined_sessions: list[dict] = []
    sources: list[str] = []
    while cursor <= end_date:
        day_summary, source = summarize_focus_day(cursor, primary_memory_dir=primary_memory_dir, fallback_memory_dir=fallback_memory_dir)
        combined_sessions.extend(day_summary['sessions'])
        if day_summary['sessions']:
            sources.append(f'{cursor.isoformat()} -> {source}')
        cursor = date.fromordinal(cursor.toordinal() + 1)
    total_minutes = sum(session['actual_minutes'] for session in combined_sessions)
    by_role: dict[str, int] = {}
    by_class: dict[str, int] = {}
    high_return_minutes = 0
    interrupted = 0
    for session in combined_sessions:
        by_role[session['role']] = by_role.get(session['role'], 0) + session['actual_minutes']
        by_class[session['task_class']] = by_class.get(session['task_class'], 0) + session['actual_minutes']
        if session['high_return']:
            high_return_minutes += session['actual_minutes']
        if session['status'] == 'interrupted' or (session['interruption'] and session['interruption'] != 'none'):
            interrupted += 1
    return {
        'sessions': combined_sessions,
        'total_minutes': total_minutes,
        'by_role': by_role,
        'by_class': by_class,
        'high_return_minutes': high_return_minutes,
        'interrupted_sessions': interrupted,
        'sources': sources,
    }, '；'.join(sources) if sources else 'no focus sessions in range'



def open_focus_sessions(
    target_date: date,
    *,
    primary_memory_dir: Path = PRIMARY_MEMORY_DIR,
    fallback_memory_dir: Path | None = FALLBACK_MEMORY_DIR,
) -> tuple[list[dict], str]:
    entries, source = focus_entries_for_date(target_date, primary_memory_dir=primary_memory_dir, fallback_memory_dir=fallback_memory_dir)
    starts: dict[str, dict] = {}
    ended_ids: set[str] = set()
    for entry in entries:
        if entry['type'] == 'start':
            starts[entry['session_id']] = entry
        elif entry['type'] == 'end':
            ended_ids.add(entry['session_id'])
    open_starts = [entry for session_id, entry in starts.items() if session_id not in ended_ids]
    open_starts.sort(key=lambda item: item['details'].get('started_at', ''), reverse=True)
    return open_starts, source
