#!/usr/bin/env python3
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from lmi_execution_support import (
    FALLBACK_MEMORY_DIR,
    PRIMARY_MEMORY_DIR,
    ensure_dir,
    load_json,
    memory_source_label,
    save_json,
)


def week_bounds(target_date: date) -> tuple[date, date]:
    monday = target_date - timedelta(days=target_date.weekday())
    friday = monday + timedelta(days=4)
    return monday, friday


def weekly_time_commitment_dir(memory_dir: Path = PRIMARY_MEMORY_DIR) -> Path:
    return memory_dir / '时间承诺'


def weekly_time_commitment_path(week_start: date, week_end: date, memory_dir: Path = PRIMARY_MEMORY_DIR) -> Path:
    return weekly_time_commitment_dir(memory_dir) / f'周时间承诺-{week_start.isoformat()}-{week_end.strftime("%d")}.json'


def active_weekly_time_commitment_path(memory_dir: Path = PRIMARY_MEMORY_DIR) -> Path:
    return memory_dir / '.lmi-active-weekly-time-commitments.json'


def weekly_calendar_sync_state_path(week_start: date, week_end: date, memory_dir: Path = PRIMARY_MEMORY_DIR) -> Path:
    return weekly_time_commitment_dir(memory_dir) / f'周时间承诺同步-{week_start.isoformat()}-{week_end.strftime("%d")}.json'


def active_weekly_calendar_sync_state_path(memory_dir: Path = PRIMARY_MEMORY_DIR) -> Path:
    return memory_dir / '.lmi-active-weekly-calendar-sync.json'


def build_weekly_time_commitment_payload(
    *,
    week_start: date,
    week_end: date,
    title: str,
    source_file: str,
    protected_blocks: list[dict[str, str]],
    calendar_commitments: list[str],
    calendar_sync_items: list[dict] | None = None,
) -> dict:
    payload = {
        'week_start': week_start.isoformat(),
        'week_end': week_end.isoformat(),
        'title': title,
        'source_file': source_file,
        'protected_blocks': protected_blocks,
        'calendar_commitments': calendar_commitments,
    }
    if calendar_sync_items is not None:
        payload['calendar_sync_items'] = calendar_sync_items
    return payload


def save_weekly_time_commitments(memory_dir: Path, payload: dict) -> tuple[Path, Path]:
    week_start = date.fromisoformat(payload['week_start'])
    week_end = date.fromisoformat(payload['week_end'])
    ensure_dir(weekly_time_commitment_dir(memory_dir))
    dated_path = weekly_time_commitment_path(week_start, week_end, memory_dir)
    active_path = active_weekly_time_commitment_path(memory_dir)
    save_json(dated_path, payload)
    save_json(active_path, payload)
    return dated_path, active_path


def save_weekly_calendar_sync_state(memory_dir: Path, payload: dict) -> tuple[Path, Path]:
    week_start = date.fromisoformat(payload['week_start'])
    week_end = date.fromisoformat(payload['week_end'])
    ensure_dir(weekly_time_commitment_dir(memory_dir))
    dated_path = weekly_calendar_sync_state_path(week_start, week_end, memory_dir)
    active_path = active_weekly_calendar_sync_state_path(memory_dir)
    save_json(dated_path, payload)
    save_json(active_path, payload)
    return dated_path, active_path


def load_weekly_time_commitments(
    target_date: date,
    *,
    primary_memory_dir: Path = PRIMARY_MEMORY_DIR,
    fallback_memory_dir: Path | None = FALLBACK_MEMORY_DIR,
) -> tuple[dict, str]:
    week_start, week_end = week_bounds(target_date)

    def _try_load(memory_dir: Path, label: str) -> tuple[dict, str] | None:
        active_path = active_weekly_time_commitment_path(memory_dir)
        payload = load_json(active_path, {})
        if isinstance(payload, dict) and payload.get('week_start') == week_start.isoformat() and payload.get('week_end') == week_end.isoformat():
            return payload, label
        dated_path = weekly_time_commitment_path(week_start, week_end, memory_dir)
        payload = load_json(dated_path, {})
        if isinstance(payload, dict) and payload.get('week_start') == week_start.isoformat() and payload.get('week_end') == week_end.isoformat():
            return payload, label
        return None

    primary_label = memory_source_label(primary_memory_dir, PRIMARY_MEMORY_DIR, 'workspace-azai/memory')
    primary_result = _try_load(primary_memory_dir, primary_label)
    if primary_result is not None:
        return primary_result

    if fallback_memory_dir is not None:
        fallback_label = memory_source_label(fallback_memory_dir, FALLBACK_MEMORY_DIR, 'workspace-main/memory')
        fallback_result = _try_load(fallback_memory_dir, fallback_label)
        if fallback_result is not None:
            return fallback_result

    return {}, 'weekly time commitments missing'
