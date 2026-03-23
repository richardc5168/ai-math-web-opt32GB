"""Lightweight Gamification Hooks — Mastery-bound rewards.

All rewards are gated by genuine mastery achievements, NOT time-on-task or
click counts. No heavy animations — just data structures and unlock logic.

Features:
- Concept zone unlock (mastery ≥ APPROACHING_MASTERY)
- Boss challenge unlock (mastery = MASTERED on all prerequisites)
- Badge system (milestone-based)
- Streak tracking (consecutive day practice)

Usage:
    from learning.gamification import (
        check_unlocks, compute_badges, update_streak,
        compute_zone_progress,
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from .concept_state import MasteryLevel, StudentConceptState
from .concept_taxonomy import (
    CONCEPT_TAXONOMY, list_domains, concepts_by_domain,
    get_all_prerequisites, get_display_name,
)

# Numeric ordering for level comparison (str enum has no natural ordering)
_LEVEL_ORDER = {
    MasteryLevel.UNBUILT: 0,
    MasteryLevel.DEVELOPING: 1,
    MasteryLevel.APPROACHING_MASTERY: 2,
    MasteryLevel.MASTERED: 3,
    MasteryLevel.REVIEW_NEEDED: 0,  # treat as needing work
}


# ---------------------------------------------------------------------------
# Enums and Constants
# ---------------------------------------------------------------------------

class BadgeType(str, Enum):
    FIRST_MASTERY = "first_mastery"          # First concept mastered
    DOMAIN_EXPLORER = "domain_explorer"      # 3+ concepts attempted in a domain
    DOMAIN_MASTER = "domain_master"          # All concepts mastered in a domain
    STREAK_3 = "streak_3"                    # 3-day practice streak
    STREAK_7 = "streak_7"                    # 7-day practice streak
    STREAK_14 = "streak_14"                  # 14-day practice streak
    NO_HINT_HERO = "no_hint_hero"            # 5+ correct without hints in a row
    COMEBACK = "comeback"                    # Recovered from REVIEW_NEEDED to MASTERED
    TEN_CONCEPTS = "ten_concepts"            # 10 concepts at APPROACHING or above


BADGE_DISPLAY = {
    BadgeType.FIRST_MASTERY: {"zh": "初次掌握", "icon": "🌟", "description_zh": "第一個觀念掌握了！"},
    BadgeType.DOMAIN_EXPLORER: {"zh": "領域探索者", "icon": "🔍", "description_zh": "在一個領域嘗試了 3 個以上觀念"},
    BadgeType.DOMAIN_MASTER: {"zh": "領域大師", "icon": "👑", "description_zh": "一個領域的所有觀念都掌握了！"},
    BadgeType.STREAK_3: {"zh": "連續三天", "icon": "🔥", "description_zh": "連續練習 3 天"},
    BadgeType.STREAK_7: {"zh": "一週達人", "icon": "💪", "description_zh": "連續練習 7 天"},
    BadgeType.STREAK_14: {"zh": "兩週堅持", "icon": "⭐", "description_zh": "連續練習 14 天"},
    BadgeType.NO_HINT_HERO: {"zh": "獨立思考", "icon": "🧠", "description_zh": "連續 5 題不看提示就答對"},
    BadgeType.COMEBACK: {"zh": "逆轉勝", "icon": "🔄", "description_zh": "從忘記到重新掌握"},
    BadgeType.TEN_CONCEPTS: {"zh": "十概念達人", "icon": "🏆", "description_zh": "10 個觀念接近掌握或已掌握"},
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class UnlockStatus:
    """Whether a concept zone or boss challenge is unlocked."""
    concept_id: str
    zone_unlocked: bool = False
    boss_unlocked: bool = False
    unlock_reason: str = ""


@dataclass
class Badge:
    """An earned badge."""
    badge_type: BadgeType
    display_name_zh: str
    icon: str
    description_zh: str
    earned_at: Optional[str] = None  # ISO timestamp


@dataclass
class Streak:
    """Practice streak state."""
    current_streak_days: int = 0
    longest_streak_days: int = 0
    last_practice_date: Optional[str] = None  # YYYY-MM-DD


@dataclass
class BossChallenge:
    """A boss challenge for a concept."""
    concept_id: str
    display_name_zh: str
    challenge_concept_ids: List[str] = field(default_factory=list)
    prereq_depth: int = 0
    difficulty: str = "easy"  # easy / normal / hard
    is_available: bool = False


@dataclass
class ZoneProgress:
    """Aggregate progress within a domain-based zone."""
    zone_id: str               # domain name (e.g. "fraction")
    display_name_zh: str
    total_concepts: int = 0
    mastered_count: int = 0
    approaching_count: int = 0
    developing_count: int = 0
    unbuilt_count: int = 0
    progress_pct: float = 0.0  # 0.0–100.0
    is_complete: bool = False


# Chinese display names for domain-based zones
ZONE_DISPLAY_NAMES: Dict[str, str] = {
    "fraction": "分數王國",
    "decimal": "小數領域",
    "percent": "百分率領域",
    "unit_conversion": "單位換算區",
    "volume": "體積空間",
    "application": "生活應用區",
    "linear": "方程式基地",
    "quadratic": "二次方程式基地",
    "arithmetic": "四則運算區",
    "geometry": "幾何面積區",
}


@dataclass
class GamificationState:
    """Full gamification state for a student."""
    unlocks: List[UnlockStatus] = field(default_factory=list)
    badges: List[Badge] = field(default_factory=list)
    streak: Streak = field(default_factory=Streak)
    zone_progress: List[ZoneProgress] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Unlock logic
# ---------------------------------------------------------------------------

def check_unlocks(
    states: List[StudentConceptState],
) -> List[UnlockStatus]:
    """Check which concept zones and boss challenges are unlocked.

    Zone unlock: mastery ≥ APPROACHING_MASTERY
    Boss unlock: mastery = MASTERED on ALL prerequisites of the concept
    """
    mastery_map: Dict[str, MasteryLevel] = {
        s.concept_id: s.mastery_level for s in states
    }

    results = []
    for state in states:
        cid = state.concept_id
        concept_info = CONCEPT_TAXONOMY.get(cid)

        # Zone unlock: student has reached at least APPROACHING_MASTERY
        zone_ok = _LEVEL_ORDER.get(state.mastery_level, 0) >= _LEVEL_ORDER[MasteryLevel.APPROACHING_MASTERY]

        # Boss unlock: all prerequisites must be MASTERED
        boss_ok = False
        if state.mastery_level == MasteryLevel.MASTERED:
            prereqs = (concept_info or {}).get("prerequisites", [])
            if prereqs:
                boss_ok = all(
                    mastery_map.get(p, MasteryLevel.UNBUILT) == MasteryLevel.MASTERED
                    for p in prereqs
                )
            else:
                # No prerequisites → boss unlocked if mastered
                boss_ok = True

        reason = ""
        if zone_ok:
            reason = "觀念接近掌握，解鎖進階區域"
        if boss_ok:
            reason = "觀念及前置觀念皆已掌握，解鎖挑戰關卡"

        results.append(UnlockStatus(
            concept_id=cid,
            zone_unlocked=zone_ok,
            boss_unlocked=boss_ok,
            unlock_reason=reason,
        ))

    return results


# ---------------------------------------------------------------------------
# Zone progress
# ---------------------------------------------------------------------------

def compute_zone_progress(
    states: List[StudentConceptState],
) -> List[ZoneProgress]:
    """Compute aggregate progress for each domain-based zone.

    Returns one ZoneProgress per domain, regardless of whether the student
    has any state entries for that domain.
    """
    mastery_map: Dict[str, MasteryLevel] = {
        s.concept_id: s.mastery_level for s in states
    }

    results: List[ZoneProgress] = []
    for domain in list_domains():
        cids = concepts_by_domain(domain)
        if not cids:
            continue

        total = len(cids)
        mastered = 0
        approaching = 0
        developing = 0
        unbuilt = 0

        for cid in cids:
            level = mastery_map.get(cid, MasteryLevel.UNBUILT)
            order = _LEVEL_ORDER.get(level, 0)
            if level == MasteryLevel.MASTERED:
                mastered += 1
            elif order >= _LEVEL_ORDER[MasteryLevel.APPROACHING_MASTERY]:
                approaching += 1
            elif order >= _LEVEL_ORDER[MasteryLevel.DEVELOPING]:
                developing += 1
            else:
                unbuilt += 1

        # Progress: mastered = 100%, approaching = 70%, developing = 30%
        weighted = mastered * 100.0 + approaching * 70.0 + developing * 30.0
        progress_pct = round(weighted / total, 1) if total else 0.0

        results.append(ZoneProgress(
            zone_id=domain,
            display_name_zh=ZONE_DISPLAY_NAMES.get(domain, domain),
            total_concepts=total,
            mastered_count=mastered,
            approaching_count=approaching,
            developing_count=developing,
            unbuilt_count=unbuilt,
            progress_pct=progress_pct,
            is_complete=(mastered == total),
        ))

    return results


# ---------------------------------------------------------------------------
# Boss challenge logic
# ---------------------------------------------------------------------------

def generate_boss_challenge(
    concept_id: str,
    states: List[StudentConceptState],
) -> BossChallenge:
    """Generate a boss challenge for a concept.

    Difficulty is scaled by prerequisite depth:
      0 prereqs → easy, 1-3 → normal, 4+ → hard
    Availability requires concept + all transitive prereqs MASTERED.
    """
    mastery_map: Dict[str, MasteryLevel] = {
        s.concept_id: s.mastery_level for s in states
    }

    prereqs = get_all_prerequisites(concept_id)
    depth = len(prereqs)
    challenge_ids = [concept_id] + prereqs

    if depth == 0:
        difficulty = "easy"
    elif depth <= 3:
        difficulty = "normal"
    else:
        difficulty = "hard"

    # Available only if concept + all prereqs are MASTERED
    concept_mastered = mastery_map.get(concept_id) == MasteryLevel.MASTERED
    prereqs_mastered = all(
        mastery_map.get(p) == MasteryLevel.MASTERED for p in prereqs
    )
    is_available = concept_mastered and prereqs_mastered

    return BossChallenge(
        concept_id=concept_id,
        display_name_zh=get_display_name(concept_id),
        challenge_concept_ids=challenge_ids,
        prereq_depth=depth,
        difficulty=difficulty,
        is_available=is_available,
    )


def get_available_bosses(
    states: List[StudentConceptState],
) -> List[BossChallenge]:
    """Return all boss challenges that are currently available."""
    mastered_ids = {
        s.concept_id for s in states
        if s.mastery_level == MasteryLevel.MASTERED
    }
    if not mastered_ids:
        return []

    results = []
    for cid in mastered_ids:
        boss = generate_boss_challenge(cid, states)
        if boss.is_available:
            results.append(boss)
    return sorted(results, key=lambda b: b.concept_id)


# ---------------------------------------------------------------------------
# Badge logic
# ---------------------------------------------------------------------------

def compute_badges(
    states: List[StudentConceptState],
    *,
    streak: Optional[Streak] = None,
    consecutive_no_hint_correct: int = 0,
    recovered_concepts: Optional[Set[str]] = None,
) -> List[Badge]:
    """Compute which badges are earned.

    All badges are based on mastery achievements, not vanity metrics.
    """
    badges: List[Badge] = []
    recovered_concepts = recovered_concepts or set()

    mastered = [s for s in states if s.mastery_level == MasteryLevel.MASTERED]
    approaching_or_above = [
        s for s in states
        if _LEVEL_ORDER.get(s.mastery_level, 0) >= _LEVEL_ORDER[MasteryLevel.APPROACHING_MASTERY]
    ]

    # First mastery
    if mastered:
        badges.append(_make_badge(BadgeType.FIRST_MASTERY))

    # Domain explorer: 3+ concepts attempted in any domain
    domain_counts: Dict[str, int] = {}
    for s in states:
        if s.attempts_total > 0:
            info = CONCEPT_TAXONOMY.get(s.concept_id, {})
            domain = info.get("domain", "unknown")
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
    if any(c >= 3 for c in domain_counts.values()):
        badges.append(_make_badge(BadgeType.DOMAIN_EXPLORER))

    # Domain master: all concepts in a domain mastered
    mastered_ids = {s.concept_id for s in mastered}
    domain_concepts: Dict[str, List[str]] = {}
    for cid, info in CONCEPT_TAXONOMY.items():
        domain = info.get("domain", "unknown")
        domain_concepts.setdefault(domain, []).append(cid)
    for domain, cids in domain_concepts.items():
        if cids and all(c in mastered_ids for c in cids):
            badges.append(_make_badge(BadgeType.DOMAIN_MASTER))
            break  # one badge is enough

    # Streaks
    if streak:
        if streak.current_streak_days >= 14:
            badges.append(_make_badge(BadgeType.STREAK_14))
        elif streak.current_streak_days >= 7:
            badges.append(_make_badge(BadgeType.STREAK_7))
        elif streak.current_streak_days >= 3:
            badges.append(_make_badge(BadgeType.STREAK_3))

    # No-hint hero
    if consecutive_no_hint_correct >= 5:
        badges.append(_make_badge(BadgeType.NO_HINT_HERO))

    # Comeback
    if recovered_concepts:
        badges.append(_make_badge(BadgeType.COMEBACK))

    # Ten concepts
    if len(approaching_or_above) >= 10:
        badges.append(_make_badge(BadgeType.TEN_CONCEPTS))

    return badges


def _make_badge(badge_type: BadgeType) -> Badge:
    info = BADGE_DISPLAY.get(badge_type, {})
    return Badge(
        badge_type=badge_type,
        display_name_zh=info.get("zh", badge_type.value),
        icon=info.get("icon", ""),
        description_zh=info.get("description_zh", ""),
    )


# ---------------------------------------------------------------------------
# Streak tracking
# ---------------------------------------------------------------------------

def update_streak(current: Streak, practice_date: str) -> Streak:
    """Update streak based on today's practice date (YYYY-MM-DD).

    Returns a new Streak (does not mutate input).
    """
    if current.last_practice_date == practice_date:
        # Already practiced today, no change
        return Streak(
            current_streak_days=current.current_streak_days,
            longest_streak_days=current.longest_streak_days,
            last_practice_date=current.last_practice_date,
        )

    if current.last_practice_date is None:
        # First ever practice
        return Streak(
            current_streak_days=1,
            longest_streak_days=max(1, current.longest_streak_days),
            last_practice_date=practice_date,
        )

    # Check if consecutive (simple YYYY-MM-DD comparison)
    from datetime import date as _date

    try:
        last = _date.fromisoformat(current.last_practice_date)
        today = _date.fromisoformat(practice_date)
        diff = (today - last).days
    except (ValueError, TypeError):
        diff = 999

    if diff == 1:
        new_streak = current.current_streak_days + 1
    elif diff == 0:
        new_streak = current.current_streak_days
    else:
        new_streak = 1  # streak broken

    return Streak(
        current_streak_days=new_streak,
        longest_streak_days=max(new_streak, current.longest_streak_days),
        last_practice_date=practice_date,
    )


# ---------------------------------------------------------------------------
# Badge delta detection
# ---------------------------------------------------------------------------

def detect_new_badges(
    current_badges: List[Badge],
    previous_badge_types: Set[str],
) -> List[Badge]:
    """Return only badges that are newly earned (not in previous set)."""
    return [b for b in current_badges if b.badge_type.value not in previous_badge_types]


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def gamification_to_dict(state: GamificationState) -> Dict[str, Any]:
    """Convert to JSON-serializable dict."""
    return {
        "unlocks": [
            {
                "concept_id": u.concept_id,
                "zone_unlocked": u.zone_unlocked,
                "boss_unlocked": u.boss_unlocked,
                "unlock_reason": u.unlock_reason,
            }
            for u in state.unlocks
        ],
        "badges": [
            {
                "badge_type": b.badge_type.value,
                "display_name_zh": b.display_name_zh,
                "icon": b.icon,
                "description_zh": b.description_zh,
            }
            for b in state.badges
        ],
        "streak": {
            "current_streak_days": state.streak.current_streak_days,
            "longest_streak_days": state.streak.longest_streak_days,
            "last_practice_date": state.streak.last_practice_date,
        },
        "zone_progress": [
            {
                "zone_id": z.zone_id,
                "display_name_zh": z.display_name_zh,
                "total_concepts": z.total_concepts,
                "mastered_count": z.mastered_count,
                "approaching_count": z.approaching_count,
                "developing_count": z.developing_count,
                "unbuilt_count": z.unbuilt_count,
                "progress_pct": z.progress_pct,
                "is_complete": z.is_complete,
            }
            for z in state.zone_progress
        ],
    }
