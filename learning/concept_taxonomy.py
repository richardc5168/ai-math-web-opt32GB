"""Concept Taxonomy — Standardized concept IDs for Grade 5-6 math.

Maps every concept to a structured record with:
- display_name_zh: Human-readable Chinese name for reports
- domain: Subject area (fraction, decimal, percent, volume, application, linear, quadratic)
- grade: Target grade level
- prerequisites: List of concept_ids that must be learned first
- difficulty_base: Baseline difficulty (easy / normal / hard)

Usage:
    from learning.concept_taxonomy import CONCEPT_TAXONOMY, get_concept, get_prerequisites
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Concept Taxonomy Registry
# ---------------------------------------------------------------------------

CONCEPT_TAXONOMY: Dict[str, Dict[str, Any]] = {
    # ----- Fraction Domain -----
    "frac_concept_basic": {
        "display_name_zh": "分數基本概念",
        "domain": "fraction",
        "grade": 5,
        "prerequisites": [],
        "difficulty_base": "easy",
    },
    "frac_add_like": {
        "display_name_zh": "同分母分數加減",
        "domain": "fraction",
        "grade": 5,
        "prerequisites": ["frac_concept_basic"],
        "difficulty_base": "easy",
    },
    "lcm_basic": {
        "display_name_zh": "最小公倍數",
        "domain": "fraction",
        "grade": 5,
        "prerequisites": [],
        "difficulty_base": "easy",
    },
    "frac_add_unlike": {
        "display_name_zh": "異分母分數加減",
        "domain": "fraction",
        "grade": 5,
        "prerequisites": ["frac_add_like", "lcm_basic"],
        "difficulty_base": "normal",
    },
    "frac_simplify": {
        "display_name_zh": "約分與最簡分數",
        "domain": "fraction",
        "grade": 5,
        "prerequisites": ["frac_concept_basic"],
        "difficulty_base": "easy",
    },
    "frac_mixed_improper": {
        "display_name_zh": "帶分數與假分數互換",
        "domain": "fraction",
        "grade": 5,
        "prerequisites": ["frac_concept_basic"],
        "difficulty_base": "easy",
    },
    "frac_multiply": {
        "display_name_zh": "分數乘法",
        "domain": "fraction",
        "grade": 5,
        "prerequisites": ["frac_simplify", "frac_mixed_improper"],
        "difficulty_base": "normal",
    },
    "frac_divide": {
        "display_name_zh": "分數除法",
        "domain": "fraction",
        "grade": 6,
        "prerequisites": ["frac_multiply"],
        "difficulty_base": "normal",
    },
    "frac_word_problem": {
        "display_name_zh": "分數應用題",
        "domain": "fraction",
        "grade": 5,
        "prerequisites": ["frac_multiply"],
        "difficulty_base": "hard",
    },
    "frac_of_quantity": {
        "display_name_zh": "求某量的幾分之幾",
        "domain": "fraction",
        "grade": 5,
        "prerequisites": ["frac_multiply"],
        "difficulty_base": "normal",
    },
    "frac_remain_then": {
        "display_name_zh": "先求剩下再求分率",
        "domain": "fraction",
        "grade": 5,
        "prerequisites": ["frac_of_quantity"],
        "difficulty_base": "hard",
    },

    # ----- Decimal Domain -----
    "decimal_basic": {
        "display_name_zh": "小數基本概念",
        "domain": "decimal",
        "grade": 5,
        "prerequisites": [],
        "difficulty_base": "easy",
    },
    "decimal_add_sub": {
        "display_name_zh": "小數加減",
        "domain": "decimal",
        "grade": 5,
        "prerequisites": ["decimal_basic"],
        "difficulty_base": "easy",
    },
    "decimal_multiply": {
        "display_name_zh": "小數乘法",
        "domain": "decimal",
        "grade": 5,
        "prerequisites": ["decimal_basic"],
        "difficulty_base": "normal",
    },
    "decimal_divide": {
        "display_name_zh": "小數除法",
        "domain": "decimal",
        "grade": 5,
        "prerequisites": ["decimal_multiply"],
        "difficulty_base": "normal",
    },
    "frac_decimal_convert": {
        "display_name_zh": "分數與小數互換",
        "domain": "decimal",
        "grade": 5,
        "prerequisites": ["frac_concept_basic", "decimal_basic"],
        "difficulty_base": "normal",
    },

    # ----- Percent & Ratio Domain -----
    "percent_concept": {
        "display_name_zh": "百分率基本概念",
        "domain": "percent",
        "grade": 5,
        "prerequisites": ["frac_decimal_convert"],
        "difficulty_base": "easy",
    },
    "percent_of_number": {
        "display_name_zh": "求某數的百分之幾",
        "domain": "percent",
        "grade": 5,
        "prerequisites": ["percent_concept", "decimal_multiply"],
        "difficulty_base": "normal",
    },
    "discount_calc": {
        "display_name_zh": "折扣計算",
        "domain": "percent",
        "grade": 5,
        "prerequisites": ["percent_of_number"],
        "difficulty_base": "normal",
    },
    "ratio_part_total": {
        "display_name_zh": "部分佔全體的比率",
        "domain": "percent",
        "grade": 5,
        "prerequisites": ["percent_concept"],
        "difficulty_base": "normal",
    },
    "ratio_compare": {
        "display_name_zh": "比率比較",
        "domain": "percent",
        "grade": 5,
        "prerequisites": ["ratio_part_total"],
        "difficulty_base": "hard",
    },

    # ----- Unit Conversion Domain -----
    "unit_length": {
        "display_name_zh": "長度單位換算",
        "domain": "unit_conversion",
        "grade": 5,
        "prerequisites": ["decimal_multiply"],
        "difficulty_base": "easy",
    },
    "unit_weight": {
        "display_name_zh": "重量單位換算",
        "domain": "unit_conversion",
        "grade": 5,
        "prerequisites": ["decimal_multiply"],
        "difficulty_base": "easy",
    },
    "unit_volume": {
        "display_name_zh": "容量單位換算",
        "domain": "unit_conversion",
        "grade": 5,
        "prerequisites": ["decimal_multiply"],
        "difficulty_base": "easy",
    },
    "unit_time": {
        "display_name_zh": "時間單位換算",
        "domain": "unit_conversion",
        "grade": 5,
        "prerequisites": [],
        "difficulty_base": "normal",
    },

    # ----- Volume Domain -----
    "volume_cube": {
        "display_name_zh": "正方體與長方體體積",
        "domain": "volume",
        "grade": 5,
        "prerequisites": ["decimal_multiply"],
        "difficulty_base": "normal",
    },
    "volume_composite": {
        "display_name_zh": "組合體體積",
        "domain": "volume",
        "grade": 5,
        "prerequisites": ["volume_cube"],
        "difficulty_base": "hard",
    },
    "volume_capacity": {
        "display_name_zh": "容積與容量",
        "domain": "volume",
        "grade": 5,
        "prerequisites": ["volume_cube", "unit_volume"],
        "difficulty_base": "normal",
    },

    # ----- Application / Life Domain -----
    "speed_distance_time": {
        "display_name_zh": "速度、距離、時間",
        "domain": "application",
        "grade": 5,
        "prerequisites": ["decimal_divide", "unit_time"],
        "difficulty_base": "hard",
    },
    "average_distribution": {
        "display_name_zh": "平均分配問題",
        "domain": "application",
        "grade": 5,
        "prerequisites": ["frac_divide", "decimal_divide"],
        "difficulty_base": "normal",
    },
    "shopping_problem": {
        "display_name_zh": "購物與找零問題",
        "domain": "application",
        "grade": 5,
        "prerequisites": ["discount_calc"],
        "difficulty_base": "normal",
    },

    # ----- Linear Equations (Grade 6+) -----
    "linear_one_step": {
        "display_name_zh": "一步驟一元一次方程式",
        "domain": "linear",
        "grade": 6,
        "prerequisites": [],
        "difficulty_base": "easy",
    },
    "linear_two_step": {
        "display_name_zh": "兩步驟一元一次方程式",
        "domain": "linear",
        "grade": 6,
        "prerequisites": ["linear_one_step"],
        "difficulty_base": "normal",
    },
    "linear_both_sides": {
        "display_name_zh": "含括號一元一次方程式",
        "domain": "linear",
        "grade": 6,
        "prerequisites": ["linear_two_step"],
        "difficulty_base": "hard",
    },

    # ----- Quadratic Equations -----
    "quadratic_factor": {
        "display_name_zh": "一元二次方程式（因式分解）",
        "domain": "quadratic",
        "grade": 6,
        "prerequisites": ["linear_both_sides"],
        "difficulty_base": "normal",
    },
    "quadratic_complete": {
        "display_name_zh": "一元二次方程式（配方法）",
        "domain": "quadratic",
        "grade": 6,
        "prerequisites": ["quadratic_factor"],
        "difficulty_base": "hard",
    },
    "quadratic_formula": {
        "display_name_zh": "一元二次方程式（公式解）",
        "domain": "quadratic",
        "grade": 6,
        "prerequisites": ["quadratic_complete"],
        "difficulty_base": "hard",
    },

    # ----- Four Operations -----
    "four_ops_order": {
        "display_name_zh": "四則運算（順序）",
        "domain": "arithmetic",
        "grade": 5,
        "prerequisites": [],
        "difficulty_base": "easy",
    },
    "four_ops_mixed": {
        "display_name_zh": "四則混合運算",
        "domain": "arithmetic",
        "grade": 5,
        "prerequisites": ["four_ops_order"],
        "difficulty_base": "normal",
    },

    # ----- Area -----
    "area_basic": {
        "display_name_zh": "面積基本計算",
        "domain": "geometry",
        "grade": 5,
        "prerequisites": ["decimal_multiply"],
        "difficulty_base": "easy",
    },
    "area_hectare": {
        "display_name_zh": "公頃與平方公尺換算",
        "domain": "geometry",
        "grade": 5,
        "prerequisites": ["area_basic"],
        "difficulty_base": "normal",
    },
}


# ---------------------------------------------------------------------------
# Mapping: topic_tags / concept_points → concept_ids
# ---------------------------------------------------------------------------

# Maps topic_tags from existing question packs to concept_ids
TOPIC_TAG_TO_CONCEPT: Dict[str, List[str]] = {
    "ratio_percent": ["percent_concept", "percent_of_number", "ratio_part_total"],
    "discount": ["discount_calc"],
    "fractions": ["frac_multiply", "frac_concept_basic"],
    "fraction": ["frac_multiply", "frac_concept_basic", "frac_word_problem"],
    "multiply": ["frac_multiply", "decimal_multiply"],
    "unit_conversion": ["unit_length", "unit_weight", "unit_volume"],
    "volume": ["volume_cube", "volume_capacity"],
    "area": ["area_basic", "area_hectare"],
    "time": ["unit_time", "speed_distance_time"],
    "decimal": ["decimal_basic", "decimal_multiply", "frac_decimal_convert"],
    "percent": ["percent_concept", "percent_of_number"],
    "ratio": ["ratio_part_total", "ratio_compare"],
    "g5s": [],  # generic tag, no specific concept
    "shopping_discount": ["discount_calc", "shopping_problem"],
    "distance_time": ["speed_distance_time"],
    "remaining_amount": ["frac_remain_then"],
    "average_distribution": ["average_distribution"],
}

# Maps concept_points (free text) to concept_ids — best-effort
CONCEPT_POINT_TO_CONCEPT: Dict[str, str] = {
    "求某數的百分之幾：用乘法": "percent_of_number",
    "百分率要除以 100": "percent_concept",
    "打折＝剩下百分率": "discount_calc",
    "現價 = 原價 × 剩下百分率": "discount_calc",
    "分數乘法：分子乘分子、分母乘分母": "frac_multiply",
    "1 公升 = 1000 毫升": "unit_volume",
    "1 公頃 = 10,000 平方公尺": "area_hectare",
    "換算倍率固定": "unit_length",
    "公升轉毫升要乘 1000": "unit_volume",
    "分數與小數可以互相轉換": "frac_decimal_convert",
    "合計比率可以直接相加": "ratio_part_total",
    "小數轉百分率要乘 100": "percent_concept",
    "約分是分子分母同除最大公因數": "frac_simplify",
    "distance=speed×time": "speed_distance_time",
    "先換單位再運算": "unit_length",
    "先換時間單位": "unit_time",
    "先算剩下量": "frac_remain_then",
    "分率乘總量": "frac_of_quantity",
    "列算式": "four_ops_order",
    "圈重點": "four_ops_order",
    "查合理性": "four_ops_order",
    "算步驟": "four_ops_order",
    "部分除以全體": "ratio_part_total",
    "小數點移動": "decimal_multiply",
}


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def get_concept(concept_id: str) -> Optional[Dict[str, Any]]:
    """Return concept record or None."""
    return CONCEPT_TAXONOMY.get(concept_id)


def get_display_name(concept_id: str) -> str:
    """Return human-readable Chinese name."""
    c = CONCEPT_TAXONOMY.get(concept_id)
    return c["display_name_zh"] if c else concept_id


def get_prerequisites(concept_id: str) -> List[str]:
    """Return list of prerequisite concept_ids."""
    c = CONCEPT_TAXONOMY.get(concept_id)
    return list(c.get("prerequisites", [])) if c else []


def get_all_prerequisites(concept_id: str) -> List[str]:
    """Return transitive closure of all prerequisites (BFS)."""
    visited = set()
    queue = list(get_prerequisites(concept_id))
    result = []
    while queue:
        cid = queue.pop(0)
        if cid in visited:
            continue
        visited.add(cid)
        result.append(cid)
        queue.extend(get_prerequisites(cid))
    return result


def resolve_concept_ids(
    topic_tags: List[str],
    concept_points: Optional[List[str]] = None,
) -> List[str]:
    """Resolve topic_tags + concept_points to a deduplicated list of concept_ids."""
    ids: set = set()
    for tag in topic_tags:
        ids.update(TOPIC_TAG_TO_CONCEPT.get(tag, []))
    if concept_points:
        for cp in concept_points:
            cid = CONCEPT_POINT_TO_CONCEPT.get(cp)
            if cid:
                ids.add(cid)
    return sorted(ids)


def list_domains() -> List[str]:
    """Return sorted unique domain names."""
    return sorted({c["domain"] for c in CONCEPT_TAXONOMY.values()})


def concepts_by_domain(domain: str) -> List[str]:
    """Return concept_ids filtered by domain."""
    return [cid for cid, c in CONCEPT_TAXONOMY.items() if c["domain"] == domain]


def all_concept_ids() -> List[str]:
    """Return all concept_ids."""
    return sorted(CONCEPT_TAXONOMY.keys())
