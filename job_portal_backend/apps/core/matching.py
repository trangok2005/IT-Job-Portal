"""Pure helpers for the rule-based recommendation components."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import re
import unicodedata


@dataclass(frozen=True)
class MatchingWeights:
    semantic: Decimal
    skill: Decimal
    experience: Decimal
    education: Decimal


# Used when an installation has no active MatchingWeightConfig row.
DEFAULT_MATCHING_WEIGHTS = MatchingWeights(
    semantic=Decimal("0.600"),
    skill=Decimal("0.250"),
    experience=Decimal("0.100"),
    education=Decimal("0.050"),
)

EXPERIENCE_YEARS_REQUIRED = {
    "": 0,
    "ENTRY": 0,
    "JUNIOR": 1,
    "MID_SENIOR": 3,
    "LEAD": 5,
}

_DEGREE_PATTERNS = {
    4: (r"\bdoctorate\b", r"\bph\s*\.?d\.?\b", r"\btien si\b"),
    3: (r"\bmaster(?:'s)?\b", r"\bthac si\b"),
    2: (
        r"\bbachelor(?:'s)?\b",
        r"\bengineer(?:ing)?(?: degree)?\b",
        r"\bcu nhan\b",
        r"\bky su\b",
        r"\bdai hoc\b",
    ),
    1: (r"\bcollege\b", r"\bassociate(?:'s)?\b", r"\bcao dang\b"),
}
_REQUIRED_BACHELOR_PATTERNS = (
    r"\bbachelor(?:'s)?\b",
    r"\bengineer(?:'s)? degree\b",
    r"\bdegree (?:in )?engineering\b",
    r"\bcu nhan\b",
    r"\bdai hoc\b",
    r"\b(?:bang|tot nghiep|trinh do)(?: [a-z]+){0,3} ky su\b",
)
_NO_DEGREE_PATTERNS = (
    r"\bkhong (?:bat buoc|yeu cau|can)(?: co)? bang\b",
    r"\bkhong yeu cau trinh do\b",
    r"\bno (?:college |university )?degree (?:is )?required\b",
    r"\bdegree (?:is )?not required\b",
)


def normalize_matching_text(value: str) -> str:
    value = unicodedata.normalize("NFD", value or "")
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    value = value.replace("đ", "d").replace("Đ", "D")
    return re.sub(r"\s+", " ", value.lower()).strip()


def recognized_degree_level(value: str) -> int:
    """Return the highest recognized degree in free-form candidate data."""
    normalized = normalize_matching_text(value)
    for level in sorted(_DEGREE_PATTERNS, reverse=True):
        if any(re.search(pattern, normalized) for pattern in _DEGREE_PATTERNS[level]):
            return level
    return 0


def required_degree_level(requirements: str) -> int:
    """Conservatively find an explicit degree requirement, or zero if absent."""
    normalized = normalize_matching_text(requirements)
    if any(re.search(pattern, normalized) for pattern in _NO_DEGREE_PATTERNS):
        return 0
    for level in (4, 3):
        if any(re.search(pattern, normalized) for pattern in _DEGREE_PATTERNS[level]):
            return level
    if any(re.search(pattern, normalized) for pattern in _REQUIRED_BACHELOR_PATTERNS):
        return 2
    if any(re.search(pattern, normalized) for pattern in _DEGREE_PATTERNS[1]):
        return 1
    return 0


def total_experience_years(intervals, today: date | None = None) -> float:
    """Sum valid intervals independently; overlapping employment is intentional."""
    today = today or date.today()
    total_days = 0
    for start_date, end_date, is_current in intervals:
        if start_date is None:
            continue
        effective_end = today if is_current else end_date
        if effective_end is None or effective_end < start_date:
            continue
        total_days += (effective_end - start_date).days
    return total_days / 365.25


def experience_score(total_years: float, experience_level: str) -> float:
    required = EXPERIENCE_YEARS_REQUIRED.get(experience_level or "", 0)
    if required == 0:
        return 100.0
    return min(100.0, max(0.0, total_years / required * 100.0))
