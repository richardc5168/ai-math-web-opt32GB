from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
import yaml
from bs4 import BeautifulSoup


@dataclass(frozen=True)
class SourceSpec:
    url: str
    grade: str
    topic_tags: list[str]


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _compact(text: str) -> str:
    return " ".join((text or "").split())


def _clip(text: str, limit: int) -> str:
    s = _compact(text)
    return s if len(s) <= limit else s[:limit].rstrip() + "…"


def _load_sources(path: Path) -> list[SourceSpec]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    sources = raw.get("sources") if isinstance(raw, dict) else None
    if not isinstance(sources, list) or not sources:
        raise SystemExit(f"No sources in {path}")

    out: list[SourceSpec] = []
    for idx, item in enumerate(sources, start=1):
        if not isinstance(item, dict):
            raise SystemExit(f"Invalid source entry #{idx}: mapping required")
        url = str(item.get("url") or "").strip()
        grade = str(item.get("grade") or "").strip()
        topic_tags = [str(x).strip() for x in (item.get("topic_tags") or []) if str(x).strip()]
        if not url:
            raise SystemExit(f"Invalid source entry #{idx}: url required")
        if grade not in ("5", "6"):
            raise SystemExit(f"Invalid source entry #{idx}: grade must be 5/6")
        if not topic_tags:
            raise SystemExit(f"Invalid source entry #{idx}: topic_tags required")
        out.append(SourceSpec(url=url, grade=grade, topic_tags=topic_tags))
    return out


def _fetch(url: str) -> tuple[str, str]:
    resp = requests.get(url, timeout=20, headers={"User-Agent": "ai-math-web/fraction-decimal-ingest"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    title = _compact(soup.title.get_text(" ", strip=True) if soup.title else url) or url
    body = _compact(soup.get_text(" ", strip=True))
    return title, body


def _note(spec: SourceSpec, note_id: str, title: str, body: str, quote_text: str) -> dict[str, Any]:
    summary = (
        "本筆記聚焦小五/小六分數與小數應用題：先辨識題型（折扣、平均分配、單位換算、路程時間），"
        "再用分數/小數列式，最後檢查單位與合理性。"
    )
    return {
        "note_id": note_id,
        "source_url": spec.url,
        "title": title,
        "retrieved_at": _now_iso(),
        "grade": spec.grade,
        "topic_tags": spec.topic_tags,
        "summary": _clip(summary, 220),
        "key_steps": [
            "先圈出整體量、部分量、比率與單位。",
            "判斷題型：折扣/比例用乘法，平均分配用除法，路程時間先統一時間單位。",
            "列式後先估算，再精算。",
            "回代檢查：答案量級與單位要符合題意。",
        ],
        "common_mistakes": [
            "把折扣率直接當付款率。",
            "平均分配題把分母設錯（人數/份數混淆）。",
            "單位換算漏做（公升與毫升混用）。",
            "路程時間題沒先把分鐘換成小時。",
            "分數/小數算完未做合理性檢查。",
        ],
        "example_patterns": [
            "購物折扣：現價 = 原價 × (1 - 折扣率)。",
            "平均分配：每份 = 總量 ÷ 份數。",
            "單位換算：先同單位再運算。",
            "路程時間：距離 = 速度 × 時間。",
        ],
        "quotes": [
            {
                "text": _clip(quote_text, 25),
                "citation": spec.url,
            }
        ],
        "trace_excerpt": _clip(body, 180),
    }


def _mock_note(spec: SourceSpec, note_id: str) -> dict[str, Any]:
    return _note(
        spec,
        note_id,
        f"(mock) {spec.url}",
        "offline generated summary",
        "先看單位再列式",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", default="data/external_web_notes/fraction_decimal_sources.yaml")
    parser.add_argument("--out", default="data/external_web_notes/fraction_decimal_notes.jsonl")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)

    source_path = Path(args.sources)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    specs = _load_sources(source_path)
    lines: list[str] = []

    for idx, spec in enumerate(specs, start=1):
        note_id = f"fdnote_{idx:04d}"
        try:
            if args.offline:
                note = _mock_note(spec, note_id)
            else:
                title, body = _fetch(spec.url)
                note = _note(spec, note_id, title, body, body)
        except Exception as error:
            note = _mock_note(spec, note_id)
            note["summary"] = _clip(f"collector_fallback: {type(error).__name__}", 220)
        lines.append(json.dumps(note, ensure_ascii=False))

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_path} ({len(lines)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
