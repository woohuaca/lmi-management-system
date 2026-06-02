#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from lmi_execution_support import PRIMARY_MEMORY_DIR, append_focus_end, append_focus_start


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Start or end an LMI focus session.')
    parser.add_argument('--memory-dir', default=str(PRIMARY_MEMORY_DIR), help='Override target memory directory for testing or custom workspaces.')
    sub = parser.add_subparsers(dest='command', required=True)

    start = sub.add_parser('start', help='Start a new focus session.')
    start.add_argument('--task', required=True)
    start.add_argument('--task-class', default='A', choices=['A', 'B', 'C', 'D'])
    start.add_argument('--role', default='未指定角色')
    start.add_argument('--minutes', type=int, default=50)
    start.add_argument('--week-goal', default='')
    start.add_argument('--month-goal', default='')
    start.add_argument('--high-return', action='store_true')

    end = sub.add_parser('end', help='End the latest open focus session or a specified session.')
    end.add_argument('--session-id', default='')
    end.add_argument('--result', default='')
    end.add_argument('--status', default='completed', choices=['completed', 'interrupted', 'partial'])
    end.add_argument('--interruption-reason', default='')
    end.add_argument('--focus-score', type=int, choices=[1, 2, 3, 4, 5], default=None)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    memory_dir = Path(args.memory_dir).expanduser()
    if args.command == 'start':
        path, session_id = append_focus_start(
            args.task,
            task_class=args.task_class,
            role=args.role,
            planned_minutes=args.minutes,
            linked_week_goal=args.week_goal,
            linked_month_goal=args.month_goal,
            high_return=args.high_return,
            memory_dir=memory_dir,
        )
        print(f'Started focus session: {session_id}')
        print(f'Focus log: {path}')
        return

    path, session_id = append_focus_end(
        session_id=args.session_id or None,
        result=args.result,
        status=args.status,
        interruption_reason=args.interruption_reason,
        focus_score=args.focus_score,
        memory_dir=memory_dir,
    )
    print(f'Ended focus session: {session_id}')
    print(f'Focus log: {path}')


if __name__ == '__main__':
    main()
