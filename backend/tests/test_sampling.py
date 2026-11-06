from datetime import UTC, datetime, timedelta

import pytest

from planner.domain.geo import LatLon
from planner.domain.hours_of_service import HOUR_S, StopKind, schedule_stops
from planner.domain.sampling import checkpoint_distances, locate_stops, plan_waypoints
from tests.factories import straight_path

DEPARTURE = datetime(2026, 11, 7, 8, tzinfo=UTC)


@pytest.mark.parametrize(
    ("length", "interval", "expected"),
    [
        (100.0, 25.0, [0.0, 25.0, 50.0, 75.0, 100.0]),
        (110.0, 25.0, [0.0, 25.0, 50.0, 75.0, 100.0, 110.0]),
        (100.5, 25.0, [0.0, 25.0, 50.0, 75.0, 100.5]),
        (10.0, 25.0, [0.0, 10.0]),
        (0.0, 25.0, [0.0]),
    ],
)
def test_checkpoint_distances(length: float, interval: float, expected: list[float]) -> None:
    assert checkpoint_distances(length, interval) == expected


def test_waypoint_etas_follow_driving_time() -> None:
    path = straight_path(LatLon(40.0, -100.0), LatLon(41.0, -100.0), steps=10, speed_mps=20.0)
    waypoints = plan_waypoints(path, path.length_m / 4, DEPARTURE, ())
    assert len(waypoints) == 5
    assert waypoints[0].eta == DEPARTURE
    assert waypoints[2].eta == DEPARTURE + timedelta(seconds=path.total_driving_s / 2)
    assert waypoints[-1].position.lat == pytest.approx(41.0)


def test_waypoint_etas_include_rest_stops() -> None:
    path = straight_path(LatLon(30.0, -100.0), LatLon(45.0, -100.0), steps=100, speed_mps=25.0)
    stops = schedule_stops(path.total_driving_s)
    assert path.total_driving_s > 12 * HOUR_S
    waypoints = plan_waypoints(path, path.length_m, DEPARTURE, stops)
    expected_arrival = DEPARTURE + timedelta(
        seconds=path.total_driving_s + sum(stop.duration_s for stop in stops)
    )
    assert waypoints[-1].eta == expected_arrival


def test_located_stops_have_positions_and_windows() -> None:
    path = straight_path(LatLon(30.0, -100.0), LatLon(45.0, -100.0), steps=100, speed_mps=25.0)
    located = locate_stops(path, DEPARTURE, schedule_stops(path.total_driving_s))
    first_break, first_rest = located[0], located[1]
    assert first_break.kind is StopKind.BREAK
    assert first_break.start == DEPARTURE + timedelta(hours=8)
    assert first_break.end == first_break.start + timedelta(minutes=30)
    assert first_rest.kind is StopKind.REST
    assert first_rest.start == DEPARTURE + timedelta(hours=11, minutes=30)
    assert (first_rest.position, first_rest.distance_m) == path.at_driving_time(11 * HOUR_S)
