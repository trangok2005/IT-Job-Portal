"""jobs throttling — chống spam tìm kiếm (UC-03 E3)."""
from rest_framework.throttling import AnonRateThrottle


class JobSearchAnonThrottle(AnonRateThrottle):
    """Khách vãng lai tối đa 5 lượt tìm kiếm/phút; vượt quá trả HTTP 429."""

    scope = "job_search"
