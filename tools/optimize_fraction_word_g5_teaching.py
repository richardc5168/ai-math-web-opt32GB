#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
BANK_PATH = ROOT / "docs" / "fraction-word-g5" / "bank.js"
PLAYBOOK_PATH = ROOT / "data" / "fraction_word_g5_teaching_playbook.json"


def parse_js_array(path: Path) -> tuple[str, list[dict[str, Any]]]:
    text = path.read_text(encoding="utf-8")
    for m in re.finditer(r"window\.(\w+)\s*=\s*\[", text):
        var_name = m.group(1)
        start = m.end() - 1
        depth = 0
        end = start
        for i in range(start, len(text)):
            c = text[i]
            if c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        chunk = text[start:end]
        if len(chunk) < 10:
            continue
        try:
            arr = json.loads(chunk)
            if isinstance(arr, list):
                return var_name, arr
        except json.JSONDecodeError:
            continue
    raise RuntimeError(f"Cannot parse array from {path}")


def write_js_array(path: Path, var_name: str, arr: list[dict[str, Any]]) -> None:
    content = f"window.{var_name} = {json.dumps(arr, ensure_ascii=False, indent=2)};\n"
    path.write_text(content, encoding="utf-8")


def unit_from_question(question: str) -> str:
    units = ["頁", "公尺", "公分", "公升", "公斤", "人", "棵", "元", "顆", "本", "杯"]
    for u in units:
        if u in question:
            return u
    return ""


def template_for_kind(kind: str) -> dict[str, str]:
    templates: dict[str, dict[str, str]] = {
        "fraction_of_quantity": {
            "l1": "先找出『全體量』和『幾分之幾』；看到「某量的幾分之幾」通常用乘法。",
            "l2": "列式：部分量 = 全體量 × 分數。可先約分再乘，算得更快更不容易錯。",
            "s2": "判斷題型：某量的幾分之幾 → 用乘法。",
            "s3": "列式：部分量 = 全體量 × 分數（先約分）。",
        },
        "remaining_after_fraction": {
            "l1": "關鍵字是『剩下』，先求剩下比例：1 − 用掉比例。",
            "l2": "列式：剩下量 = 全體量 × (1 − 用掉分數)。先算括號內分數再乘全體量。",
            "s2": "判斷題型：先求剩下比例，再求剩下量。",
            "s3": "列式：剩下量 = 全體量 × (1 − 用掉分數)。",
        },
        "remain_then_fraction": {
            "l1": "這是兩段題：先算第一次剩下，再算第二次針對『剩下』的部分。",
            "l2": "列式：第一次剩下 = 全體×(1−a/b)；最後剩下 = 第一次剩下×(1−c/d) 或 第一次剩下−第二次用掉。",
            "s2": "判斷題型：連續兩段（剩下再處理）。",
            "s3": "列式：先算第一次剩下，再算第二次變化。",
        },
        "average_division": {
            "l1": "看到『平均分成幾份，每份多少』，通常用除法。",
            "l2": "列式：每份 = 總量 ÷ 份數。分數除以整數可改成乘以倒數。",
            "s2": "判斷題型：平均分配 → 除法。",
            "s3": "列式：每份 = 總量 ÷ 份數。",
        },
        "fraction_of_fraction": {
            "l1": "看到『幾分之幾的幾分之幾』，是分數乘分數。",
            "l2": "列式：結果 = 第一個分數 × 第二個分數；分子乘分子、分母乘分母，再化簡。",
            "s2": "判斷題型：分數的分數 → 乘法。",
            "s3": "列式：結果 = 分數 × 分數（可先約分）。",
        },
        "reverse_fraction": {
            "l1": "若已知『某部分』和『它占全體幾分之幾』，要反推全體，通常用除法。",
            "l2": "列式：全體量 = 已知部分 ÷ 分數。分數除法要乘倒數。",
            "s2": "判斷題型：已知部分，反推全體。",
            "s3": "列式：全體量 = 部分量 ÷ 分數。",
        },
        "shopping_two_step": {
            "l1": "先分清楚每一步在算什麼（先算單價/總價，再算折扣或剩餘）。",
            "l2": "列式：把題目拆成 Step A、Step B 兩個算式，先做 A 再把結果帶入 B。",
            "s2": "判斷題型：兩步驟生活應用題。",
            "s3": "列式：Step A 先求中間量，Step B 求最終量。",
        },
        "generic_fraction_word": {
            "l1": "先圈出關鍵字（用了、剩下、平均、幾分之幾），先決定加減乘除再列式。",
            "l2": "列式原則：同整體可加減；『某量的幾分之幾』用乘法；平均分配用除法。",
            "s2": "判斷題型：先辨識關鍵字與整體。",
            "s3": "列式：依題意選對加減乘除後再計算。",
        },
    }
    return templates.get(kind, templates["generic_fraction_word"])


