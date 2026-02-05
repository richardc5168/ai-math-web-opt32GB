"""Multi-seed stability check for the interactive-g5-empire bank.

Goal:
- Catch "random corner" failures by generating banks across many seeds
  and verifying each bank through the same verifier gate.

Design:
- Does NOT overwrite the committed docs/interactive-g5-empire/bank.js
- Writes each generated bank to a temporary file, then runs verifier
  on that temp path (tests both generation + serialization format).

Exit code:
  0 = all seeds OK
  1 = at least one seed failed
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from generate_interactive_g5_empire_bank import build_bank, write_bank_js
from verify_interactive_g5_empire_bank import verify_path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Stability check: interactive-g5-empire (multi-seed)")
    p.add_argument("--count", type=int, default=20, help="How many seeds to test (default: 20)")
    p.add_argument("--start-seed", type=int, default=20260204, help="First seed (default: 20260204)")
    p.add_argument("--total", type=int, default=320, help="Questions per bank (default: 320)")
    args = p.parse_args(argv)

    count = max(1, int(args.count))
    start_seed = int(args.start_seed)
    total = int(args.total)

    failures: list[tuple[int, str]] = []

    with tempfile.TemporaryDirectory(prefix="g5e_stability_") as td:
        tmp_dir = Path(td)

        for i in range(count):
            seed = start_seed + i
            bank = build_bank(target_total=total, seed=seed)
            tmp_path = tmp_dir / f"bank_seed_{seed}.js"
            write_bank_js(tmp_path, bank)

            _, fails = verify_path(tmp_path)
            if fails:
                msg = f"seed={seed}: {len(fails)} issues (first: #{fails[0].idx} id={fails[0].qid}: {fails[0].msg})"
                failures.append((seed, msg))
                continue

            print(f"OK seed={seed} (n={len(bank)})")

    if failures:
        print(f"FAILED: {len(failures)}/{count} seeds had issues")
        for _, msg in failures[:20]:
            print(f"- {msg}")
        if len(failures) > 20:
            print(f"... and {len(failures) - 20} more")
        return 1

    print(f"ALL OK: {count} seeds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
