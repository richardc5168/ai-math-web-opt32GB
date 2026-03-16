from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRITEBACK = {
    'logs/change_history.jsonl',
    'logs/lessons_learned.jsonl',
    'reports/latest_iteration_report.md',
}


def git_changed_files() -> list[str]:
    cmd = ['git', '-c', 'core.pager=cat', 'diff', '--name-only', 'HEAD']
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or 'git diff failed')
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def docs_path_to_dist(path: str) -> str:
    if path.startswith('docs/'):
        return 'dist_ai_math_web_pages/' + path
    return path


def main() -> int:
    changed = git_changed_files()
    changed_set = set(changed)
    web_changes = [path for path in changed if path.startswith('docs/')]
    meaningful = [path for path in changed if path.startswith('docs/') or path.startswith('scripts/') or path.startswith('tests_js/') or path.startswith('tests/specs/')]

    if meaningful and not WRITEBACK.issubset(changed_set):
        print('POST-FLIGHT FAILED')
        print('Missing writeback files:')
        for path in sorted(WRITEBACK - changed_set):
            print('- ' + path)
        return 1

    missing_mirror = []
    for path in web_changes:
        mirror = docs_path_to_dist(path)
        if mirror not in changed_set and Path(ROOT / mirror).exists():
            missing_mirror.append((path, mirror))

    if missing_mirror:
        print('POST-FLIGHT FAILED')
        print('Missing docs/dist mirror updates:')
        for src, dist in missing_mirror:
            print('- ' + src + ' -> ' + dist)
        return 1

    print('POST-FLIGHT OK')
    print('Changed files checked: ' + str(len(changed)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
