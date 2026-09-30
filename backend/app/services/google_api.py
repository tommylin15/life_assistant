import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.google_oauth import get_access_token


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def request_google(
    db: AsyncSession,
    user_sub: str,
    scope: str,
    method: str,
    url: str,
    **kwargs,
) -> httpx.Response:
    """Make an authenticated Google API request with one forced-refresh retry."""

    token = await get_access_token(db, user_sub, scope)
    headers = dict(kwargs.pop("headers", {}))
    headers.update(_auth_headers(token))
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.request(method, url, headers=headers, **kwargs)
    except httpx.HTTPError as exc:
        raise HTTPException(503, "Google API unavailable") from exc

    if response.status_code == 401:
        token = await get_access_token(db, user_sub, scope, force_refresh=True)
        headers.update(_auth_headers(token))
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.request(method, url, headers=headers, **kwargs)
        except httpx.HTTPError as exc:
            raise HTTPException(503, "Google API unavailable") from exc

    if response.status_code in {401, 403}:
        raise HTTPException(
            409, "Google reauthorization or additional permission is required"
        )
    if response.status_code >= 400:
        raise HTTPException(502, "Google API request failed")
    return response
