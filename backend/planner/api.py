import logging
from typing import Any

from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from django.utils.cache import patch_cache_control
from ninja import Field, NinjaAPI, Query, Schema
from ninja.errors import ValidationError
from ninja.throttling import AnonRateThrottle

from planner import services
from planner.clients.tomtom import Place
from planner.domain.geo import LatLon
from planner.errors import PlanningError, UpstreamError
from planner.schemas import Error, PlaceOut, TripIn, TripPlanOut
from planner.services import TripPlan, TripRequest

logger = logging.getLogger(__name__)

PLACES_BROWSER_CACHE_S = 24 * 3_600

api = NinjaAPI(title="Weather-Aware Truck Routing", version="1.0.0")


class PlaceQuery(Schema):
    q: str = Field(min_length=2, max_length=200)


def _describe(error: dict[str, Any]) -> str:
    message = str(error["msg"]).removeprefix("Value error, ")
    field = ".".join(str(part) for part in error.get("loc", ())[2:])
    return f"{field}: {message}" if field else message


@api.exception_handler(ValidationError)
def validation_error(request: HttpRequest, exc: ValidationError) -> HttpResponse:
    detail = "; ".join(_describe(error) for error in exc.errors)
    return api.create_response(request, {"detail": detail}, status=422)


@api.exception_handler(PlanningError)
def planning_error(request: HttpRequest, exc: PlanningError) -> HttpResponse:
    return api.create_response(request, {"detail": str(exc)}, status=422)


@api.exception_handler(UpstreamError)
def upstream_error(request: HttpRequest, exc: UpstreamError) -> HttpResponse:
    logger.warning("Upstream failure: %s", exc)
    return api.create_response(request, {"detail": str(exc)}, status=502)


@api.get(
    "/places",
    response={200: list[PlaceOut], 422: Error, 502: Error},
    throttle=[AnonRateThrottle("120/m")],
)
async def places(
    request: HttpRequest, response: HttpResponse, query: Query[PlaceQuery]
) -> list[Place]:
    places = await services.search_places(query.q)
    patch_cache_control(response, public=True, max_age=PLACES_BROWSER_CACHE_S)
    return places


@api.post(
    "/trips",
    response={200: TripPlanOut, 422: Error, 502: Error},
    throttle=[AnonRateThrottle("20/m")],
)
async def plan_trip(request: HttpRequest, trip: TripIn) -> TripPlan:
    return await services.plan_trip(
        TripRequest(
            origin=LatLon(trip.origin.lat, trip.origin.lon),
            destination=LatLon(trip.destination.lat, trip.destination.lon),
            departure=trip.departure,
            load_lb=trip.load_lb,
            interval_mi=trip.interval_mi,
            rest_breaks=trip.rest_breaks,
        ),
        now=timezone.now(),
    )
