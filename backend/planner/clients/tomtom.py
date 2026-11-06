import itertools
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import quote

import httpx

from planner.clients.http import send
from planner.domain.alternatives import Box
from planner.domain.geo import LatLon, RoutePath, haversine_m, lerp
from planner.errors import PlanningError, UpstreamError

BASE_URL = "https://api.tomtom.com"
SERVICE = "TomTom"
UNROUTABLE_MESSAGES = {
    "NO_ROUTE_FOUND": "No truck route exists between these locations.",
    "MAP_MATCHING_FAILURE": "One of the locations cannot be reached by road.",
}


@dataclass(frozen=True, slots=True)
class Place:
    label: str
    position: LatLon


def _place_label(result: dict[str, Any]) -> str:
    address: str = result["address"]["freeformAddress"]
    poi_name = result.get("poi", {}).get("name")
    return f"{poi_name}, {address}" if poi_name else address


def _route_path(route: dict[str, Any]) -> RoutePath:
    points = [
        LatLon(point["latitude"], point["longitude"])
        for leg in route["legs"]
        for point in leg["points"]
    ]
    anchors = {
        entry["pointIndex"]: (float(entry["distanceInMeters"]), float(entry["travelTimeInSeconds"]))
        for entry in route["progress"]
    }
    anchors.setdefault(0, (0.0, 0.0))
    summary = route["summary"]
    anchors[len(points) - 1] = (
        float(summary["lengthInMeters"]),
        float(summary["travelTimeInSeconds"]),
    )
    distances = [0.0] * len(points)
    times = [0.0] * len(points)
    indices = sorted(anchors)
    for start, end in itertools.pairwise(indices):
        (start_m, start_s), (end_m, end_s) = anchors[start], anchors[end]
        chord = [0.0]
        for i in range(start, end):
            chord.append(chord[-1] + haversine_m(points[i], points[i + 1]))
        for offset, along in enumerate(chord):
            fraction = along / chord[-1] if chord[-1] > 0 else 0.0
            distances[start + offset] = lerp(start_m, end_m, fraction)
            times[start + offset] = lerp(start_s, end_s, fraction)
    return RoutePath(points, distances, times)


def _rectangle(box: Box) -> dict[str, dict[str, float]]:
    return {
        "southWestCorner": {"latitude": box.south_west.lat, "longitude": box.south_west.lon},
        "northEastCorner": {"latitude": box.north_east.lat, "longitude": box.north_east.lon},
    }


def _error_code(response: httpx.Response) -> str:
    try:
        return str(response.json()["detailedError"]["code"])
    except (ValueError, KeyError, TypeError):
        return ""


class TomTomClient:
    def __init__(self, http: httpx.AsyncClient, api_key: str) -> None:
        if not api_key:
            raise UpstreamError("Routing is not configured on the server.")
        self._http = http
        self._api_key = api_key

    async def search_places(self, query: str, limit: int) -> list[Place]:
        response = await send(
            self._http,
            "GET",
            f"{BASE_URL}/search/2/search/{quote(query, safe='')}.json",
            params={"key": self._api_key, "typeahead": "true", "limit": limit},
            service=SERVICE,
        )
        if response.status_code != httpx.codes.OK:
            raise UpstreamError("Address search is temporarily unavailable.")
        places: dict[str, Place] = {}
        for result in response.json()["results"]:
            label = _place_label(result)
            position = LatLon(result["position"]["lat"], result["position"]["lon"])
            places.setdefault(label, Place(label, position))
        return list(places.values())

    async def calculate_routes(
        self,
        origin: LatLon,
        destination: LatLon,
        *,
        depart_at: datetime | None,
        vehicle_weight_kg: int,
        vehicle_max_speed_kmh: int,
        max_alternatives: int,
        avoid: Sequence[Box] = (),
    ) -> list[RoutePath]:
        locations = f"{origin.lat},{origin.lon}:{destination.lat},{destination.lon}"
        body = {"avoidAreas": {"rectangles": [_rectangle(box) for box in avoid]}} if avoid else None
        response = await send(
            self._http,
            "POST" if body else "GET",
            f"{BASE_URL}/routing/1/calculateRoute/{locations}/json",
            json=body,
            params=(
                ("key", self._api_key),
                ("travelMode", "truck"),
                ("vehicleCommercial", "true"),
                ("vehicleWeight", vehicle_weight_kg),
                ("vehicleMaxSpeed", vehicle_max_speed_kmh),
                ("routeType", "fastest"),
                ("maxAlternatives", max_alternatives),
                ("traffic", "true"),
                ("departAt", depart_at.isoformat(timespec="seconds") if depart_at else "now"),
                ("extendedRouteRepresentation", "distance"),
                ("extendedRouteRepresentation", "travelTime"),
            ),
            service=SERVICE,
        )
        if response.status_code != httpx.codes.OK:
            message = UNROUTABLE_MESSAGES.get(_error_code(response))
            if message:
                raise PlanningError(message)
            raise UpstreamError("Routing is temporarily unavailable.")
        return [_route_path(route) for route in response.json()["routes"]]
