"""UC-03 orchestration: hard filters first, then semantic ranking or fallback."""
import logging
from dataclasses import dataclass

from django.db.models import QuerySet

from apps.core.embedding_text_builders import build_query_text
from apps.jobs import selectors
from apps.jobs.models import JobPost
from integrations.gemini.embeddings import EmbeddingError, embed_query


logger = logging.getLogger(__name__)

NO_RESULTS_MESSAGE = (
    "Không tìm thấy công việc phù hợp với yêu cầu của bạn. "
    "Hãy thử bỏ bớt bộ lọc hoặc đổi từ khóa."
)


@dataclass(frozen=True)
class SearchFilters:
    location: str | None = None
    salary_min: int | None = None
    experience_level: str | None = None
    job_type: str | None = None

    def is_empty(self) -> bool:
        return not any(
            (
                self.location,
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
        job_type=filters.job_type,
        location=filters.location,
        experience_level=filters.experience_level,
        salary_min=filters.salary_min,
    )

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
            "Gemini embedding failed; using UC-03 SQL fallback (%s)",
            type(exc.__cause__ or exc).__name__,
        )
        fallback = selectors.fallback_keyword_search(queryset, normalized_keyword)
        return SearchResult(
            queryset=fallback,
            mode="FALLBACK_SQL",
            message=None if fallback.exists() else NO_RESULTS_MESSAGE,
            fallback_used=True,
        )

    ranked = selectors.rank_jobs_by_query_embedding(queryset, query_vector)
    return SearchResult(
        queryset=ranked,
        mode="SEMANTIC",
        message=None if ranked.exists() else NO_RESULTS_MESSAGE,
    )