def build_hints(kind: str) -> list[str]:
    t = template_for_kind(kind)
    return [
        f"L1 觀念判斷：{t['l1']}",
        f"L2 列式模型：{t['l2']}",
        "L3 計算提醒：先把式子完整寫出，再一步一步算；最後檢查單位、合理性與是否化簡。",
    ]


def build_steps(kind: str, question: str) -> list[str]:
    t = template_for_kind(kind)
    unit = unit_from_question(question)
    utext = f"（單位：{unit}）" if unit else ""
    return [
        "步驟1：先圈出題目已知（全體量、分數、要求的量）。",
        f"步驟2：{t['s2']}",
        f"步驟3：{t['s3']}",
        "步驟4：依運算順序計算（先括號、再乘除、後加減；分數先通分或先約分）。",
        f"步驟5：把計算結果寫成答案{utext}，並確認是否要化成最簡分數或整數。",
        "步驟6：回題目檢查：答案大小是否合理、語意是否吻合（是『用掉』還是『剩下』）。",
    ]


def build_explanation(steps: list[str]) -> str:
    lines = []
    for i, s in enumerate(steps, start=1):
        plain = s.replace(f"步驟{i}：", "", 1)
        lines.append(f"步驟 {i}：{plain}")
    return "\n".join(lines)


def optimize() -> tuple[int, Counter[str]]:
    var_name, bank = parse_js_array(BANK_PATH)
    stats: Counter[str] = Counter()

    for q in bank:
        if not isinstance(q, dict):
            continue
        kind = str(q.get("kind") or "generic_fraction_word").strip()
        question = str(q.get("question") or "")

        q["hints"] = build_hints(kind)
        q["steps"] = build_steps(kind, question)
        q["explanation"] = build_explanation(q["steps"])

        stats[kind] += 1

    write_js_array(BANK_PATH, var_name, bank)
    return len(bank), stats


def write_playbook(total: int, stats: Counter[str]) -> None:
    payload = {
        "module": "fraction-word-g5",
        "target": "讓孩童與家長一看就懂的分層教學提示與步驟",
        "question_count": total,
        "rules": [
            {
                "rule_id": "HINT_L1",
                "goal": "只做觀念判斷，不給答案",
                "pattern": "L1 觀念判斷：指出題型與運算選擇原因",
            },
            {
                "rule_id": "HINT_L2",
                "goal": "把文字題轉成方程/算式骨架",
                "pattern": "L2 列式模型：給公式與變數角色，不帶最終數值",
            },
            {
                "rule_id": "HINT_L3",
                "goal": "只給計算流程與檢查清單",
                "pattern": "L3 計算提醒：一步步算 + 單位/化簡檢查",
            },
            {
                "rule_id": "STEPS_6",
                "goal": "固定六步教學流程",
                "pattern": "找已知→判型→列式→計算→寫答→回題檢查",
            },
            {
                "rule_id": "NO_ANSWER_LEAK",
                "goal": "提示不直接出現最終答案",
                "pattern": "hints 不包含答案字串，特別是最後一層提示",
            },
        ],
        "kind_distribution": dict(stats),
        "copilot_recipe": [
            "先保留 question 與 answer，不改題意與答案。",
            "依 kind 套入 L1/L2/L3 模板生成 hints。",
            "依 kind 產生 6 步驟 steps；explanation 由 steps 自動串接。",
            "執行驗證：validate_all_elementary_banks.py 必須 0 FAIL。",
            "抽樣人工複核：每種 kind 至少 2 題，確認語句易懂且不爆答案。",
        ],
    }
    PLAYBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLAYBOOK_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    total, stats = optimize()
    write_playbook(total, stats)
    print(f"Optimized fraction-word-g5: {total} questions")
    for k, c in stats.most_common():
        print(f"  {k:28s} {c:4d}")
    print(f"Playbook: {PLAYBOOK_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
