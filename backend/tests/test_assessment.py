from datetime import UTC, datetime

import pytest

from planner.domain.assessment import Checkpoint, assess_route
from planner.domain.geo import METERS_PER_MILE, LatLon
from planner.domain.risk import Assessment, RiskLevel
from planner.domain.sampling import plan_waypoints
from tests.factories import CALM, straight_path

DEPARTURE = datetime(2026, 11, 7, 8, tzinfo=UTC)
PATH = straight_path(LatLon(40.0, -100.0), LatLon(41.0, -100.0), steps=20, speed_mps=25.0)


def _checkpoints(levels: list[RiskLevel]) -> list[Checkpoint]:
    waypoints = plan_waypoints(PATH, PATH.length_m / (len(levels) - 1), DEPARTURE, ())
    assert len(waypoints) == len(levels)
    return [
        Checkpoint(waypoint, CALM, Assessment(level, level, RiskLevel.LOW, RiskLevel.LOW, False))
        for waypoint, level in zip(waypoints, levels, strict=True)
    ]


def test_segments_take_worse_endpoint() -> None:
    checkpoints = _checkpoints([RiskLevel.LOW, RiskLevel.HIGH, RiskLevel.LOW, RiskLevel.LOW])
    route = assess_route(PATH, DEPARTURE, checkpoints, [])
    assert [segment.level for segment in route.segments] == [
        RiskLevel.HIGH,
        RiskLevel.HIGH,
        RiskLevel.LOW,
    ]
    assert route.segments[0].path[0] == PATH.points[0]
    assert route.segments[-1].path[-1].lat == pytest.approx(PATH.points[-1].lat)


def test_summary_weights_by_miles() -> None:
    checkpoints = _checkpoints([RiskLevel.LOW, RiskLevel.SEVERE, RiskLevel.LOW, RiskLevel.LOW])
    route = assess_route(PATH, DEPARTURE, checkpoints, [])
    third = PATH.length_m / 3 / METERS_PER_MILE
    assert route.summary.miles(RiskLevel.SEVERE) == pytest.approx(2 * third)
    assert route.summary.miles(RiskLevel.LOW) == pytest.approx(third)
    assert route.summary.average_risk == pytest.approx(2.0)
    assert sum(route.summary.miles_by_level) == pytest.approx(PATH.length_m / METERS_PER_MILE)


def test_arrival_is_last_checkpoint_eta() -> None:
    checkpoints = _checkpoints([RiskLevel.LOW, RiskLevel.LOW])
    route = assess_route(PATH, DEPARTURE, checkpoints, [])
    assert route.arrival == checkpoints[-1].eta
    assert route.duration_s == pytest.approx(PATH.total_driving_s)
