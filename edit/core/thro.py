
from rest_framework.throttling import SimpleRateThrottle

class CustomUserRateThrottle(SimpleRateThrottle):
    scope = "custom_user"

    def get_cache_key(self, request, view):
        # Если токен ещё не проверен — ограничиваем по IP
        if not hasattr(request, "user_id"):
            return self.cache_format % {
                "scope": self.scope,
                "ident": self.get_ident(request),
            }
        # Если есть user_id из твоего require_auth
        return self.cache_format % {
            "scope": self.scope,
            "ident": str(request.user_id),
        }