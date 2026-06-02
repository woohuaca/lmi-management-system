#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from lmi_execution_support import PRIMARY_MEMORY_DIR, append_inbox_item


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Capture a new LMI inbox item.')
    parser.add_argument('raw_text', help='The idea, task, reminder, risk, or insight to capture.')
    parser.add_argument('--kind', default='idea', choices=['idea', 'todo', 'risk', 'question', 'followup', 'insight'])
    parser.add_argument('--role', default='未指定角色')
    parser.add_argument('--horizon', default='weekly', choices=['today', 'weekly', 'monthly', 'later'])
    parser.add_argument('--memory-dir', default=str(PRIMARY_MEMORY_DIR), help='Override target memory directory for testing or custom workspaces.')
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    memory_dir = Path(args.memory_dir).expanduser()
    path, item_id = append_inbox_item(
        args.raw_text,
        kind=args.kind,
        role=args.role,
        horizon=args.horizon,
        memory_dir=memory_dir,
    )
    print(f'Captured inbox item: {item_id}')
    print(f'Inbox file: {path}')


if __name__ == '__main__':
    main()
