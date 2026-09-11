"""Các hàm hỗ trợ thuần túy cho thành phần gợi ý dựa trên quy tắc."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import math
import re
import unicodedata


@dataclass(frozen=True)
class MatchingWeights:
    semantic: Decimal
    skill: Decimal
    experience: Decimal
    education: Decimal
    required_skill_multiplier: Decimal = Decimal("2.000")


# Giá trị mặc định cho bản cài đặt mới; việc chấm điểm vẫn cần một bản ghi đang active.
DEFAULT_MATCHING_WEIGHTS = MatchingWeights(
    semantic=Decimal("0.350"),
    skill=Decimal("0.400"),
    experience=Decimal("0.200"),
    education=Decimal("0.050"),
    required_skill_multiplier=Decimal("2.000"),
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
    """Trả về bậc học vấn cao nhất nhận diện được trong dữ liệu tự do của ứng viên."""
    normalized = normalize_matching_text(value)
    for level in sorted(_DEGREE_PATTERNS, reverse=True):
        if any(re.search(pattern, normalized) for pattern in _DEGREE_PATTERNS[level]):
            return level
    return 0


def required_degree_level(requirements: str) -> int:
    """Tìm thận trọng yêu cầu học vấn rõ ràng, hoặc trả về 0 nếu không có."""
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
    """Trả về hợp các khoảng thời gian làm việc nửa mở hợp lệ, tính theo năm."""
    today = today or date.today()
    normalized = []
    for start_date, end_date, is_current in intervals:
        if start_date is None:
            continue
        effective_end = today if is_current else end_date
        if effective_end is None or effective_end < start_date:
            continue
        normalized.append((start_date, effective_end))
    if not normalized:
        return 0.0

    normalized.sort()
    merged = [normalized[0]]
    for start_date, end_date in normalized[1:]:
        previous_start, previous_end = merged[-1]
        if start_date <= previous_end:
            merged[-1] = (previous_start, max(previous_end, end_date))
        else:
            merged.append((start_date, end_date))
    total_days = sum((end - start).days for start, end in merged)
    return total_days / 365.25


def experience_score(total_years: float, experience_level: str) -> float:
    if not math.isfinite(total_years) or total_years < 0:
        raise ValueError("Số năm kinh nghiệm phải hữu hạn và không âm.")
    required = EXPERIENCE_YEARS_REQUIRED.get(experience_level or "", 0)
    if required == 0:
        return 1.0
    return min(1.0, total_years / required)


def skill_match_score(candidate_skill_ids, job_skills, multiplier) -> tuple[float | None, dict]:
    """Tính K-rho sau khi loại trùng theo định danh skill ổn định."""
    multiplier = float(multiplier)
    if not math.isfinite(multiplier) or multiplier < 1:
        raise ValueError("Hệ số kỹ năng bắt buộc phải hữu hạn và không nhỏ hơn 1.")

    candidate_ids = set(candidate_skill_ids)
    required = {}
    preferred = {}
    for item in job_skills:
        skill_id = str(item["id"])
        if item.get("is_required", True):
            required[skill_id] = item
            preferred.pop(skill_id, None)
        elif skill_id not in required:
            preferred[skill_id] = item
    if not required and not preferred:
        return None, {
            "required_count": 0,
            "preferred_count": 0,
            "matched_required_count": 0,
            "matched_preferred_count": 0,
        }

    matched_required = candidate_ids & required.keys()
    matched_preferred = candidate_ids & preferred.keys()
    denominator = multiplier * len(required) + len(preferred)
    score = (multiplier * len(matched_required) + len(matched_preferred)) / denominator
    return score, {
        "required_count": len(required),
        "preferred_count": len(preferred),
        "matched_required_count": len(matched_required),
        "matched_preferred_count": len(matched_preferred),
        "required": required,
        "preferred": preferred,
    }


def education_score(candidate_level: str | None, required_level: str | None) -> float | None:
    from apps.candidates.models import DEGREE_LEVEL_RANK, DegreeLevel

    if required_level in (None, "", DegreeLevel.NONE):
        return None
    if required_level not in DEGREE_LEVEL_RANK:
        raise ValueError("Bậc học vấn yêu cầu không hợp lệ.")
    if candidate_level is None:
        return 0.0
    if candidate_level not in DEGREE_LEVEL_RANK:
        raise ValueError("Bậc học vấn ứng viên không hợp lệ.")
    gap = max(0, DEGREE_LEVEL_RANK[required_level] - DEGREE_LEVEL_RANK[candidate_level])
    return max(0.0, 1.0 - 0.25 * gap)


def aggregate_match_score(components: dict, weights: MatchingWeights):
    """Chuẩn hóa trọng số trên các tiêu chí áp dụng và tính điểm từ 0 đến 100."""
    original = {
        "semantic": Decimal(weights.semantic),
        "skill": Decimal(weights.skill),
        "experience": Decimal(weights.experience),
        "education": Decimal(weights.education),
    }
    for name, weight in original.items():
        if not weight.is_finite() or weight < 0:
            raise ValueError(f"Trọng số {name} phải hữu hạn và không âm.")
    if sum(original.values()) != Decimal("1"):
        raise ValueError("Tổng các trọng số phải bằng 1.")

    applicable = {}
    for name, value in components.items():
        if value is None:
            continue
        value = Decimal(str(value))
        if not value.is_finite() or not Decimal("0") <= value <= Decimal("1"):
            raise ValueError(f"Điểm thành phần {name} phải thuộc [0, 1].")
        applicable[name] = value

    denominator = sum((original[name] for name in applicable), Decimal("0"))
    if denominator == 0:
        return None, {name: Decimal("0") for name in original}
    normalized = {
        name: (original[name] / denominator if name in applicable else Decimal("0"))
        for name in original
    }
    score = Decimal("100") * sum(
        normalized[name] * value for name, value in applicable.items()
    )
    return score.quantize(Decimal("0.01")), normalized
