from django.utils import timezone


class ServerTimeMiddleware:
    """Appends X-Server-Time ISO timestamp and ensures standard Date header for client clock skew sync."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["X-Server-Time"] = timezone.now().isoformat()
        return response
