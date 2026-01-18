from __future__ import annotations

import json
from typing import Any, Literal


def build_tagging_prompt(*, knowledge_points: list[str], question: str) -> str:
    kp = ", ".join(knowledge_points)

    schema = {
        "core_concept": "<must be one of the knowledge points>",
        "prerequisites": ["<short prerequisite skill>"] ,
        "difficulty": 1,
        "estimated_time_sec": 90,
        "rationale": "<short reason>",
    }

    return (
        "你現在是一位數學學科專家。請閱讀以下題目，並根據我提供的【知識點清單】，為題目標註：\n"
        "1) 核心知識點（只能從清單挑 1 個）\n"
        "2) 前置必要能力（可多個，請用簡短片語）\n"
        "3) 難度等級（1-5）\n"
        "4) 預估解題時間（秒，15-3600）\n\n"
        f"【知識點清單】：[{kp}]\n"
        f"【題目內容】：{question.strip()}\n\n"
        "【輸出格式】：請只輸出 1 個 JSON object，不要加任何多餘文字。\n"
        f"【JSON Schema 範例】：{json.dumps(schema, ensure_ascii=False)}\n"
    )


def build_misconception_mcq_prompt(
    *,
    concept: str,
    grade: str = "國中",
    style: Literal["standard", "factoring_then_formula"] = "standard",
    roots: Literal["integer", "rational", "mixed"] = "integer",
    difficulty: int = 3,
) -> str:
    schema = {
        "items": [
            {
                "concept_tag": concept,
                "stem": "<question stem>",
                "verification": {
                    "symbol": "x",
                    "expr": "x**2 - 5*x + 6",
                    "solution_set": ["2", "3"],
                },
                "options": [
                    {"key": "A", "text": "...", "values": ["..."], "misconception_tag": "..."},
                    {"key": "B", "text": "...", "values": ["..."], "misconception_tag": "..."},
                    {"key": "C", "text": "...", "values": ["..."], "misconception_tag": "..."},
                    {"key": "D", "text": "...", "values": ["..."], "misconception_tag": None},
                ],
                "correct": "D",
                "solution": "<teacher-facing solution>",
                "diagnostics": {
                    "A": "<if choose A, what misconception>",
                    "B": "...",
                    "C": "...",
                    "D": "<correct reasoning>",
                },
                "hints": {"level1": "...", "level2": "...", "level3": "...", "level4": "..."},
            }
        ]
    }

    if not (1 <= int(difficulty) <= 5):
        raise ValueError("difficulty must be 1..5")

    extra_style_rules = ""
    if style == "factoring_then_formula":
        extra_style_rules = (
            "\n風格要求（factoring_then_formula）：\n"
            "- 題目請選擇『可因式分解』的二次式（建議整數根），讓學生可以先用因式分解解。\n"
            "- 解題說明(solution)必須先用因式分解得到根，再用公式解進行驗算（同一題兩種方法）。\n"
            "- 誘答項至少要涵蓋：因式分解找因數配對錯、零乘積性質用錯、公式解忘記除以 2a、判別式/正負號錯。\n"
            "- verification.solution_set 請只給『實數解』，並與正確選項 values 完全一致（忽略順序）。\n"
        )

    roots_rule = (
        "\n根型態控制（roots）：\n"
        "- integer：兩個根皆為整數。\n"
        "- rational：兩個根皆為有理數，且至少一個不是整數（例如 1/2）。\n"
        "- mixed：兩個根皆為有理數，且至少一個是整數、至少一個不是整數。\n"
        f"本次 roots = {roots}\n"
    )

    difficulty_rule = (
        "\n難度控制（difficulty 1-5）：\n"
        "- 1：係數很小、可快速因式分解；提示偏引導找因數。\n"
        "- 2：係數小到中等；允許有負數根；步驟仍短。\n"
        "- 3：標準課本題；可能需要先整理同類項或提公因數。\n"
        "- 4：係數較大或 a≠1（但仍可因分）；容易出現符號陷阱。\n"
        "- 5：係數較大、需要較多整理/檢核；仍需保持清楚可引導。\n"
        f"本次 difficulty = {int(difficulty)}\n"
    )

    quality_rules = (
        "\n品質與可驗證性硬性規則：\n"
        "- verification.expr 必須是一個『整係數』二次多項式（例如 ax**2+bx+c），用來表示 expr==0。\n"
        "- 請避免過大的係數；讓國中生可手算。\n"
        "- hints 必須是『概念提示/下一步』，不可直接揭露答案或完整解。\n"
        "- hints 必須符合課本式固定流程（請用接近下列句型、但填入本題的 a,b,c 或關鍵整理結果）：\n"
        "  • level1（整理）：\"先把方程式整理成 ax^2+bx+c=0（移項、合併同類項）。\"\n"
        "  • level2（因式分解）：\"嘗試因式分解成 (px+q)(rx+s)=0（必要時可先提出公因數）。\"\n"
        "  • level3（零乘積）：\"利用零乘積性質：令 px+q=0 或 rx+s=0，得到兩個一次方程。\"\n"
        "  • level4（公式驗算）：\"用公式解驗算：Δ=b^2-4ac，x=[-b±sqrt(Δ)]/(2a)，只用來檢核，不要在提示中寫出最後根。\"\n"
        "- 提示中禁止出現『x=...』或直接列出兩個解。\n"
    )

    return (
        f"請針對『{concept}』設計 1 道高品質的{grade}數學選擇題。\n\n"
        "要求：\n"
        "- 需包含 4 個選項（A-D），且只有 1 個正確答案。\n"
        "- 題目需可被程式驗證：請提供 verification.expr（可給 Sympy 的 expr，代表 expr==0）、verification.symbol、verification.solution_set。\n"
        "- 每個選項都必須提供 options[i].values（用字串列出該選項代表的解，例如 ['2','3']）。\n"
        "- 正確選項的 values 必須等於 solution_set（忽略順序）。\n"
        "- 三個錯誤選項必須對應常見迷思（例如：判別式計算錯誤、忘記除以 2a、正負號帶錯）。\n"
        "- 請為每個錯誤選項提供 misconception_tag（短標籤）。\n"
        "- 診斷邏輯：說明學生選各選項代表的迷思。\n"
        "- 引導式提示：提供四層提示 level1→level2→level3→level4（不要直接給答案）。\n\n"
        f"{extra_style_rules}"
        f"{roots_rule}"
        f"{difficulty_rule}"
        f"{quality_rules}\n"
        "輸出規則：只輸出 1 個 JSON object，不要加任何多餘文字。\n"
        f"JSON Schema 範例：{json.dumps(schema, ensure_ascii=False)}\n"
    )


def safe_get(obj: dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = obj
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur
