#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path

from lmi_execution_support import (
    INBOX_DECISIONS,
    PRIMARY_MEMORY_DIR,
    apply_inbox_decisions,
    preview_inbox_cleanup,
)

DECISION_LABELS = {
    'tomorrow': '进明天',
    'this_week': '留在本周',
    'project_fact_candidate': '转项目事实候选',
    'discard': '丢弃 / 仅记录',
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Preview or apply LMI Inbox cleanup decisions.')
    parser.add_argument('--memory-dir', default=str(PRIMARY_MEMORY_DIR), help='Override target memory directory.')
    parser.add_argument('--tomorrow-date', default='', help='Override tomorrow carry target date (YYYY-MM-DD).')
    parser.add_argument(
        '--decision',
        action='append',
        default=[],
        help='Apply a decision in ITEM_ID=tomorrow|this_week|project_fact_candidate|discard format. Repeat for multiple items.',
    )
    return parser


def parse_decisions(values: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for value in values:
        if '=' not in value:
            raise ValueError(f'Invalid --decision format: {value}')
        item_id, decision = value.split('=', 1)
        item_id = item_id.strip()
        decision = decision.strip()
        if not item_id or decision not in INBOX_DECISIONS:
            raise ValueError(f'Unsupported decision: {value}')
        out[item_id] = decision
    return out


def render_groups(groups: dict[str, list[dict]], *, heading: str) -> str:
    lines = [heading, '']
    for decision in ['tomorrow', 'this_week', 'project_fact_candidate', 'discard']:
        lines.append(f'### {DECISION_LABELS[decision]}')
        items = groups.get(decision) or []
        if items:
            for item in items:
                lines.append(f'- [{item["id"]}] {item["raw_text"]}')
        else:
            lines.append('- 当前无事项')
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    memory_dir = Path(args.memory_dir).expanduser()
    decisions = parse_decisions(args.decision)
    tomorrow = date.fromisoformat(args.tomorrow_date) if args.tomorrow_date else None

    if not decisions:
        preview = preview_inbox_cleanup(memory_dir=memory_dir)
        print(render_groups(preview['groups'], heading='## Inbox 清理建议'), end='')
        print(f'来源：{preview["source"]}')
        return

    summary = apply_inbox_decisions(decisions, memory_dir=memory_dir, tomorrow_date=tomorrow, decision_time=datetime.now().astimezone())
    print(render_groups(summary['groups'], heading='## Inbox 清理结果'), end='')
    print(f'Inbox file: {summary["inbox_path"]}')
    for decision, path in summary['target_paths'].items():
        if path:
            print(f'{DECISION_LABELS[decision]} -> {path}')


if __name__ == '__main__':
    main()
