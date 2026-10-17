from __future__ import annotations
import re
import time
from collections import defaultdict, deque
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse
from .config import settings

SENSITIVE_KEYS = {
    "donor", "donor_name", "person_name", "board_member", "relationship_notes",
    "private_email", "phone", "address", "crm_record", "internal_notes"
}


def scrub_external_payload(value):
    """Remove obvious private donor/relationship fields before any external AI call.
    Defense-in-depth only; internal data should not be sent at all unless approved.
    """
    if isinstance(value, dict):
        return {k: scrub_external_payload(v) for k, v in value.items() if k.lower() not in SENSITIVE_KEYS}
    if isinstance(value, list):
        return [scrub_external_payload(v) for v in value]
    if isinstance(value, str):
        # Redact common email/phone patterns from free text.
        value = re.sub(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", "[REDACTED_EMAIL]", value, flags=re.I)
        value = re.sub(r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}(?!\d)", "[REDACTED_PHONE]", value)
    return value

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.requests: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":
            return await call_next(request)
        now = time.time()
        ip = request.client.host if request.client else "unknown"
        q = self.requests[ip]
        while q and q[0] < now - 60:
            q.popleft()
        if len(q) >= settings.rate_limit_per_minute:
            return JSONResponse({"detail":"Rate limit exceeded"}, status_code=429)
        q.append(now)
        return await call_next(request)
