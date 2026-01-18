from __future__ import annotations

import json
import os
from typing import Any, Optional


def _extract_json_object(text: str) -> str:
    """Best-effort extraction of a JSON object from arbitrary text."""

    s = (text or "").strip()
    if not s:
        raise ValueError("empty response")

    # Fast path: already JSON.
    if s.startswith("{") and s.endswith("}"):
        return s

    # Try to find the first {...} block.
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        return s[start : end + 1]

    raise ValueError("no JSON object found")


def chat_json(
    *,
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.2,
    api_key_env: str = "OPENAI_API_KEY",
) -> dict[str, Any]:
    """Call OpenAI chat and return a JSON object.

    If API key is missing, raises RuntimeError.
    """

    api_key = os.getenv(api_key_env, "").strip()
    if not api_key:
        raise RuntimeError(f"Missing env var {api_key_env}")

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    chosen_model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    resp = client.chat.completions.create(
        model=chosen_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        # JSON mode is supported by many recent models; keep best-effort.
        response_format={"type": "json_object"},
    )

    content = (resp.choices[0].message.content or "").strip()
    json_text = _extract_json_object(content)
    return json.loads(json_text)
