#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from lmi_execution_support import PRIMARY_MEMORY_DIR, rebuild_inbox_preview


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Preview a rebuilt inbox from capture logs and archive history.')
    parser.add_argument('--memory-dir', default=str(PRIMARY_MEMORY_DIR), help='Override target memory directory.')
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    memory_dir = Path(args.memory_dir).expanduser()
    print(rebuild_inbox_preview(memory_dir), end='')


if __name__ == '__main__':
    main()
