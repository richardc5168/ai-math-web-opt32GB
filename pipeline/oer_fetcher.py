"""
pipeline/oer_fetcher.py — OER content fetcher and normalizer.

Fetches curriculum-aligned math content from trusted OER sources
(教育大市集, NAER, 教育部, etc.) and normalizes to problem schema.

Design principles:
- Only fetch from SOURCE_PRIORITY allowlist (pipeline/source_governance.py)
- All content gets license_decision before entering pipeline
- Content snapshots preserved with SHA-256 evidence hash
- Operates in offline mode by default (cached/seed data)
- Online mode fetches from real APIs when available

Source Priority:
  1. gazette.nat.gov.tw  — 課綱原文 (公共領域)
  2. market.cloud.edu.tw — 教育大市集 (CC 授權, API)
  3. www.naer.edu.tw     — 國教院 (結構性資訊)
  4. www.edu.tw          — 教育部 (素養測驗範例)
  5. gpi.culture.tw      — 政府出版品 (結構性資訊)

Usage:
  from pipeline.oer_fetcher import fetch_topic_seeds, build_problem_from_seed
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline.source_governance import (
    SOURCE_PRIORITY,
    build_source_metadata,
    check_textbook_reproduction,
    decide_license,
)


# ── Stage III Curriculum Structure ─────────────────────────

# 第三學習階段能力敘述與分年內容條目 (107 課綱)
STAGE_III_TOPICS: dict[str, dict[str, Any]] = {
    # ── 數與量 (n-III) ──
    "N-5-1": {
        "name": "十進位數的位值結構",
        "performance": "n-III-1",
        "grade": 5,
        "keywords": ["位值", "十進位", "數的大小比較"],
        "problem_types": ["比較大小", "位值表", "數的組成"],
    },
    "N-5-2": {
        "name": "因數與公因數",
        "performance": "n-III-2",
        "grade": 5,
        "keywords": ["因數", "公因數", "最大公因數"],
        "problem_types": ["找因數", "公因數", "GCD應用"],
    },
    "N-5-3": {
        "name": "倍數與公倍數",
        "performance": "n-III-2",
        "grade": 5,
        "keywords": ["倍數", "公倍數", "最小公倍數"],
        "problem_types": ["找倍數", "公倍數", "LCM應用"],
    },
    "N-5-4": {
        "name": "擴分、約分與通分",
        "performance": "n-III-3",
        "grade": 5,
        "keywords": ["擴分", "約分", "通分", "等值分數"],
        "problem_types": ["約分", "通分", "等值分數比較"],
    },
    "N-5-5": {
        "name": "異分母分數加減",
        "performance": "n-III-4",
        "grade": 5,
        "keywords": ["分數加法", "分數減法", "異分母", "通分"],
        "problem_types": ["異分母加法", "異分母減法", "帶分數加減"],
    },
    "N-5-6": {
        "name": "分數乘法(整數×分數、分數×分數)",
        "performance": "n-III-5",
        "grade": 5,
        "keywords": ["分數乘法", "帶分數乘法"],
        "problem_types": ["分數×整數", "分數×分數", "應用題"],
    },
    "N-5-7": {
        "name": "量的小數表示",
        "performance": "n-III-6",
        "grade": 5,
        "keywords": ["小數", "小數與分數互換"],
        "problem_types": ["小數化分數", "分數化小數"],
    },
    "N-5-8": {
        "name": "小數乘以整數",
        "performance": "n-III-7",
        "grade": 5,
        "keywords": ["小數乘法", "直式計算"],
        "problem_types": ["小數×整數", "直式乘法"],
    },
    "N-5-9": {
        "name": "小數除以整數",
        "performance": "n-III-8",
        "grade": 5,
        "keywords": ["小數除法", "直式計算"],
        "problem_types": ["小數÷整數", "直式除法"],
    },
    "N-5-10": {
        "name": "百分率（折、成）",
        "performance": "n-III-9",
        "grade": 5,
        "keywords": ["百分率", "折", "成", "百分比"],
        "problem_types": ["求百分率", "折扣計算", "成數計算"],
    },
    "N-5-11": {
        "name": "概數（四捨五入）",
        "performance": "n-III-10",
        "grade": 5,
        "keywords": ["概數", "四捨五入", "估算"],
        "problem_types": ["四捨五入", "估算", "概數應用"],
    },
    "N-6-1": {
        "name": "質因數分解",
        "performance": "n-III-2",
        "grade": 6,
        "keywords": ["質數", "合數", "質因數分解", "短除法"],
        "problem_types": ["質因數分解", "用短除法求GCD/LCM"],
    },
    "N-6-2": {
        "name": "分數四則混合計算",
        "performance": "n-III-4",
        "grade": 6,
        "keywords": ["四則混合", "先乘除後加減", "分數計算"],
        "problem_types": ["混合計算", "括號運算"],
    },
    "N-6-3": {
        "name": "分數除法",
        "performance": "n-III-5",
        "grade": 6,
        "keywords": ["分數除法", "倒數", "整數÷分數", "分數÷分數"],
        "problem_types": ["分數÷整數", "整數÷分數", "分數÷分數"],
    },
    "N-6-4": {
        "name": "小數乘以小數",
        "performance": "n-III-7",
        "grade": 6,
        "keywords": ["小數乘法", "小數×小數"],
        "problem_types": ["小數×小數", "直式乘法"],
    },
    "N-6-5": {
        "name": "小數除以小數",
        "performance": "n-III-8",
        "grade": 6,
        "keywords": ["小數除法", "小數÷小數"],
        "problem_types": ["小數÷小數", "直式除法"],
    },
    "N-6-6": {
        "name": "比與比值",
        "performance": "n-III-9",
        "grade": 6,
        "keywords": ["比", "比值", "等比", "比例"],
        "problem_types": ["求比值", "等比判斷", "比的應用"],
    },
    "N-6-7": {
        "name": "速度（距離、時間）",
        "performance": "n-III-11",
        "grade": 6,
        "keywords": ["速度", "距離", "時間", "單位換算"],
        "problem_types": ["求速度", "求距離", "求時間", "單位換算"],
    },
    "N-6-8": {
        "name": "小數與分數的互換",
        "performance": "n-III-6",
        "grade": 6,
        "keywords": ["小數", "分數", "互換", "循環小數"],
        "problem_types": ["小數化分數", "分數化小數"],
    },
    # ── 空間與形狀 (s-III) ──
    "S-5-1": {
        "name": "三角形與四邊形面積",
        "performance": "s-III-1",
        "grade": 5,
        "keywords": ["面積", "三角形", "四邊形", "平行四邊形", "梯形"],
        "problem_types": ["求面積", "面積比較"],
    },
    "S-5-2": {
        "name": "正方體與長方體體積",
        "performance": "s-III-2",
        "grade": 5,
        "keywords": ["體積", "正方體", "長方體", "容積"],
        "problem_types": ["求體積", "求容積"],
    },
    "S-6-1": {
        "name": "圓形圖與圓面積",
        "performance": "s-III-3",
        "grade": 6,
        "keywords": ["圓", "圓周", "圓面積", "圓周率"],
        "problem_types": ["求圓面積", "求圓周長"],
    },
    "S-6-2": {
        "name": "比例尺（地圖與縮放）",
        "performance": "s-III-4",
        "grade": 6,
        "keywords": ["比例尺", "縮放", "地圖", "放大", "縮小"],
        "problem_types": ["地圖距離", "實際距離", "求比例尺"],
    },
    "S-6-3": {
        "name": "角柱與圓柱",
        "performance": "s-III-2",
        "grade": 6,
        "keywords": ["角柱", "圓柱", "表面積", "體積"],
        "problem_types": ["求體積", "求表面積"],
    },
    # ── 資料與不確定性 (d-III) ──
    "D-5-1": {
        "name": "折線圖",
        "performance": "d-III-1",
        "grade": 5,
        "keywords": ["折線圖", "資料", "趨勢", "平均"],
        "problem_types": ["讀圖", "趨勢判斷", "求平均"],
    },
    "D-6-1": {
        "name": "圓形圖",
        "performance": "d-III-2",
        "grade": 6,
        "keywords": ["圓形圖", "百分比", "資料統計"],
        "problem_types": ["讀圖", "百分比計算"],
    },
    # ── 關係 (r-III) ──
    "R-5-1": {
        "name": "未知數的列式與計算",
        "performance": "r-III-1",
        "grade": 5,
        "keywords": ["未知數", "列式", "等式"],
        "problem_types": ["列式求解", "找規律"],
    },
    "R-6-1": {
        "name": "正比與反比",
        "performance": "r-III-2",
        "grade": 6,
        "keywords": ["正比", "反比", "比例"],
        "problem_types": ["正比判斷", "反比應用"],
    },
}

# ── Problem Seed Templates ─────────────────────────────────

# Seed templates with deterministic parameter ranges
SEED_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "N-5-10": [
        {
            "template": "某商店原價 {price} 元的商品打 {discount}折，售價是多少元？",
            "params_range": {"price": (100, 1000, 50), "discount": (5, 9, 1)},
            "operation": "discount",
            "answer_type": "integer",
            "unit": "元",
        },
        {
            "template": "班上有 {total} 人，其中 {part} 人戴眼鏡，戴眼鏡的人佔全班的百分之幾？",
            "params_range": {"total": (20, 50, 5), "part": (5, 20, 1)},
            "operation": "percent_of",
            "answer_type": "percent",
            "unit": "%",
        },
    ],
    "N-5-11": [
        {
            "template": "把 {value} 用四捨五入法取概數到{place_zh}位，結果是多少？",
            "params_range": {"value": (1.01, 99.99, 0.01)},
            "place_options": [
                ("個", "ones"),
                ("十分", "tenths"),
                ("百分", "hundredths"),
            ],
            "operation": "round",
            "answer_type": "decimal",
        },
    ],
    "N-6-3": [
        {
            "template": "{a_whole} 又 {a_num}/{a_den} ÷ {b_num}/{b_den} = ?",
            "params_range": {
                "a_whole": (1, 5, 1),
                "a_num": (1, 5, 1),
                "a_den": (2, 8, 1),
                "b_num": (1, 5, 1),
                "b_den": (2, 8, 1),
            },
            "operation": "fraction_div",
            "answer_type": "fraction",
        },
    ],
    "N-6-7": [
        {
            "template": "小明騎腳踏車以每小時 {speed} 公里的速度行駛 {time} 小時，共走了幾公里？",
            "params_range": {"speed": (10, 30, 2), "time": (1, 5, 1)},
            "operation": "find_distance",
            "answer_type": "integer",
            "unit": "公里",
        },
        {
            "template": "A 地到 B 地距離 {distance} 公里，火車花了 {time} 小時到達，火車的速度是每小時幾公里？",
            "params_range": {"distance": (100, 500, 50), "time": (1, 5, 1)},
            "operation": "find_speed",
            "answer_type": "integer",
            "unit": "公里/小時",
        },
    ],
    "S-6-2": [
        {
            "template": "地圖上比例尺為 1:{scale}，地圖上 {map_dist} 公分代表實際幾公分？",
            "params_range": {"scale": (1000, 50000, 1000), "map_dist": (1, 10, 1)},
            "operation": "map_to_actual",
            "answer_type": "integer",
            "unit": "公分",
        },
    ],
    "D-5-1": [
        {
            "template": "下表為某班一週每天的氣溫記錄（°C）：{values_str}。請問平均氣溫是幾度？",
            "params_range": {"base_temp": (20, 30, 1), "variation": (1, 5, 1)},
            "operation": "mean",
            "answer_type": "decimal",
            "unit": "°C",
            "data_points": 5,
        },
    ],
}


# ── Seed Data (offline mode) ──────────────────────────────

def generate_seed_problems(
    topic_code: str,
    count: int = 5,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """
    Generate deterministic seed problems from templates.
    Uses seed for reproducibility (no randomness dependency).
    """
    import random as _random

    rng = _random.Random(seed)
    templates = SEED_TEMPLATES.get(topic_code, [])
    if not templates:
        return []

    topic_info = STAGE_III_TOPICS.get(topic_code, {})
    problems = []

    for i in range(count):
        tmpl = templates[i % len(templates)]
        params = _generate_params(tmpl, rng)
        question = _fill_template(tmpl["template"], params)

        # Build source metadata (seed data = self-generated, public-domain)
        source = build_source_metadata(
            url=f"self-generated://seed/{topic_code}/{i}",
            license_type="public-domain",
            content_snapshot=question,
        )

        problem = {
            "id": f"seed-{topic_code}-{seed}-{i:03d}",
            "grade": topic_info.get("grade", 5),
            "stage": "III",
            "topic_codes": [topic_info.get("performance", ""), topic_code],
            "question": question,
            "answer_type": tmpl.get("answer_type", "integer"),
            "source": source,
            "generation_metadata": {
                "model": "deterministic-seed",
                "self_refine_iterations": 0,
                "prompt_version": "seed-v1",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            "_solver_params": {
                "topic_code": topic_code,
                **params,
                "operation": tmpl.get("operation", ""),
            },
        }

        if tmpl.get("unit"):
            problem["_solver_params"]["unit"] = tmpl["unit"]

        problems.append(problem)

    return problems


def _generate_params(
    tmpl: dict[str, Any],
    rng: Any,
) -> dict[str, Any]:
    """Generate random parameters from template ranges."""
    params = {}
    ranges = tmpl.get("params_range", {})
    for key, spec in ranges.items():
        if isinstance(spec, tuple) and len(spec) == 3:
            low, high, step = spec
            if isinstance(low, float) or isinstance(high, float):
                # Float range
                steps = int((high - low) / step)
                val = low + rng.randint(0, max(steps, 1)) * step
                params[key] = round(val, 4)
            else:
                # Integer range
                steps = (high - low) // step
                val = low + rng.randint(0, max(steps, 1)) * step
                params[key] = val
    # Handle place_options for rounding
    if "place_options" in tmpl:
        choice = rng.choice(tmpl["place_options"])
        params["place_zh"] = choice[0]
        params["place"] = choice[1]
    # Handle data_points for D-5-1
    if "data_points" in tmpl:
        base = params.get("base_temp", 25)
        var = params.get("variation", 3)
        values = [base + rng.randint(-var, var) for _ in range(tmpl["data_points"])]
        params["values"] = values
        params["values_str"] = "、".join(str(v) for v in values)
    return params


def _fill_template(template: str, params: dict) -> str:
    """Fill template string with parameters."""
    try:
        return template.format(**params)
    except KeyError:
        return template


# ── OER API Integration (online mode) ─────────────────────

class OERFetcher:
    """
    Fetches content from OER sources. Operates offline by default.

    Online mode requires network access and is rate-limited.
    All fetched content goes through license verification before use.
    """

    def __init__(self, offline: bool = True):
        self.offline = offline
        self.cache_dir = Path("data/oer_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch_topic_seeds(
        self,
        topic_code: str,
        count: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Fetch seed content for a topic code.

        In offline mode: returns deterministic seed data.
        In online mode: fetches from OER APIs and caches.
        """
        if self.offline:
            return generate_seed_problems(topic_code, count)

        # Online mode — try each source in priority order
        seeds = []
        for source in SOURCE_PRIORITY:
            if len(seeds) >= count:
                break
            fetched = self._fetch_from_source(source, topic_code, count - len(seeds))
            seeds.extend(fetched)

        return seeds

    def _fetch_from_source(
        self,
        source: dict,
        topic_code: str,
        count: int,
    ) -> list[dict[str, Any]]:
        """Fetch from a specific OER source. Returns normalized problem dicts."""
        domain = source["domain"]
        topic_info = STAGE_III_TOPICS.get(topic_code, {})

        if domain == "market.cloud.edu.tw":
            return self._fetch_edu_market(topic_info, count)
        # Other sources would have their own fetchers
        return []

    def _fetch_edu_market(
        self,
        topic_info: dict,
        count: int,
    ) -> list[dict[str, Any]]:
        """
        Fetch from 教育大市集 API.

        NOTE: Actual API integration requires:
        1. API key registration
        2. TW LOM metadata parsing
        3. Rate limiting compliance

        This is a scaffold — returns empty until API is configured.
        """
        # When API is available:
        # 1. Search by keyword (topic_info['keywords'])
        # 2. Filter by grade and CC license
        # 3. Parse TW LOM metadata
        # 4. Verify license with decide_license()
        # 5. Create evidence hash of content
        # 6. Normalize to problem schema
        return []

    def get_cached(self, topic_code: str) -> list[dict[str, Any]]:
        """Load cached content for a topic."""
        cache_file = self.cache_dir / f"{topic_code}.jsonl"
        if not cache_file.exists():
            return []
        items = []
        for line in cache_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return items

    def save_to_cache(self, topic_code: str, items: list[dict]) -> None:
        """Save fetched items to cache."""
        cache_file = self.cache_dir / f"{topic_code}.jsonl"
        lines = [json.dumps(item, ensure_ascii=False) for item in items]
        cache_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── Content Normalization ──────────────────────────────────

