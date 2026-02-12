from fastapi import APIRouter, Depends, Request, Response, Cookie
from src.dependencies import get_auth_claims
from src.routers.session import SESSION_STORE
import httpx
import os

router = APIRouter(prefix="/grafana", tags=["grafana-proxy"])

GRAFANA_INTERNAL_URL = "http://grafana:3000"


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def proxy_to_grafana(
    path: str,
    request: Request,
    backend_session: str | None = Cookie(default=None),
):
    """
    Reverse proxy to Grafana with Auth Proxy headers.
    """

    if not backend_session or backend_session not in SESSION_STORE:
        return Response(status_code=401, content="Not authenticated")

    user_data = SESSION_STORE[backend_session]
    user_email = user_data["email"]
    user_name = user_data["name"]

    # Copy incoming headers
    headers = dict(request.headers)

    # Inject trusted auth proxy headers
    headers["X-WEBAUTH-USER"] = user_email
    headers["X-WEBAUTH-EMAIL"] = user_email
    headers["X-WEBAUTH-NAME"] = user_name
    headers["ngrok-skip-browser-warning"] = "69420"  # Value can be anything

    # Remove host header to avoid conflicts
    headers.pop("host", None)

    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await client.request(
            request.method,
            f"{GRAFANA_INTERNAL_URL}/{path}",
            headers=headers,
            content=await request.body(),
        )

    # Remove hop-by-hop headers
    excluded = ["content-encoding", "transfer-encoding", "connection"]

    response_headers = {
        k: v for k, v in resp.headers.items()
        if k.lower() not in excluded
    }

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=response_headers,
    )
