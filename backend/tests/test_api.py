import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
import respx
from django.test import AsyncClient
from django.utils import timezone

from planner.domain.geo import LatLon, RoutePath
from tests.factories import straight_path

ORIGIN = LatLon(40.0, -100.0)
DESTINATION = LatLon(41.0, -100.0)
ROUTING_URL = "https://api.tomtom.com/routing/1/calculateRoute/"
SEARCH_URL = "https://api.tomtom.com/search/2/search/"
WEATHER_URL = "https://weather.test/v1/forecast"

FAST = straight_path(ORIGIN, DESTINATION, steps=40, speed_mps=28.0)
WEST = straight_path(ORIGIN, LatLon(41.0, -100.3), steps=40, speed_mps=26.0)
EAST = straight_path(ORIGIN, LatLon(41.0, -99.7), steps=40, speed_mps=24.0)

Weather = dict[str, float]
CALM: Weather = {"wind": 5.0, "gust": 9.0, "rain": 0.0, "showers": 0.0, "snow": 0.0}


def _route_json(path: RoutePath) -> dict[str, Any]:
    return {
        "summary": {
            "lengthInMeters": round(path.length_m),
            "travelTimeInSeconds": round(path.total_driving_s),
        },
        "legs": [{"points": [{"latitude": p.lat, "longitude": p.lon} for p in path.points]}],
        "progress": [
            {"pointIndex": i, "distanceInMeters": round(d), "travelTimeInSeconds": round(t)}
            for i, (d, t) in enumerate(zip(path.distances_m, path.driving_s, strict=True))
        ],
    }


def _routes_response(*paths: RoutePath) -> httpx.Response:
    return httpx.Response(200, json={"routes": [_route_json(path) for path in paths]})


def _mock_routing(*paths: RoutePath) -> None:
    respx.get(url__startswith=ROUTING_URL).mock(return_value=_routes_response(*paths))
    respx.post(url__startswith=ROUTING_URL).mock(return_value=_routes_response(*paths))


def _weather_responder(weather: Weather) -> Callable[[httpx.Request], httpx.Response]:
    def respond(request: httpx.Request) -> httpx.Response:
        params = request.url.params
        start = datetime.fromisoformat(params["start_hour"]).replace(tzinfo=UTC)
        end = datetime.fromisoformat(params["end_hour"]).replace(tzinfo=UTC)
        count = int((end - start) / timedelta(hours=1)) + 1
        times = [int((start + timedelta(hours=i)).timestamp()) for i in range(count)]
        location = {
            "hourly": {
                "time": times,
                "wind_speed_10m": [weather["wind"]] * count,
                "wind_gusts_10m": [weather["gust"]] * count,
                "rain": [weather["rain"]] * count,
                "showers": [weather["showers"]] * count,
                "snowfall": [weather["snow"]] * count,
            }
        }
        return httpx.Response(200, json=[location] * len(params["latitude"].split(",")))

    return respond


def _trip(**overrides: Any) -> dict[str, Any]:
    return {
        "origin": {"lat": ORIGIN.lat, "lon": ORIGIN.lon},
        "destination": {"lat": DESTINATION.lat, "lon": DESTINATION.lon},
        "departure": (timezone.now() + timedelta(hours=2)).isoformat(),
        "load_lb": 20_000,
        "interval_mi": 25,
        "rest_breaks": True,
    } | overrides


async def _post(payload: dict[str, Any]) -> httpx.Response:
    response = await AsyncClient().post(
        "/api/trips", data=json.dumps(payload), content_type="application/json"
    )
    return httpx.Response(response.status_code, content=response.content)


@respx.mock
async def test_plan_returns_three_assessed_routes_and_heatmap() -> None:
    respx.get(url__startswith=ROUTING_URL).mock(return_value=_routes_response(FAST, WEST, EAST))
    respx.get(WEATHER_URL).mock(side_effect=_weather_responder(CALM))

    response = await _post(_trip())

    assert response.status_code == 200
    body = response.json()
    assert len(body["routes"]) == 3
    route = body["routes"][0]
    assert route["distance_mi"] == pytest.approx(69.1, abs=0.1)
    assert [round(c["mile"]) for c in route["checkpoints"]] == [0, 25, 50, 69]
    assert len(route["segments"]) == 3
    assert route["stops"] == []
    assert all(c["risk"]["level"] == 0 for c in route["checkpoints"])
    assert body["recommendation"] == {
        "index": 0,
        "deciding_factor": "travel_time",
        "runner_up_index": 1,
    }
    assert body["verification"]["passed"] is True
    assert {check["key"] for check in body["verification"]["checks"]} >= {
        "risk_table",
        "hours_of_service",
        "recommendation",
    }
    heatmap = body["heatmap"]
    assert len(heatmap["hours"]) == 49
    assert len(heatmap["risk"]) == len(heatmap["cells"]) > 0


