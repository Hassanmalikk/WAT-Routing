import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime
from itertools import batched
from typing import Any

import httpx

from planner.clients.http import send
from planner.domain.geo import LatLon
from planner.domain.weather import HourlySeries
from planner.errors import UpstreamError

SERVICE = "Open-Meteo"
HOURLY_VARIABLES = ("wind_speed_10m", "wind_gusts_10m", "rain", "showers", "snowfall")
BATCH_SIZE = 100
MAX_CONCURRENT_BATCHES = 4
HOUR_FORMAT = "%Y-%m-%dT%H:%M"


def _values(hourly: dict[str, Any], name: str, expected: int) -> list[float]:
    values = hourly[name]
    if len(values) != expected or any(value is None for value in values):
        raise UpstreamError("The weather forecast is incomplete for part of this trip.")
    return [float(value) for value in values]


def _series(location: dict[str, Any], start: datetime, expected: int) -> HourlySeries:
    hourly = location["hourly"]
    if not hourly["time"] or datetime.fromtimestamp(hourly["time"][0], UTC) != start:
        raise UpstreamError("The weather forecast does not cover this trip's time window.")
    rain = _values(hourly, "rain", expected)
    showers = _values(hourly, "showers", expected)
    return HourlySeries(
        start=start,
        wind_mph=_values(hourly, "wind_speed_10m", expected),
        gust_mph=_values(hourly, "wind_gusts_10m", expected),
        rain_in_hr=[round(r + s, 3) for r, s in zip(rain, showers, strict=True)],
        snow_in_hr=_values(hourly, "snowfall", expected),
    )


class OpenMeteoClient:
    def __init__(self, http: httpx.AsyncClient, url: str, api_key: str) -> None:
        self._http = http
        self._url = url
        self._api_key = api_key
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_BATCHES)

    async def _batch(
        self, points: Sequence[LatLon], start: datetime, end: datetime
    ) -> list[HourlySeries]:
        params = {
            "latitude": ",".join(f"{point.lat:.4f}" for point in points),
            "longitude": ",".join(f"{point.lon:.4f}" for point in points),
            "hourly": ",".join(HOURLY_VARIABLES),
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": "GMT",
            "timeformat": "unixtime",
            "start_hour": start.strftime(HOUR_FORMAT),
            "end_hour": end.strftime(HOUR_FORMAT),
        }
        if self._api_key:
            params["apikey"] = self._api_key
        async with self._semaphore:
            response = await send(self._http, "GET", self._url, params=params, service=SERVICE)
        if response.status_code != httpx.codes.OK:
            raise UpstreamError("The weather forecast is unavailable for this trip.")
        payload = response.json()
        locations = payload if isinstance(payload, list) else [payload]
        if len(locations) != len(points):
            raise UpstreamError("The weather service returned an unexpected response.")
        expected = int((end - start).total_seconds() // 3600) + 1
        return [_series(location, start, expected) for location in locations]

    async def hourly(
        self, points: Sequence[LatLon], start: datetime, end: datetime
    ) -> list[HourlySeries]:
        try:
            async with asyncio.TaskGroup() as group:
                tasks = [
                    group.create_task(self._batch(batch, start, end))
                    for batch in batched(points, BATCH_SIZE, strict=False)
                ]
        except* UpstreamError as failures:
            raise failures.exceptions[0] from None
        return [series for task in tasks for series in task.result()]
