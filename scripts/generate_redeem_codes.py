"""Generate redeem codes for static (frontend-only) commercial packs.

Outputs:
- A JSON file with SHA-256 hashes + policy metadata (safe to commit)
- A CSV file with plaintext codes for distribution (MUST NOT be committed)

Security note:
This is lightweight gating for MVP. Without a server, expiry/max-uses can only be
enforced on-device (via localStorage). Do NOT treat this as DRM.

Example:
  python scripts/generate_redeem_codes.py \
    --pack-id commercial.pack1.g5.fraction_sprint.tw.v1 \
    --prefix CP1 \
    --count 100 \
        --valid-days 15 \
    --expires 2026-03-31 \
    --max-uses 1 \
    --out-json docs/commercial-pack1-fraction-sprint/redeem_codes.json \
    --out-json-dist dist_ai_math_web_pages/docs/commercial-pack1-fraction-sprint/redeem_codes.json \
    --out-csv issued_codes/CP1_fraction_sprint_2026-02-07.csv
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import secrets
from pathlib import Path


ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def parse_expires(expires: str | None) -> str | None:
    if not expires:
        return None
    # Accept YYYY-MM-DD; convert to UTC end-of-day.
    d = dt.date.fromisoformat(expires)
    end = dt.datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=dt.timezone.utc)
    return end.isoformat().replace("+00:00", "Z")


def gen_code(prefix: str, groups: int, group_len: int) -> str:
    parts = []
    for _ in range(groups):
        parts.append("".join(secrets.choice(ALPHABET) for _ in range(group_len)))
    if prefix:
        return f"{prefix}-" + "-".join(parts)
    return "-".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack-id", required=True)
    ap.add_argument("--prefix", default="")
    ap.add_argument("--count", type=int, default=100)
    ap.add_argument("--valid-days", type=int, default=None, help="Days from first redemption (per device)")
    ap.add_argument("--expires", default=None, help="YYYY-MM-DD (UTC end-of-day)")
    ap.add_argument("--max-uses", type=int, default=1)
    ap.add_argument("--groups", type=int, default=3, help="Groups of code segments")
    ap.add_argument("--group-len", type=int, default=5)
    ap.add_argument("--label", default="batch")
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-json-dist", default=None)
    ap.add_argument("--out-csv", required=True)
    args = ap.parse_args()

    if args.count <= 0:
        raise SystemExit("--count must be > 0")
    if args.max_uses <= 0:
        raise SystemExit("--max-uses must be > 0")

    expires_utc = parse_expires(args.expires)
    valid_days = args.valid_days
    if valid_days is not None and valid_days <= 0:
        raise SystemExit("--valid-days must be > 0 (or omit it)")

    codes: list[str] = []
    seen = set()
    while len(codes) < args.count:
        c = gen_code(args.prefix, args.groups, args.group_len)
        if c in seen:
            continue
        seen.add(c)
        codes.append(c)

    now = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")

    json_obj = {
        "schema": "aimath.redeem_codes.v1",
        "pack_id": args.pack_id,
        "generated_at_utc": now,
        "policy": {
            "expires_utc": expires_utc,
            "valid_days": valid_days,
            "max_uses_per_device": args.max_uses,
            "label": args.label,
        },
        "codes": [
            {
                "code_hash": sha256_hex(c),
                "expires_utc": expires_utc,
                "valid_days": valid_days,
                "max_uses_per_device": args.max_uses,
                "label": args.label,
            }
            for c in codes
        ],
    }

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(json_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.out_json_dist:
        out_json_dist = Path(args.out_json_dist)
        out_json_dist.parent.mkdir(parents=True, exist_ok=True)
        out_json_dist.write_text(json.dumps(json_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out_csv = Path(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pack_id", "code", "valid_days", "expires_utc", "max_uses_per_device", "label"]) 
        for c in codes:
            w.writerow([args.pack_id, c, valid_days if valid_days is not None else "", expires_utc or "", args.max_uses, args.label])

    print(f"OK: wrote JSON: {out_json}")
    if args.out_json_dist:
        print(f"OK: wrote JSON (dist): {args.out_json_dist}")
    print(f"OK: wrote CSV (DO NOT COMMIT): {out_csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
