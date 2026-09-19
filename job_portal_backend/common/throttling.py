from rest_framework.throttling import AnonRateThrottle
from rest_framework.throttling import SimpleRateThrottle


class JobSearchAnonThrottle(AnonRateThrottle):
    scope = "job_search_anon"


class AuthenticatedUserThrottle(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": user.pk}


class JobSearchUserThrottle(AuthenticatedUserThrottle):
    scope = "job_search_user"


class UploadParseMinuteThrottle(AuthenticatedUserThrottle):
    scope = "upload_parse_minute"


class UploadParseDailyThrottle(AuthenticatedUserThrottle):
    scope = "upload_parse_daily"
