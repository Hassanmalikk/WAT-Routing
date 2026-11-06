import asyncio
import hashlib
import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta

import httpx
from django.conf import settings
from django.core.cache import cache

from planner.clients.open_meteo import OpenMeteoClient
from planner.clients.tomtom import Place, TomTomClient
from planner.domain.alternatives import Box, detour_boxes, distinct_routes
from planner.domain.assessment import Checkpoint, RouteAssessment, assess_route
from planner.domain.corridor import (
    FORECAST_HOURS,
    Grid,
    Heatmap,
    build_heatmap,
    coarsest_needed_cell,
    corridor_grid,
    snap_to_cell,
)
from planner.domain.geo import METERS_PER_MILE, LatLon, RoutePath, haversine_m, simplify
from planner.domain.hours_of_service import ScheduledStop, schedule_stops
from planner.domain.recommendation import Recommendation, recommend
from planner.domain.risk import assess
from planner.domain.sampling import Waypoint, locate_stops, plan_waypoints
from planner.domain.verification import PlanInputs, Verification, verify
from planner.domain.weather import HourlySeries, ceil_hour, floor_hour
from planner.errors import PlanningError, UpstreamError

TRUCK_TARE_LB = 35_000
TRUCK_MAX_SPEED_KMH = 105
KG_PER_LB = 0.45359237
ROUTE_OPTION_COUNT = 3
MIN_TRIP_DISTANCE_M = 100.0
DEPART_NOW_TOLERANCE = timedelta(minutes=1)

MAX_CHECKPOINT_CELLS = 250
CORRIDOR_BUFFER_M = 25 * METERS_PER_MILE
CORRIDOR_SIMPLIFY_M = 1_000.0
MAX_HEATMAP_CELLS = 200

FORECAST_DAYS = 16
WINDOW_STEP = timedelta(hours=24)

PLACE_RESULT_LIMIT = 6
PLACES_CACHE_TTL_S = 30 * 24 * 3_600
ROUTES_CACHE_TTL_S = 60 * 60
WEATHER_CACHE_TTL_S = 60 * 60
HTTP_TIMEOUT = httpx.Timeout(20.0, connect=5.0)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TripRequest:
    origin: LatLon
    destination: LatLon
    departure: datetime
    load_lb: int
    interval_mi: int
    rest_breaks: bool


@dataclass(frozen=True, slots=True)
class TripPlan:
    routes: Sequence[RouteAssessment]
    recommendation: Recommendation
    heatmap: Heatmap
    verification: Verification


def _cache_key(namespace: str, *parts: object) -> str:
    digest = hashlib.sha256(repr(parts).encode()).hexdigest()[:32]
    return f"{namespace}:{digest}"


def _http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=HTTP_TIMEOUT)


async def search_places(query: str) -> list[Place]:
    normalized = " ".join(query.split()).casefold()
    key = _cache_key("places", normalized)
    cached: list[Place] | None = await cache.aget(key)
    if cached is not None:
        return cached
    async with _http_client() as http:
        tomtom = TomTomClient(http, settings.TOMTOM_API_KEY)
        places = await tomtom.search_places(normalized, PLACE_RESULT_LIMIT)
    await cache.aset(key, places, PLACES_CACHE_TTL_S)
    return places


async def _route_options(
    tomtom: TomTomClient, request: TripRequest, now: datetime
) -> list[RoutePath]:
    depart_at = request.departure if request.departure > now + DEPART_NOW_TOLERANCE else None
    weight_kg = round((TRUCK_TARE_LB + request.load_lb) * KG_PER_LB)
    key = _cache_key("routes", request.origin, request.destination, depart_at, weight_kg)
    cached: list[RoutePath] | None = await cache.aget(key)
    if cached is not None:
        return cached

    async def calculate(avoid: Sequence[Box] = ()) -> list[RoutePath]:
        return await tomtom.calculate_routes(
            request.origin,
            request.destination,
            depart_at=depart_at,
            vehicle_weight_kg=weight_kg,
            vehicle_max_speed_kmh=TRUCK_MAX_SPEED_KMH,
            max_alternatives=ROUTE_OPTION_COUNT - 1,
            avoid=avoid,
        )

    routes = distinct_routes(await calculate(), ROUTE_OPTION_COUNT)
    if not routes:
        raise PlanningError("No truck route exists between these locations.")
    boxes = (
        detour_boxes(routes, request.origin, request.destination)
        if len(routes) < ROUTE_OPTION_COUNT
        else []
    )
    if boxes:
        try:
            detours = await calculate(avoid=boxes)
        except (PlanningError, UpstreamError) as exc:
            logger.warning("Detour route request failed: %s", exc)
        else:
            routes = distinct_routes([*routes, *detours], ROUTE_OPTION_COUNT)
    await cache.aset(key, routes, ROUTES_CACHE_TTL_S)
    return routes


