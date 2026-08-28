"""Throttling dùng chung cho toàn dự án.

Tần suất cấu hình tập trung tại REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
(config/settings/base.py) — muốn chỉnh limit chỉ cần sửa settings,
không đụng code class.
"""
from rest_framework.throttling import AnonRateThrottle
from rest_framework.throttling import SimpleRateThrottle


class JobSearchAnonThrottle(AnonRateThrottle):
    """UC-03 E3: khách vãng lai tối đa 5 lượt tìm kiếm/phút."""

    scope = "job_search_anon"


class AuthenticatedUserThrottle(SimpleRateThrottle):
    """Base cho throttle chỉ áp dụng người đã đăng nhập (định danh theo pk)."""

    def get_cache_key(self, request, view):
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": user.pk}


class JobSearchUserThrottle(AuthenticatedUserThrottle):
    """UC-03 E3: ứng viên đăng nhập tối đa 10 lượt tìm kiếm/phút."""

    scope = "job_search_user"


class UploadParseMinuteThrottle(AuthenticatedUserThrottle):
    """UC-01/02: mỗi user tối đa 2 lượt upload file parse Gemini/phút."""

    scope = "upload_parse_minute"


class UploadParseDailyThrottle(AuthenticatedUserThrottle):
    """UC-01/02: mỗi user tối đa 10 lượt upload parse/ngày (trần chi phí AI)."""

    scope = "upload_parse_daily"
