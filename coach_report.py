from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Literal, Optional, TypedDict


Quadrant = Literal["A", "B", "C", "D"]


class HintInfo(TypedDict, total=False):
    shown_levels: List[int]
    shown_count: int
    first_shown_at: int
    total_hint_ms: int


class StepsInfo(TypedDict, total=False):
    used_next_step: bool
    shown_solution: bool


class AttemptEventLike(TypedDict, total=False):
    kind: str
    ts_start: int
    ts_end: int
    is_correct: bool
    attempts_count: int
    hint: HintInfo
    steps: StepsInfo


@dataclass
class TopicStats:
    kind: str
    n: int = 0
    correct: int = 0
    independent_correct: int = 0  # A
    hint_correct: int = 0  # B
    hint_wrong: int = 0  # C
    nohint_wrong: int = 0  # D
    hint_level_hist: Dict[str, int] = None
    first_try_correct: int = 0
    avg_time_ms_sum: int = 0

    def __post_init__(self) -> None:
        if self.hint_level_hist is None:
            self.hint_level_hist = {"none": 0, "L1": 0, "L2": 0, "L3": 0, "solution": 0}

    @property
    def avg_time_ms(self) -> int:
        if self.n <= 0:
            return 0
        return round(self.avg_time_ms_sum / self.n)


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        n = int(x)
        return n
    except Exception:
        return default


def _shown_levels(evt: AttemptEventLike) -> List[int]:
    hint = evt.get("hint") or {}
    levels = hint.get("shown_levels")
    return levels if isinstance(levels, list) else []


def _shown_solution(evt: AttemptEventLike) -> bool:
    steps = evt.get("steps") or {}
    return bool(steps.get("shown_solution"))


def classify_quadrant(evt: AttemptEventLike) -> Quadrant:
    is_correct = bool(evt.get("is_correct"))
    shown_levels = _shown_levels(evt)
    shown_solution = _shown_solution(evt)
    attempts_count = max(1, _safe_int(evt.get("attempts_count"), 1))

    has_hint = bool(shown_levels) or shown_solution

    if is_correct and (not has_hint) and attempts_count == 1:
        return "A"
    if is_correct and has_hint:
        return "B"
    if (not is_correct) and has_hint:
        return "C"
    return "D"


def hint_depth_key(evt: AttemptEventLike) -> str:
    if _shown_solution(evt):
        return "solution"
    shown_levels = _shown_levels(evt)
    if not shown_levels:
        return "none"
    try:
        max_lv = max(int(x) for x in shown_levels)
    except Exception:
        return "none"
    if max_lv >= 3:
        return "L3"
    if max_lv >= 2:
        return "L2"
    if max_lv >= 1:
        return "L1"
    return "none"


def _bump(stats: TopicStats, evt: AttemptEventLike) -> None:
    q = classify_quadrant(evt)
    dkey = hint_depth_key(evt)

    stats.n += 1
    is_correct = bool(evt.get("is_correct"))
    if is_correct:
        stats.correct += 1

    if q == "A":
        stats.independent_correct += 1
    elif q == "B":
        stats.hint_correct += 1
    elif q == "C":
        stats.hint_wrong += 1
    else:
        stats.nohint_wrong += 1

    stats.hint_level_hist[dkey] = int(stats.hint_level_hist.get(dkey, 0)) + 1

    attempts_count = max(1, _safe_int(evt.get("attempts_count"), 1))
    if is_correct and attempts_count == 1:
        stats.first_try_correct += 1

    ts_start = _safe_int(evt.get("ts_start"), 0)
    ts_end = _safe_int(evt.get("ts_end"), 0)
    stats.avg_time_ms_sum += max(0, ts_end - ts_start)


def aggregate(attempts: Iterable[AttemptEventLike]) -> Dict[str, Any]:
    overall = TopicStats(kind="overall")
    by_kind: Dict[str, TopicStats] = {}

    for evt in attempts:
        kind = str(evt.get("kind") or "unknown")
        st = by_kind.get(kind)
        if st is None:
            st = TopicStats(kind=kind)
            by_kind[kind] = st

        _bump(st, evt)
        _bump(overall, evt)

    kind_list = sorted(by_kind.values(), key=lambda x: x.n, reverse=True)

    kpi = {
        "total": overall.n,
        "accuracy": (overall.correct / overall.n) if overall.n else 0.0,
        "independent_rate": (overall.independent_correct / overall.n) if overall.n else 0.0,
        "hint_dependency": ((overall.hint_correct + overall.hint_wrong) / overall.n) if overall.n else 0.0,
        "first_try_accuracy": (overall.first_try_correct / overall.n) if overall.n else 0.0,
        "avg_time_ms": overall.avg_time_ms,
    }

    def to_dict(s: TopicStats) -> Dict[str, Any]:
        return {
            "kind": s.kind,
            "n": s.n,
            "correct": s.correct,
            "independent_correct": s.independent_correct,
            "hint_correct": s.hint_correct,
            "hint_wrong": s.hint_wrong,
            "nohint_wrong": s.nohint_wrong,
            "hint_level_hist": dict(s.hint_level_hist),
            "first_try_correct": s.first_try_correct,
            "avg_time_ms": s.avg_time_ms,
        }

    return {
        "overall": to_dict(overall),
        "by_kind": [to_dict(x) for x in kind_list],
        "kpi": kpi,
    }
