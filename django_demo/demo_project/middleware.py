"""Custom middleware for the SAPL Django demo."""
from __future__ import annotations

import json

from django.http import HttpResponse


def _error_response(exc):
    return HttpResponse(
        json.dumps({"detail": str(exc)}),
        content_type="application/json",
        status=500,
    )


class RuntimeErrorMiddleware:
    """Convert RuntimeError to a JSON 500 response.

    Uses process_exception to intercept errors before Django's
    convert_exception_to_response converts them to HTML debug pages.
    """
    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    async def __acall__(self, request):
        return await self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, RuntimeError):
            return _error_response(exception)
        return None
