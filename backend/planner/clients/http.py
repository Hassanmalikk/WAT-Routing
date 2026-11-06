import asyncio
import logging
from collections.abc import Mapping

import httpx

from planner.errors import UpstreamError

RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
MAX_ATTEMPTS = 3
BACKOFF_S = 0.5

QueryParams = Mapping[str, str | int | float] | tuple[tuple[str, str | int | float], ...]

logger = logging.getLogger(__name__)


async def send(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    params: QueryParams,
    service: str,
    json: object = None,
) -> httpx.Response:
    failure = ""
    for attempt in range(MAX_ATTEMPTS):
        if attempt:
            await asyncio.sleep(BACKOFF_S * 2 ** (attempt - 1))
        try:
            response = await client.request(method, url, params=params, json=json)
        except httpx.TransportError as exc:
            failure = type(exc).__name__
            continue
        if response.status_code not in RETRYABLE_STATUS:
            return response
        failure = f"HTTP {response.status_code}"
    logger.warning("%s failed after %d attempts: %s", service, MAX_ATTEMPTS, failure)
    if failure == f"HTTP {httpx.codes.TOO_MANY_REQUESTS}":
        raise UpstreamError(f"{service} rate limit reached. Please wait a minute and try again.")
    raise UpstreamError(f"{service} is temporarily unavailable. Please try again shortly.")
