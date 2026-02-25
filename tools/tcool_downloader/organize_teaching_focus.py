#!/usr/bin/env python3
"""
Pair tcool question/answer files from downloads/manifest.json and
build a teaching-friendly concept index.

Output:
  - downloads/paired_manifest.json
  - downloads/teaching_focus.json
  - downloads/teaching_focus.md
    - downloads/new_type_hint_seeds.json

Notes:
  - No anti-bot/captcha logic.
  - Works offline after files are downloaded.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
DOWNLOADS = ROOT / "downloads"
MANIFEST_PATH = DOWNLOADS / "manifest.json"
PAIRED_PATH = DOWNLOADS / "paired_manifest.json"
TEACHING_JSON = DOWNLOADS / "teaching_focus.json"
TEACHING_MD = DOWNLOADS / "teaching_focus.md"
NEW_TYPE_HINT_SEEDS = DOWNLOADS / "new_type_hint_seeds.json"


@dataclass
class PairItem:
    exam_id: str
    question_file: Optional[str]
    answer_file: Optional[str]
    question_url: Optional[str]
    answer_url: Optional[str]
    source_pages: List[str]
    downloaded_at: str
    status: str


def load_manifest() -> List[Dict[str, Any]]:
    if not MANIFEST_PATH.exists():
        MANIFEST_PATH.write_text("[]", encoding="utf-8")
        return []
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("manifest.json must be an array")
    return data


def extract_exam_key(file_url: str, filename: str) -> Tuple[str, str]:
    """
    Returns (kind, exam_id)
      kind: 'q' | 'a' | 'u'
    """
    raw = f"{file_url or ''} {filename or ''}"

    m = re.search(r"/d/(q|a)/([^/?#]+)", str(file_url or ""), re.IGNORECASE)
    if m:
        kind = m.group(1).lower()
        exam_id = m.group(2)
        exam_id = re.sub(r"\.pdf$", "", exam_id, flags=re.IGNORECASE)
        return kind, exam_id

    m2 = re.search(r"([^\\/]+)\.pdf$", str(filename or ""), re.IGNORECASE)
    if m2:
        return "u", m2.group(1)

    fallback = re.sub(r"\W+", "_", raw).strip("_")[:80] or "unknown"
    return "u", fallback


def pair_manifest(items: List[Dict[str, Any]]) -> List[PairItem]:
    bucket: Dict[str, Dict[str, Any]] = {}

    for it in items:
        item_status = str(it.get("status") or "")
        file_url = str(it.get("file_url") or "")
        filename = str(it.get("filename") or "")
        source_page = str(it.get("source_page") or "")
        downloaded_at = str(it.get("downloaded_at") or "")

        if not file_url and not filename:
            continue

        explicit_exam_id = str(it.get("exam_id") or "").strip()
        paper_type = str(it.get("paper_type") or "").strip().lower()

        kind, exam_id = extract_exam_key(file_url, filename)
        if explicit_exam_id:
            exam_id = explicit_exam_id
            if paper_type == "question":
                kind = "q"
            elif paper_type == "answer":
                kind = "a"
        b = bucket.setdefault(
            exam_id,
            {
                "exam_id": exam_id,
                "question_file": None,
                "answer_file": None,
                "question_url": None,
                "answer_url": None,
                "source_pages": set(),
                "downloaded_at": downloaded_at,
                "any_success": False,
            },
        )

        if downloaded_at and downloaded_at > b["downloaded_at"]:
            b["downloaded_at"] = downloaded_at

        if source_page:
            b["source_pages"].add(source_page)

        if item_status == "success":
            b["any_success"] = True

        if kind == "q":
            if item_status == "success" and filename:
                b["question_file"] = filename
            b["question_url"] = file_url
        elif kind == "a":
            if item_status == "success" and filename:
                b["answer_file"] = filename
            b["answer_url"] = file_url
        else:
            # unknown: try infer from filename/text
            low = (filename + " " + file_url).lower()
            if "/d/q/" in low or "題目" in filename:
                if item_status == "success" and filename:
                    b["question_file"] = filename
                b["question_url"] = file_url
            elif "/d/a/" in low or "答案" in filename:
                if item_status == "success" and filename:
                    b["answer_file"] = filename
                b["answer_url"] = file_url

    out: List[PairItem] = []
    for _, b in sorted(bucket.items(), key=lambda x: x[0]):
        has_q = bool(b["question_file"])
        has_a = bool(b["answer_file"])
        if has_q and has_a:
            status = "paired"
        elif has_q:
            status = "question_only"
        elif has_a:
            status = "answer_only"
        elif b.get("question_url") and b.get("answer_url"):
            status = "browse_only_pair"
        elif b.get("question_url"):
            status = "browse_only_question"
        elif b.get("answer_url"):
            status = "browse_only_answer"
        else:
            status = "unknown"
        out.append(
            PairItem(
                exam_id=b["exam_id"],
                question_file=b["question_file"],
                answer_file=b["answer_file"],
                question_url=b["question_url"],
                answer_url=b["answer_url"],
                source_pages=sorted(b["source_pages"]),
                downloaded_at=b["downloaded_at"] or "",
                status=status,
            )
        )
    return out


def extract_pdf_text(pdf_path: Path, max_pages: int = 2) -> str:
    try:
        import pypdf  # type: ignore
    except Exception:
        return ""

    if not pdf_path.exists():
        return ""

    try:
        reader = pypdf.PdfReader(str(pdf_path))
        texts: List[str] = []
        for page in reader.pages[:max_pages]:
            txt = page.extract_text() or ""
            if txt:
                texts.append(txt)
        return "\n".join(texts)
    except Exception:
        return ""


CONCEPT_RULES: List[Tuple[str, List[str], List[str]]] = [
    (
        "分數乘除與分數應用",
        ["分數", "約分", "通分", "幾分之幾", "乘", "除", "剩下的"],
        [
            "先判斷基準量（是全部，還是剩下的）。",
            "把文字轉成算式：分數的分數通常用乘法。",
            "最後做約分與合理性檢查。",
        ],
    ),
    (
        "小數與位值",
        ["小數", "十分位", "百分位", "千分位", "位值", "0."],
        [
            "先對齊位值再比較或運算。",
            "強化位值表與數字組成概念。",
            "用估算檢查小數乘除結果合理性。",
        ],
    ),
    (
        "面積與單位換算",
        ["面積", "平方公尺", "平方公里", "公畝", "公頃"],
        [
            "先統一面積單位再比較或相減。",
            "建立公頃、公畝、平方公尺換算表。",
            "強調題目問的是哪個單位。",
        ],
    ),
    (
        "體積與立體圖形",
        ["體積", "立方公分", "立方公尺", "長方體", "正方體"],
        [
            "先辨識是否為複合立體，再拆解計算。",
            "長方體體積公式：長 × 寬 × 高。",
            "必要時用大減小避免重複計算。",
        ],
    ),
    (
        "時間路程與應用題",
        ["公里", "馬拉松", "時間", "小時", "路程", "累積"],
        [
            "先整理『每次/每單位』與『總次數』關係。",
            "列出一行算式再代入數值。",
            "最後用估算做結果檢核。",
        ],
    ),
    (
        "整數與大數比較",
        ["億", "千億", "百億", "排序", "由大到小", "比較大小"],
        [
            "先看最高位值再比較。",
            "單位不同時先換成同單位。",
            "排序後再回答排名題。",
        ],
    ),
]


def classify_concepts(text: str) -> Tuple[List[str], Dict[str, List[str]]]:
    low = text.lower()
    labels: List[str] = []
    focus: Dict[str, List[str]] = {}

    for label, kws, tips in CONCEPT_RULES:
        hit = any((kw.lower() in low) for kw in kws)
        if hit:
            labels.append(label)
            focus[label] = tips

    if not labels:
        labels = ["綜合應用（需人工覆核）"]
        focus[labels[0]] = [
            "先做單位統一與關鍵字標記。",
            "把題目拆成 2~3 個可計算步驟。",
            "用反算檢查答案。",
        ]

    return labels, focus


def build_teaching_index(pairs: List[PairItem]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    for p in pairs:
        q_text = ""
        a_text = ""

        if p.question_file:
            q_text = extract_pdf_text(DOWNLOADS / p.question_file, max_pages=2)
        if p.answer_file:
            a_text = extract_pdf_text(DOWNLOADS / p.answer_file, max_pages=2)

        merged = "\n".join([q_text, a_text]).strip()
        concept_source = merged if merged else f"{p.question_url or ''} {p.answer_url or ''}"
        concepts, focus = classify_concepts(concept_source)

        out.append(
            {
                "exam_id": p.exam_id,
                "status": p.status,
                "question_file": p.question_file,
                "answer_file": p.answer_file,
                "source_pages": p.source_pages,
                "question_url": p.question_url,
                "answer_url": p.answer_url,
                "downloaded_at": p.downloaded_at,
                "concepts": concepts,
                "teaching_focus": focus,
                "preview_text": (merged[:350] + "...") if len(merged) > 350 else merged,
            }
        )

    return out


def concept_to_seed_kind(concept: str) -> str:
    c = str(concept or "")
    if "分數" in c:
        return "fraction_application"
    if "小數" in c or "位值" in c:
        return "decimal_place_value"
    if "面積" in c or "換算" in c:
        return "area_unit_conversion"
    if "體積" in c or "立體" in c:
        return "volume_geometry"
    if "時間" in c or "路程" in c:
        return "time_speed_word_problem"
    if "整數" in c or "大數" in c:
        return "integer_place_value_compare"
    return "comprehensive_word_problem"


def build_new_type_hint_seeds(teaching: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seeds: List[Dict[str, Any]] = []
    for item in teaching:
        exam_id = str(item.get("exam_id") or "").strip()
        if not exam_id:
            continue

        concepts = list(item.get("concepts") or [])
        focus = item.get("teaching_focus") or {}
        concept = str(concepts[0]) if concepts else "綜合應用（需人工覆核）"
        tips = list(focus.get(concept) or [])

        hint_l1 = tips[0] if len(tips) >= 1 else "先圈出已知、未知與單位。"
        hint_l2 = tips[1] if len(tips) >= 2 else "把題目翻成算式，分步驟計算。"
        hint_l3 = tips[2] if len(tips) >= 3 else "最後用反算或估算檢查結果合理性。"

        seeds.append(
            {
                "seed_id": f"tcool_{exam_id}_{concept_to_seed_kind(concept)}",
                "source_exam_id": exam_id,
                "source_status": item.get("status"),
                "suggested_kind": concept_to_seed_kind(concept),
                "tags": concepts,
                "hint_seed": {
                    "l1": f"Level 1（觀念）｜{hint_l1}",
                    "l2": f"Level 2（列式/操作）｜{hint_l2}",
                    "l3": f"Level 3（驗算/注意）｜{hint_l3}",
                },
                "question_url": item.get("question_url"),
                "answer_url": item.get("answer_url"),
                "preview_text": item.get("preview_text") or "",
            }
        )

    return seeds


def write_outputs(
    pairs: List[PairItem],
    teaching: List[Dict[str, Any]],
    seeds: List[Dict[str, Any]],
) -> None:
    PAIRED_PATH.write_text(
        json.dumps([asdict(p) for p in pairs], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    TEACHING_JSON.write_text(
        json.dumps(teaching, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    NEW_TYPE_HINT_SEEDS.write_text(
        json.dumps(seeds, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines: List[str] = []
    lines.append("# tcool 題目/解答教學分類整理")
    lines.append("")
    lines.append(f"產生時間：{datetime.now().isoformat(timespec='seconds')}")
    lines.append("")

    for idx, item in enumerate(teaching, start=1):
        lines.append(f"## {idx}. exam_id: {item['exam_id']}")
        lines.append(f"- 狀態：{item['status']}")
        lines.append(f"- 題目檔：{item.get('question_file') or '（無）'}")
        lines.append(f"- 解答檔：{item.get('answer_file') or '（無）'}")
        if item.get("question_url"):
            lines.append(f"- 題目連結（可瀏覽）：{item.get('question_url')}")
        if item.get("answer_url"):
            lines.append(f"- 解答連結（可瀏覽）：{item.get('answer_url')}")
        lines.append(f"- 觀念分類：{', '.join(item.get('concepts') or [])}")

        tf = item.get("teaching_focus") or {}
        for concept, tips in tf.items():
            lines.append(f"- {concept}：")
            for tip in tips:
                lines.append(f"  - {tip}")

        preview = (item.get("preview_text") or "").strip()
        if preview:
            lines.append(f"- 文字預覽：{preview}")

        src = item.get("source_pages") or []
        if src:
            lines.append("- 來源頁：")
            for u in src:
                lines.append(f"  - {u}")
        lines.append("")

    TEACHING_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    pairs = pair_manifest(manifest)
    teaching = build_teaching_index(pairs)
    seeds = build_new_type_hint_seeds(teaching)
    write_outputs(pairs, teaching, seeds)

    paired_count = sum(1 for p in pairs if p.status == "paired")
    print("=== organize_teaching_focus done ===")
    print(f"manifest: {MANIFEST_PATH}")
    print(f"pairs: {PAIRED_PATH} (total={len(pairs)}, paired={paired_count})")
    print(f"teaching json: {TEACHING_JSON}")
    print(f"teaching md: {TEACHING_MD}")
    print(f"new type hint seeds: {NEW_TYPE_HINT_SEEDS} (total={len(seeds)})")


if __name__ == "__main__":
    main()