@respx.mock
async def test_heavy_load_in_high_wind_is_no_travel() -> None:
    _mock_routing(FAST)
    respx.get(WEATHER_URL).mock(side_effect=_weather_responder(CALM | {"wind": 48.0}))

    body = (await _post(_trip(load_lb=35_000))).json()

    checkpoint = body["routes"][0]["checkpoints"][0]
    assert checkpoint["risk"] == {
        "level": 4,
        "wind": 4,
        "rain": 0,
        "snow": 0,
        "load_adjusted": True,
    }
    assert body["routes"][0]["summary"]["no_travel_mi"] == pytest.approx(69.1, abs=0.1)


@respx.mock
async def test_rain_combines_rain_and_showers() -> None:
    _mock_routing(FAST)
    respx.get(WEATHER_URL).mock(
        side_effect=_weather_responder(CALM | {"rain": 0.06, "showers": 0.05})
    )

    body = (await _post(_trip())).json()

    checkpoint = body["routes"][0]["checkpoints"][0]
    assert checkpoint["conditions"]["rain_in_hr"] == 0.11
    assert checkpoint["risk"]["rain"] == 1


@respx.mock
async def test_detour_request_supplies_missing_alternative() -> None:
    respx.get(url__startswith=ROUTING_URL).mock(return_value=_routes_response(FAST))
    detour = respx.post(url__startswith=ROUTING_URL).mock(return_value=_routes_response(FAST, WEST))
    respx.get(WEATHER_URL).mock(side_effect=_weather_responder(CALM))

    body = (await _post(_trip())).json()

    assert detour.calls.last.request.url.params["vehicleMaxSpeed"] == "105"
    rectangles = json.loads(detour.calls.last.request.content)["avoidAreas"]["rectangles"]
    assert len(rectangles) == 1
    assert len(body["routes"]) == 2


@respx.mock
async def test_failed_detour_keeps_primary_routes() -> None:
    respx.get(url__startswith=ROUTING_URL).mock(return_value=_routes_response(FAST))
    respx.post(url__startswith=ROUTING_URL).mock(
        return_value=httpx.Response(400, json={"detailedError": {"code": "NO_ROUTE_FOUND"}})
    )
    respx.get(WEATHER_URL).mock(side_effect=_weather_responder(CALM))

    response = await _post(_trip())

    assert response.status_code == 200
    assert len(response.json()["routes"]) == 1


@respx.mock
async def test_three_primary_routes_skip_detour() -> None:
    respx.get(url__startswith=ROUTING_URL).mock(return_value=_routes_response(FAST, WEST, EAST))
    detour = respx.post(url__startswith=ROUTING_URL)
    respx.get(WEATHER_URL).mock(side_effect=_weather_responder(CALM))

    await _post(_trip())

    assert not detour.called


@respx.mock
async def test_single_route_is_recommended_as_only_option() -> None:
    _mock_routing(FAST)
    respx.get(WEATHER_URL).mock(side_effect=_weather_responder(CALM))

    body = (await _post(_trip())).json()

    assert body["recommendation"]["deciding_factor"] == "only_route"


@respx.mock
async def test_long_trip_schedules_rest_stops() -> None:
    long_path = straight_path(LatLon(30.0, -100.0), LatLon(45.0, -100.0), steps=200, speed_mps=25)
    _mock_routing(long_path)
    respx.get(WEATHER_URL).mock(side_effect=_weather_responder(CALM))
    trip = _trip(destination={"lat": 45.0, "lon": -100.0}, origin={"lat": 30.0, "lon": -100.0})

    with_breaks = (await _post(trip)).json()["routes"][0]
    without_breaks = (await _post(trip | {"rest_breaks": False})).json()["routes"][0]

    assert [stop["kind"] for stop in with_breaks["stops"]] == ["break", "rest"]
    break_mile, rest_mile = (stop["mile"] for stop in with_breaks["stops"])
    assert break_mile == pytest.approx(8 * 3600 * 25 / 1609.344, abs=0.5)
    assert rest_mile == pytest.approx(11 * 3600 * 25 / 1609.344, abs=0.5)
    assert without_breaks["stops"] == []
    assert with_breaks["duration_s"] - without_breaks["duration_s"] == 10.5 * 3600


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"load_lb": 0}, "greater than or equal to 1"),
        ({"load_lb": 80_001}, "less than or equal to 80000"),
        ({"interval_mi": 15}, "10, 25 or 50"),
        ({"departure": "2020-01-01T00:00:00Z"}, "cannot be in the past"),
        ({"departure": "2099-01-01T00:00:00Z"}, "within the next 14 days"),
        ({"departure": "2026-11-07T10:00:00"}, "timezone"),
        ({"origin": {"lat": 91, "lon": 0}}, "less than or equal to 90"),
    ],
)
async def test_invalid_requests_are_rejected(overrides: dict[str, Any], message: str) -> None:
    response = await _post(_trip(**overrides))
    assert response.status_code == 422
    assert message in response.json()["detail"]


