from __future__ import annotations

import argparse
import json
import random
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from typing import Any


TYPE_KEY = "fraction_decimal_application_web_v1"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _pick_note(notes: list[dict[str, Any]], rng: random.Random) -> dict[str, Any]:
    if notes:
        return rng.choice(notes)
    return {
        "note_id": "fdnote_0000",
        "source_url": "(mock)",
        "title": "(mock)",
        "retrieved_at": _now_iso(),
        "quotes": [{"text": "先看單位再列式", "citation": "(mock)"}],
    }


def _norm(s: str) -> str:
    return "".join(str(s or "").split()).lower()


def _make_hints(level1: str, level2: str, level3: str, answer: str) -> dict[str, str]:
    ans = _norm(answer)
    for name, text in (("level1", level1), ("level2", level2), ("level3", level3)):
        if ans and ans in _norm(text):
            raise ValueError(f"{name} leaks answer")
    return {"level1": level1.strip(), "level2": level2.strip(), "level3": level3.strip()}


def _make_ladder(h1: str, h2: str, h3: str, h4: str, answer: str) -> dict[str, str]:
    ans = _norm(answer)
    for name, text in (("h1_strategy", h1), ("h4_check_reflect", h4)):
        if ans and ans in _norm(text):
            raise ValueError(f"{name} leaks answer")
    return {
        "h1_strategy": h1.strip(),
        "h2_equation": h2.strip(),
        "h3_compute": h3.strip(),
        "h4_check_reflect": h4.strip(),
    }


def _diag() -> list[dict[str, str]]:
    return [
        {"code": "E_RATE", "message": "比率解讀錯誤", "remedy": "確認折扣率與付款率是否相反。"},
        {"code": "E_DEN", "message": "分母使用錯誤", "remedy": "平均分配時分母應是份數或人數。"},
        {"code": "E_UNIT", "message": "單位未統一", "remedy": "先全部換成同一單位再計算。"},
        {"code": "E_TIME", "message": "時間換算錯誤", "remedy": "分鐘先換成小時，再代入路程公式。"},
        {"code": "E_CHECK", "message": "缺少回代檢查", "remedy": "把答案代回題目看是否合理。"},
    ]


def _item(idx: int, *, category: str, question: str, answer: str, hints: dict[str, str], hint_ladder: dict[str, str], steps: list[str], validator: dict[str, Any], topic_tags: list[str], note: dict[str, Any]) -> dict[str, Any]:
    quote = ((note.get("quotes") or [{}])[0] or {}) if isinstance(note.get("quotes"), list) else {}
    return {
        "id": f"fdweb_{idx:04d}",
        "type_key": TYPE_KEY,
        "category": category,
        "difficulty": random.choice(["easy", "medium", "hard"]),
        "question": question,
        "answer": answer,
        "hints": hints,
        "hint_ladder": hint_ladder,
        "steps": steps,
        "error_diagnostics": _diag(),
        "validator": validator,
        "topic_tags": topic_tags,
        "concept_points": ["圈重點", "列算式", "算步驟", "查合理性"],
        "evidence": {
            "note_id": str(note.get("note_id") or ""),
            "source_url": str(note.get("source_url") or ""),
            "title": str(note.get("title") or ""),
            "quoted_fact": str(quote.get("text") or "")[:25],
            "retrieved_at": str(note.get("retrieved_at") or ""),
        },
        "generated_at": _now_iso(),
    }


def _reduced_fraction_str(num: int, den: int) -> str:
    f = Fraction(num, den)
    return f"{f.numerator}/{f.denominator}"


def _gen_discount(rng: random.Random, notes: list[dict[str, Any]], idx: int) -> dict[str, Any]:
    price = rng.choice([120, 180, 250, 320, 480])
    discount = rng.choice([10, 15, 20, 25])
    answer = str(int(price * (100 - discount) / 100))
    hints = _make_hints("先把折扣轉成付款率。", "現價 = 原價 × (1 - 折扣率)。", "把百分率改成小數或分數再算。", answer)
    ladder = _make_ladder("策略：先求付款率。", "列式：現價 = 原價 × 付款率。", "計算：百分率轉小數後相乘。", "檢查：折後價要小於原價。", answer)
    steps = [
        f"步驟 1：付款率 = {100-discount}%",
        f"步驟 2：現價 = {price} × {(100-discount)}/100",
        f"步驟 3：得到 {answer} 元",
    ]
    return _item(idx, category="shopping_discount", question=f"（購物折扣）商品原價 {price} 元，打 {discount}% 折後要付多少元？（整數）", answer=answer, hints=hints, hint_ladder=ladder, steps=steps, validator={"type": "number", "tolerance": 0}, topic_tags=["shopping_discount", "decimal"], note=_pick_note(notes, rng))


