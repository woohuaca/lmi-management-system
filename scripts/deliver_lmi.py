#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[1]
DEFAULT_TARGET = os.environ.get('LMI_FEISHU_TARGET', '')
DEFAULT_ACCOUNT_ID = os.environ.get('LMI_FEISHU_ACCOUNT', '1')
DEFAULT_OPENCLAW_BIN = os.environ.get('LMI_OPENCLAW_BIN') or shutil.which('openclaw') or 'openclaw'

SCRIPTS = {
    'daily': REPO_DIR / 'scripts/generate_lmi_daily.py',
    'daily-review': REPO_DIR / 'scripts/generate_lmi_daily_review.py',
    'weekly-plan': REPO_DIR / 'scripts/generate_lmi_weekly_plan.py',
    'weekly-review': REPO_DIR / 'scripts/generate_lmi_weekly_review.py',
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Generate and optionally deliver an LMI update through OpenClaw / Feishu.')
    parser.add_argument('kind', nargs='?', default='daily', choices=sorted(SCRIPTS))
    parser.add_argument('--target', default=DEFAULT_TARGET, help='Feishu target. Defaults to LMI_FEISHU_TARGET.')
    parser.add_argument('--account', default=DEFAULT_ACCOUNT_ID, help='Feishu account id. Defaults to LMI_FEISHU_ACCOUNT or 1.')
    parser.add_argument('--openclaw-bin', default=DEFAULT_OPENCLAW_BIN, help='OpenClaw executable path.')
    parser.add_argument('--dry-run', action='store_true', help='Print generated output without sending it.')
    return parser


def run_generator(kind: str) -> tuple[int, str]:
    script = SCRIPTS.get(kind)
    if script is None:
        known = ', '.join(sorted(SCRIPTS))
        return 2, f'Unknown LMI delivery kind: {kind}. Known: {known}'
    result = subprocess.run(
        ['python3', str(script)],
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    output = (result.stdout or '').strip()
    if result.returncode != 0:
        details = (result.stderr or output or 'no error output').strip()
        return result.returncode, f'LMI {kind} generator failed:\n\n{details}'
    if not output:
        return 1, f'LMI {kind} generator produced empty output.'
    return 0, output


def send_to_azai(message: str, *, target: str, account: str, openclaw_bin: str) -> tuple[int, str]:
    if not target:
        return 2, 'Missing Feishu target. Set LMI_FEISHU_TARGET or pass --target.'
    result = subprocess.run(
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
            '--json',
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
    )
    details = (result.stdout or result.stderr or '').strip()
    return result.returncode, details


def main() -> int:
    args = build_parser().parse_args()
    code, output = run_generator(args.kind)
    print(output)
    if code != 0:
        return code
    if args.dry_run:
        return 0
    send_code, send_details = send_to_azai(output, target=args.target, account=args.account, openclaw_bin=args.openclaw_bin)
    if send_code != 0:
        print(f'\n[delivery failed]\n{send_details}', file=sys.stderr)
        return send_code
    print(f'\n[delivered to azai via Feishu account {args.account}]', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