async def test_same_origin_and_destination_rejected() -> None:
    response = await _post(_trip(destination={"lat": ORIGIN.lat, "lon": ORIGIN.lon}))
    assert response.status_code == 422
    assert response.json()["detail"] == "Origin and destination are the same location."


@respx.mock
async def test_unroutable_trip_is_a_planning_error() -> None:
    respx.get(url__startswith=ROUTING_URL).mock(
        return_value=httpx.Response(
            400, json={"detailedError": {"code": "NO_ROUTE_FOUND", "message": "x"}}
        )
    )
    response = await _post(_trip())
    assert response.status_code == 422
    assert response.json()["detail"] == "No truck route exists between these locations."


@respx.mock
async def test_weather_outage_is_a_gateway_error() -> None:
    _mock_routing(FAST)
    weather = respx.get(WEATHER_URL).mock(return_value=httpx.Response(503))

    response = await _post(_trip())

    assert response.status_code == 502
    assert weather.call_count >= 3
    assert "Open-Meteo" in response.json()["detail"]


@respx.mock
async def test_incomplete_forecast_is_rejected() -> None:
    _mock_routing(FAST)

    def gappy(request: httpx.Request) -> httpx.Response:
        response = _weather_responder(CALM)(request)
        payload = response.json()
        payload[0]["hourly"]["rain"][0] = None
        return httpx.Response(200, json=payload)

    respx.get(WEATHER_URL).mock(side_effect=gappy)

    response = await _post(_trip())

    assert response.status_code == 502
    assert "incomplete" in response.json()["detail"]


@respx.mock
async def test_trip_beyond_forecast_horizon_rejected() -> None:
    long_path = straight_path(LatLon(30.0, -100.0), LatLon(45.0, -100.0), steps=200, speed_mps=25)
    _mock_routing(long_path)
    departure = (timezone.now() + timedelta(days=14)).isoformat()

    response = await _post(_trip(departure=departure, destination={"lat": 45.0, "lon": -100.0}))

    assert response.status_code == 422
    assert "16-day weather forecast" in response.json()["detail"]


@respx.mock
async def test_places_search() -> None:
    search = respx.get(url__startswith=SEARCH_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "address": {"freeformAddress": "Denver, CO"},
                        "position": {"lat": 39.74, "lon": -104.99},
                    },
                    {
                        "address": {"freeformAddress": "Denver, CO"},
                        "position": {"lat": 39.7, "lon": -104.9},
                    },
                    {
                        "poi": {"name": "Denver Depot"},
                        "address": {"freeformAddress": "1 Main St, Denver, CO"},
                        "position": {"lat": 39.75, "lon": -105.0},
                    },
                ]
            },
        )
    )

    response = await AsyncClient().get("/api/places", {"q": "  Denver  "})
    cached = await AsyncClient().get("/api/places", {"q": "denver"})

    assert response.status_code == 200
    assert response.json() == [
        {"label": "Denver, CO", "position": {"lat": 39.74, "lon": -104.99}},
        {"label": "Denver Depot, 1 Main St, Denver, CO", "position": {"lat": 39.75, "lon": -105.0}},
    ]
    assert cached.json() == response.json()
    assert search.call_count == 1
    assert "max-age=86400" in response["Cache-Control"]


async def test_places_query_too_short() -> None:
    response = await AsyncClient().get("/api/places", {"q": "a"})
    assert response.status_code == 422


@respx.mock
async def test_location_off_the_road_network() -> None:
    respx.get(url__startswith=ROUTING_URL).mock(
        return_value=httpx.Response(400, json={"detailedError": {"code": "MAP_MATCHING_FAILURE"}})
    )
    response = await _post(_trip())
    assert response.status_code == 422
    assert response.json()["detail"] == "One of the locations cannot be reached by road."


@respx.mock
async def test_unexpected_routing_error_is_a_gateway_error() -> None:
    respx.get(url__startswith=ROUTING_URL).mock(return_value=httpx.Response(403, text="Forbidden"))
    response = await _post(_trip())
    assert response.status_code == 502
    assert response.json()["detail"] == "Routing is temporarily unavailable."


@respx.mock
async def test_weather_rate_limit_has_specific_message() -> None:
    _mock_routing(FAST)
    respx.get(WEATHER_URL).mock(return_value=httpx.Response(429))

    response = await _post(_trip())

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "Open-Meteo rate limit reached. Please wait a minute and try again."
    )
