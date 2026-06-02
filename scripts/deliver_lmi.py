#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_DIR = Path('/Users/woohuaca/Documents/New project/lmi-management-system')
TARGET = 'ou_04eadea6992a4400a8b7b151fdb101ee'
ACCOUNT_ID = '1'

SCRIPTS = {
    'daily': REPO_DIR / 'scripts/generate_lmi_daily.py',
    'daily-review': REPO_DIR / 'scripts/generate_lmi_daily_review.py',
    'weekly-plan': REPO_DIR / 'scripts/generate_lmi_weekly_plan.py',
    'weekly-review': REPO_DIR / 'scripts/generate_lmi_weekly_review.py',
}


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


def send_to_azai(message: str) -> tuple[int, str]:
    result = subprocess.run(
        [
            'openclaw',
            'message',
            'send',
            '--channel',
            'feishu',
            '--account',
            ACCOUNT_ID,
            '--target',
            TARGET,
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
    kind = sys.argv[1] if len(sys.argv) > 1 else 'daily'
    code, output = run_generator(kind)
    print(output)
    if code != 0:
        return code
    send_code, send_details = send_to_azai(output)
    if send_code != 0:
        print(f'\n[delivery failed]\n{send_details}', file=sys.stderr)
        return send_code
    print(f'\n[delivered to azai via Feishu account {ACCOUNT_ID}]', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
