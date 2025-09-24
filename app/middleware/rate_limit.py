import time, ipaddress
import redis
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.responses import PlainTextResponse
from app.core.config import settings

class RateLimitMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app
        self.r = redis.from_url(settings.redis_url, decode_responses=True)
        self.window = 86400  # 1 day

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        path = scope.get("path", "")
        # guard analyze endpoints only
        if path not in ("/ui-match", "/demo"):
            return await self.app(scope, receive, send)

        # read session (Starlette stores in scope["session"] only after middleware resolves;
        # so we look at headers/cookies is tricky here. Best approach:
        # defer to ASGI downstream, but we want to block before. Simple compromise:
        # use query of cookies; but safe path: read session later -> we’ll accept minor duplication:
        # We'll use IP for anon + user_id cookie presence signal from header if any.
        # Simpler solution: let UI route call a helper check. But we keep middleware:

        # pull client IP
        client = scope.get("client")
        ip = (client[0] if client else "0.0.0.0")
        try:
            ipaddress.ip_address(ip)
        except Exception:
            ip = "0.0.0.0"

        # detect user id from cookie (session) if present (best-effort)
        # Starlette session cookie name: "session"
        user_id = None
        for k, v in (scope.get("headers") or []):
            if k == b"cookie" and b"session=" in v:
                # we can't decode session here; so do a conservative approach:
                # allow per-IP anon once; additional checks happen inside the route.
                break

        # Basic IP gate for anonymous (1/day)
        day = time.strftime("%Y%m%d")
        key_ip = f"rl:ip:{ip}:{day}"
        cnt = self.r.incr(key_ip)
        if cnt == 1:
            self.r.expire(key_ip, self.window)

        # If they blow past 20 reqs by IP, just block aggressively (abuse)
        if cnt > 20:
            return await PlainTextResponse("Slow down. Try again tomorrow.", status_code=429)(scope, receive, send)

        # Let the route enforce precise user-tier limits (anon=1, free=15, premium=∞)
        return await self.app(scope, receive, send)
