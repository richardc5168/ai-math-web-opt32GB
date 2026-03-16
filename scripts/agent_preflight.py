from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    ROOT / 'README.md',
    ROOT / 'AGENTS.md',
    ROOT / 'logs' / 'change_history.jsonl',
    ROOT / 'logs' / 'lessons_learned.jsonl',
    ROOT / 'reports' / 'latest_iteration_report.md',
]


def tail_jsonl(path: Path, limit: int = 2) -> list[dict]:
    rows = [line.strip() for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    result = []
    for line in rows[-limit:]:
        try:
            result.append(json.loads(line))
        except json.JSONDecodeError:
            result.append({'raw': line})
    return result


def main() -> int:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED if not path.exists()]
    if missing:
      print('PRE-FLIGHT FAILED')
      print('Missing required files:')
      for item in missing:
          print('- ' + item)
      return 1

    print('PRE-FLIGHT OK')
    print('Required files present:')
    for path in REQUIRED:
        print('- ' + str(path.relative_to(ROOT)))

    print('\nRecent change history:')
    for row in tail_jsonl(REQUIRED[2]):
        print('- ' + str(row.get('date', 'unknown')) + ' :: ' + str(row.get('objective', row.get('area', 'n/a'))))

    print('\nRecent lessons:')
    for row in tail_jsonl(REQUIRED[3]):
        print('- ' + str(row.get('area', 'unknown')) + ' :: ' + str(row.get('next_time_instruction', 'n/a')))

    print('\nChecklist:')
    print('- Define acceptance criteria before patching')
    print('- Keep docs and dist mirrored for web changes')
    print('- Update change_history, lessons_learned, latest_iteration_report after meaningful edits')
    print('- Run required validation before declaring success')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
