"""Throttling dùng chung, với tần suất được cấu hình tập trung trong settings."""
from rest_framework.throttling import AnonRateThrottle
from rest_framework.throttling import SimpleRateThrottle


class JobSearchAnonThrottle(AnonRateThrottle):
    """UC-03 E3: khách vãng lai tối đa 5 lượt tìm kiếm/phút."""

    scope = "job_search_anon"


class AuthenticatedUserThrottle(SimpleRateThrottle):
    """Lớp throttle cơ sở cho user đã đăng nhập, định danh theo khóa chính."""

    def get_cache_key(self, request, view):
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": user.pk}


class JobSearchUserThrottle(AuthenticatedUserThrottle):
    """UC-03 E3: ứng viên đăng nhập tối đa 10 lượt tìm kiếm/phút."""

    scope = "job_search_user"


class UploadParseMinuteThrottle(AuthenticatedUserThrottle):
    """UC-01/02: mỗi user tối đa 2 lượt upload file để Gemini phân tích mỗi phút."""

    scope = "upload_parse_minute"


class UploadParseDailyThrottle(AuthenticatedUserThrottle):
    """UC-01/02: mỗi user tối đa 10 lượt upload để phân tích mỗi ngày."""

    scope = "upload_parse_daily"