def normalize_to_problem_schema(
    raw: dict[str, Any],
    topic_code: str,
    source_url: str,
    license_type: str,
) -> dict[str, Any]:
    """
    Normalize raw fetched content to the problem.schema.json format.

    Performs:
    - License verification
    - Textbook reproduction check
    - Field mapping
    - Evidence hash creation
    """
    topic_info = STAGE_III_TOPICS.get(topic_code, {})

    # License check
    license_decision = decide_license(license_type, source_url)

    # Textbook reproduction check
    question_text = raw.get("question", raw.get("text", ""))
    is_safe, pattern = check_textbook_reproduction(question_text)
    if not is_safe:
        return {
            "error": f"textbook reproduction detected: {pattern}",
            "blocked": True,
        }

    # Build normalized problem
    source = build_source_metadata(
        url=source_url,
        license_type=license_type,
        content_snapshot=question_text,
    )

    problem = {
        "id": raw.get("id", f"oer-{topic_code}-{hashlib.md5(question_text.encode()).hexdigest()[:8]}"),
        "grade": topic_info.get("grade", 5),
        "stage": "III",
        "topic_codes": [topic_info.get("performance", ""), topic_code],
        "question": question_text,
        "answer_type": raw.get("answer_type", "integer"),
        "source": source,
        "difficulty": raw.get("difficulty", 1),
    }

    # Include solution if provided
    if "solution" in raw:
        problem["solution"] = raw["solution"]
    if "answer" in raw:
        problem["solution"] = problem.get("solution", {})
        problem["solution"]["answer"] = {"value": raw["answer"]}

    return problem


# ── Topic Coverage Report ──────────────────────────────────

def compute_topic_coverage(
    existing_problems: list[dict],
) -> dict[str, Any]:
    """
    Compute coverage of Stage III topics against curriculum requirements.

    Returns coverage report with gaps to fill.
    """
    covered: dict[str, int] = {}
    for p in existing_problems:
        for code in p.get("topic_codes", []):
            if code in STAGE_III_TOPICS:
                covered[code] = covered.get(code, 0) + 1

    all_topics = set(STAGE_III_TOPICS.keys())
    covered_topics = set(covered.keys())
    missing = all_topics - covered_topics
    low_coverage = {k: v for k, v in covered.items() if v < 3}

    total = len(all_topics)
    covered_count = len(covered_topics)

    return {
        "total_topics": total,
        "covered_count": covered_count,
        "coverage_rate": round(covered_count / max(total, 1), 4),
        "missing_topics": sorted(missing),
        "low_coverage_topics": low_coverage,
        "topic_counts": covered,
        "priority_gaps": [
            code for code in sorted(missing)
            if STAGE_III_TOPICS[code]["grade"] in (5, 6)
        ],
    }
