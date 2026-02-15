"""Hint overrides (manual-approval gate).

This file is intentionally simple and safe:
- The engine will ONLY apply overrides where `approved` is True.
- External LLM suggestions should be written here as `approved=False` first.
- After human review, flip to `approved=True` per template.
"""

from __future__ import annotations

from typing import Any, Dict


HINT_OVERRIDES: Dict[str, Dict[str, Any]] = {
    # Example:
    # "11": {
    #     "approved": False,
    #     "level1": "先判斷這題在問『用掉/剩下』還是『平均分』。",
    #     "level2": "把題目變成算式（先...再...）。",
    #     "level3": "算出答案，最後檢查單位與合理性。",
    #     "source": "external_llm",
    #     "note": "2026-02-15 candidate",
    # },
}
