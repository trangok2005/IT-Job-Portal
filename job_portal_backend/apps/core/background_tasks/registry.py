"""Allow-list các business task được background dispatcher chấp nhận."""
from collections.abc import Callable

from apps.ai_analysis.tasks import (
    compute_application_match_score,
    retry_incomplete_application_matches,
)
from apps.candidates.tasks import (
    cleanup_expired_resume_imports,
    generate_candidate_embedding,
    parse_resume_import,
)
from apps.jobs.tasks import (
    cleanup_expired_jd_imports,
    expire_jobs,
    generate_job_embedding,
    parse_jd_import,
)
from apps.notifications.tasks import send_application_status_email


TASK_REGISTRY: dict[str, Callable] = {
    "cleanup_expired_jd_imports": cleanup_expired_jd_imports,
    "cleanup_expired_resume_imports": cleanup_expired_resume_imports,
    "compute_application_match_score": compute_application_match_score,
    "retry_incomplete_application_matches": retry_incomplete_application_matches,
    "expire_jobs": expire_jobs,
    "generate_candidate_embedding": generate_candidate_embedding,
    "generate_job_embedding": generate_job_embedding,
    "parse_jd_import": parse_jd_import,
    "parse_resume_import": parse_resume_import,
    "send_application_status_email": send_application_status_email,
}