def _forecast_window(
    departure: datetime, arrival: datetime, now: datetime
) -> tuple[datetime, datetime]:
    start = floor_hour(departure)
    needed_end = max(ceil_hour(arrival), ceil_hour(departure + timedelta(hours=FORECAST_HOURS)))
    horizon = datetime.combine(now.date(), time(), UTC) + timedelta(days=FORECAST_DAYS, hours=-1)
    if needed_end > horizon:
        raise PlanningError(
            "This trip extends beyond the 16-day weather forecast. Choose an earlier departure."
        )
    steps = -(-(needed_end - start) // WINDOW_STEP)
    return start, min(start + steps * WINDOW_STEP, horizon)


async def _forecasts(
    client: OpenMeteoClient, cells: Iterable[LatLon], start: datetime, end: datetime
) -> dict[LatLon, HourlySeries]:
    keys = {cell: _cache_key("weather", cell, start, end) for cell in dict.fromkeys(cells)}
    cached = await cache.aget_many(keys.values())
    forecasts = {cell: cached[key] for cell, key in keys.items() if key in cached}
    missing = [cell for cell in keys if cell not in forecasts]
    if missing:
        fresh = dict(zip(missing, await client.hourly(missing, start, end), strict=True))
        await cache.aset_many(
            {keys[cell]: series for cell, series in fresh.items()}, WEATHER_CACHE_TTL_S
        )
        forecasts |= fresh
    return forecasts


@dataclass(frozen=True, slots=True)
class _Itinerary:
    schedules: Sequence[Sequence[ScheduledStop]]
    waypoints: Sequence[Sequence[Waypoint]]
    checkpoint_cell_deg: float
    grid: Grid

    def checkpoint_cell(self, waypoint: Waypoint) -> LatLon:
        return snap_to_cell(waypoint.position, self.checkpoint_cell_deg)

    @property
    def checkpoint_cells(self) -> list[LatLon]:
        return [self.checkpoint_cell(waypoint) for route in self.waypoints for waypoint in route]

    @property
    def last_arrival(self) -> datetime:
        return max(route[-1].eta for route in self.waypoints)


def _itinerary(request: TripRequest, paths: Sequence[RoutePath]) -> _Itinerary:
    interval_m = request.interval_mi * METERS_PER_MILE
    schedules = [
        schedule_stops(path.total_driving_s) if request.rest_breaks else () for path in paths
    ]
    waypoints = [
        plan_waypoints(path, interval_m, request.departure, schedule)
        for path, schedule in zip(paths, schedules, strict=True)
    ]
    grid = corridor_grid(
        [simplify(path.points, CORRIDOR_SIMPLIFY_M) for path in paths],
        CORRIDOR_BUFFER_M,
        MAX_HEATMAP_CELLS,
    )
    checkpoint_cell_deg = coarsest_needed_cell(
        [waypoint.position for route in waypoints for waypoint in route], MAX_CHECKPOINT_CELLS
    )
    return _Itinerary(schedules, waypoints, checkpoint_cell_deg, grid)


def _assemble(
    request: TripRequest,
    paths: Sequence[RoutePath],
    itinerary: _Itinerary,
    forecasts: dict[LatLon, HourlySeries],
) -> TripPlan:
    def checkpoint(waypoint: Waypoint) -> Checkpoint:
        series = forecasts[itinerary.checkpoint_cell(waypoint)]
        conditions = series.at(waypoint.eta)
        return Checkpoint(waypoint, conditions, assess(conditions, request.load_lb))

    routes = [
        assess_route(
            path,
            request.departure,
            [checkpoint(waypoint) for waypoint in route_waypoints],
            locate_stops(path, request.departure, schedule),
        )
        for path, schedule, route_waypoints in zip(
            paths, itinerary.schedules, itinerary.waypoints, strict=True
        )
    ]
    heatmap = build_heatmap(
        itinerary.grid,
        lambda cell, moment: forecasts[cell].at(moment),
        request.departure,
        request.load_lb,
    )
    recommendation = recommend(routes)
    verification = verify(
        routes,
        recommendation,
        PlanInputs(
            departure=request.departure,
            interval_m=request.interval_mi * METERS_PER_MILE,
            load_lb=request.load_lb,
            rest_breaks=request.rest_breaks,
        ),
    )
    if not verification.passed:
        failed = [check.key for check in verification.checks if not check.passed]
        logger.error("Plan failed verification: %s", ", ".join(failed))
    return TripPlan(routes, recommendation, heatmap, verification)


async def plan_trip(request: TripRequest, now: datetime) -> TripPlan:
    if haversine_m(request.origin, request.destination) < MIN_TRIP_DISTANCE_M:
        raise PlanningError("Origin and destination are the same location.")
    async with _http_client() as http:
        paths = await _route_options(TomTomClient(http, settings.TOMTOM_API_KEY), request, now)
        itinerary = await asyncio.to_thread(_itinerary, request, paths)
        start, end = _forecast_window(request.departure, itinerary.last_arrival, now)
        weather = OpenMeteoClient(http, settings.OPEN_METEO_URL, settings.OPEN_METEO_API_KEY)
        forecasts = await _forecasts(
            weather, [*itinerary.checkpoint_cells, *itinerary.grid.cells], start, end
        )
    return await asyncio.to_thread(_assemble, request, paths, itinerary, forecasts)