def _gen_avg(rng: random.Random, notes: list[dict[str, Any]], idx: int) -> dict[str, Any]:
    total = rng.choice([18, 24, 30, 36])
    used_num = rng.choice([1, 2, 3])
    used_den = rng.choice([4, 5, 6])
    people = rng.choice([2, 3, 4, 6])
    remain = Fraction(total, 1) * (Fraction(1, 1) - Fraction(used_num, used_den))
    each = remain / people
    answer = f"{each.numerator}/{each.denominator}"
    hints = _make_hints("先求剩下量，再平均分配。", "每份 = [總量×(1-用掉分率)] ÷ 人數。", "先做分數減法，再除法與約分。", answer)
    ladder = _make_ladder("策略：兩段式（先剩下、再平均）。", "列式：每份 = (總量×剩下比例)÷人數。", "計算：分數運算後化最簡。", "檢查：每份×人數要回到剩下量。", answer)
    steps = [
        f"步驟 1：剩下比例 = 1 - {used_num}/{used_den}",
        f"步驟 2：剩下量 = {total} × 剩下比例",
        f"步驟 3：每人 = 剩下量 ÷ {people} = {answer}",
    ]
    return _item(idx, category="average_distribution", question=f"（平均分配）有 {total} 公升果汁，先用掉 {used_num}/{used_den}，剩下平均分給 {people} 人，每人多少公升？（最簡分數）", answer=answer, hints=hints, hint_ladder=ladder, steps=steps, validator={"type": "fraction"}, topic_tags=["average_distribution", "fraction"], note=_pick_note(notes, rng))


def _gen_unit(rng: random.Random, notes: list[dict[str, Any]], idx: int) -> dict[str, Any]:
    liters = rng.choice([1.2, 1.5, 2.4, 3.0])
    num = rng.choice([1, 2, 3])
    den = rng.choice([4, 5, 8])
    ml = int(liters * 1000)
    answer = str(int(ml * num / den))
    hints = _make_hints("先統一單位再運算。", "取出量 = 總毫升 × 分率。", "先換算，再做乘法。", answer)
    ladder = _make_ladder("策略：先公升轉毫升。", "列式：取出量 = (公升×1000)×分率。", "計算：先換單位再乘。", "檢查：答案不能超過總毫升。", answer)
    steps = [
        f"步驟 1：{liters:g} 公升 = {ml} 毫升",
        f"步驟 2：取出量 = {ml} × {num}/{den}",
        f"步驟 3：得到 {answer} 毫升",
    ]
    return _item(idx, category="unit_conversion", question=f"（單位換算）{liters:g} 公升牛奶取出 {num}/{den}，取出多少毫升？（整數）", answer=answer, hints=hints, hint_ladder=ladder, steps=steps, validator={"type": "number", "tolerance": 0}, topic_tags=["unit_conversion", "decimal"], note=_pick_note(notes, rng))


def _gen_distance(rng: random.Random, notes: list[dict[str, Any]], idx: int) -> dict[str, Any]:
    speed = rng.choice([42, 48, 54, 60, 72])
    mins = rng.choice([20, 25, 30, 40, 45])
    ans = _reduced_fraction_str(speed * mins, 60)
    hints = _make_hints("先把分鐘換成小時。", "距離 = 速度 × 時間。", "用分數小時代入後約分。", ans)
    ladder = _make_ladder("策略：先時間換算。", "列式：距離 = 速度×(分鐘/60)。", "計算：先約分再相乘。", "檢查：不到一小時，距離應小於時速。", ans)
    steps = [
        f"步驟 1：{mins} 分鐘 = {mins}/60 小時",
        f"步驟 2：距離 = {speed}×{mins}/60",
        f"步驟 3：約分得 {ans} 公里",
    ]
    return _item(idx, category="distance_time", question=f"（路程時間）車速每小時 {speed} 公里，行駛 {mins} 分鐘可走多少公里？（最簡分數）", answer=ans, hints=hints, hint_ladder=ladder, steps=steps, validator={"type": "fraction"}, topic_tags=["distance_time", "unit_conversion"], note=_pick_note(notes, rng))


def build_pack(raw_jsonl: Path, out_json: Path, n: int, seed: int) -> dict[str, Any]:
    notes = _read_jsonl(raw_jsonl)
    rng = random.Random(seed)
    gens = [_gen_discount, _gen_avg, _gen_unit, _gen_distance]

    items: list[dict[str, Any]] = []
    seen_q: set[str] = set()
    attempts = 0
    idx = 1
    while len(items) < n and attempts < n * 300:
        attempts += 1
        gen = rng.choice(gens)
        it = gen(rng, notes, idx)
        q = str(it.get("question") or "")
        if q in seen_q:
            continue
        seen_q.add(q)
        items.append(it)
        idx += 1

    if len(items) < n:
        raise RuntimeError(f"Unable to generate target items n={n}, got={len(items)}")

    pack = {
        "type_key": TYPE_KEY,
        "version": f"v{datetime.now().strftime('%Y%m%d')}",
        "seed": seed,
        "generated_at": _now_iso(),
        "items": items,
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    return pack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", default="data/external_web_notes/fraction_decimal_notes.jsonl")
    parser.add_argument("--out", default="data/fraction_decimal_application_web_v1_pack.json")
    parser.add_argument("--n", type=int, default=40)
    parser.add_argument("--seed", type=int, default=60224)
    args = parser.parse_args(argv)

    pack = build_pack(Path(args.raw), Path(args.out), n=int(args.n), seed=int(args.seed))
    print(f"Wrote {args.out} (items={len(pack['items'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
