"""UC-03 orchestration: hard filters first, then semantic ranking or fallback."""
import logging
import re
from dataclasses import dataclass

from django.db.models import QuerySet

from apps.core.embedding_text_builders import build_query_text
from apps.jobs import selectors
from apps.jobs.models import JobPost
from apps.skills import selectors as skill_selectors
from integrations.gemini.embeddings import EmbeddingError, embed_query


logger = logging.getLogger(__name__)

NO_RESULTS_MESSAGE = (
    "Không tìm thấy công việc phù hợp với yêu cầu của bạn. "
    "Hãy thử bỏ bớt bộ lọc hoặc đổi từ khóa."
)


def normalize_basic_keyword(keyword: str) -> str:
    """Expand common developer shorthand for deterministic basic search."""
    return re.sub(r"\bdev\b", "developer", keyword, flags=re.IGNORECASE)


def apply_explicit_developer_intent(queryset, keyword: str):
    """Honor explicit "<technology> developer" intent before semantic rank."""
    if not re.search(r"\b(dev|developer)\b", keyword, flags=re.IGNORECASE):
        return queryset
    queryset = queryset.filter(title__icontains="Developer")
    for skill_id in skill_selectors.get_skill_ids_mentioned_in_text(keyword):
        queryset = queryset.filter(job_skills__skill_id=skill_id)
    return queryset.distinct()


@dataclass(frozen=True)
class SearchFilters:
    workplace_type: str | None = None
    location: str | None = None
    salary_min: int | None = None
    experience_level: str | None = None
    job_type: str | None = None

    def is_empty(self) -> bool:
        return not any(
            (
                self.location,
                self.workplace_type,
                self.salary_min is not None,
                self.experience_level,
                self.job_type,
            )
        )


@dataclass(frozen=True)
class SearchResult:
    queryset: QuerySet[JobPost]
    mode: str
    message: str | None = None
    fallback_used: bool = False


def search_jobs(keyword: str | None, filters: SearchFilters) -> SearchResult:
    """Return one of UC-03's LATEST, FILTER_ONLY, SEMANTIC, or fallback modes."""
    normalized_keyword = (keyword or "").strip()
    has_keyword = bool(normalized_keyword)
    has_filters = not filters.is_empty()
    queryset = selectors.filter_active_jobs(
        workplace_type=filters.workplace_type,
        job_type=filters.job_type,
        location=filters.location,
        experience_level=filters.experience_level,
        salary_min=filters.salary_min,
    )
    if has_keyword:
        queryset = apply_explicit_developer_intent(queryset, normalized_keyword)

    if not has_keyword:
        mode = "FILTER_ONLY" if has_filters else "LATEST"
        message = None if queryset.exists() else NO_RESULTS_MESSAGE
        return SearchResult(queryset=queryset, mode=mode, message=message)

    if not queryset.exists():
        return SearchResult(
            queryset=queryset,
            mode="SEMANTIC",
            message=NO_RESULTS_MESSAGE,
        )

    query_text = build_query_text(normalized_keyword)
    try:
        query_vector = embed_query(query_text)
    except EmbeddingError as exc:
        logger.warning(
            "Gemini embedding failed; using UC-03 basic keyword fallback (%s)",
            type(exc.__cause__ or exc).__name__,
        )
        fallback = selectors.basic_keyword_search(
            queryset,
            normalize_basic_keyword(normalized_keyword),
        )
        return SearchResult(
            queryset=fallback,
            mode="FALLBACK_BASIC",
            message=None if fallback.exists() else NO_RESULTS_MESSAGE,
            fallback_used=True,
        )

    if not selectors.jobs_with_current_embeddings(queryset).exists():
        fallback = selectors.basic_keyword_search(
            queryset,
            normalize_basic_keyword(normalized_keyword),
        )
        return SearchResult(
            queryset=fallback,
            mode="FALLBACK_BASIC",
            message=None if fallback.exists() else NO_RESULTS_MESSAGE,
            fallback_used=True,
        )
    ranked = selectors.rank_jobs_by_query_embedding(queryset, query_vector)
    return SearchResult(
        queryset=ranked,
        mode="SEMANTIC",
        message=None if ranked.exists() else NO_RESULTS_MESSAGE,
    )
