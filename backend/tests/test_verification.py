import dataclasses
from datetime import UTC, datetime

from planner.domain.assessment import Checkpoint, RouteAssessment, assess_route
from planner.domain.geo import METERS_PER_MILE, LatLon, RoutePath
from planner.domain.hours_of_service import schedule_stops
from planner.domain.recommendation import Recommendation, recommend
from planner.domain.risk import Conditions, RiskLevel, assess
from planner.domain.sampling import locate_stops, plan_waypoints
from planner.domain.verification import PlanInputs, Verification, verify
from tests.factories import CALM, straight_path

DEPARTURE = datetime(2026, 11, 7, 8, tzinfo=UTC)
INPUTS = PlanInputs(
    departure=DEPARTURE, interval_m=25 * METERS_PER_MILE, load_lb=42_000, rest_breaks=True
)
LONG = straight_path(LatLon(30.0, -100.0), LatLon(45.0, -100.0), steps=200, speed_mps=25.0)
SHORT = straight_path(LatLon(40.0, -100.0), LatLon(41.0, -100.0), steps=40, speed_mps=25.0)
WINDY = Conditions(wind_mph=38.0, gust_mph=50.0, rain_in_hr=0.3, snow_in_hr=0.0)


def _route(path: RoutePath, conditions: Conditions = CALM) -> RouteAssessment:
    schedule = schedule_stops(path.total_driving_s)
    waypoints = plan_waypoints(path, INPUTS.interval_m, DEPARTURE, schedule)
    checkpoints = [
        Checkpoint(waypoint, conditions, assess(conditions, INPUTS.load_lb))
        for waypoint in waypoints
    ]
    return assess_route(path, DEPARTURE, checkpoints, locate_stops(path, DEPARTURE, schedule))


def _failed(verification: Verification) -> set[str]:
    return {check.key for check in verification.checks if not check.passed}


def test_planned_routes_pass_every_check() -> None:
    routes = [_route(LONG), _route(SHORT, WINDY)]
    verification = verify(routes, recommend(routes), INPUTS)
    assert verification.passed
    assert len(verification.checks) == 8


def test_wrong_checkpoint_level_is_caught() -> None:
    route = _route(SHORT, WINDY)
    tampered = route.checkpoints[2]
    wrong = dataclasses.replace(tampered.risk, level=RiskLevel.LOW, wind=RiskLevel.HIGH)
    checkpoints = [*route.checkpoints]
    checkpoints[2] = Checkpoint(tampered.waypoint, tampered.conditions, wrong)
    broken = dataclasses.replace(route, checkpoints=checkpoints)
    assert "risk_table" in _failed(verify([broken], recommend([broken]), INPUTS))


def test_missing_rest_is_caught() -> None:
    route = _route(LONG)
    assert len(route.stops) >= 2
    broken = dataclasses.replace(route, stops=route.stops[:1])
    assert "hours_of_service" in _failed(verify([broken], recommend([broken]), INPUTS))


def test_stops_when_switched_off_are_caught() -> None:
    route = _route(LONG)
    inputs = dataclasses.replace(INPUTS, rest_breaks=False)
    assert "hours_of_service" in _failed(verify([route], recommend([route]), inputs))


def test_wrong_stretch_level_is_caught() -> None:
    route = _route(SHORT)
    segments = [*route.segments]
    segments[0] = dataclasses.replace(segments[0], level=RiskLevel.SEVERE)
    broken = dataclasses.replace(route, segments=segments)
    assert {"segment_levels", "mileage"} <= _failed(verify([broken], recommend([broken]), INPUTS))


def test_worse_route_recommended_is_caught() -> None:
    routes = [_route(SHORT), _route(SHORT, WINDY)]
    wrong = Recommendation(
        index=1, deciding_factor=recommend(routes).deciding_factor, runner_up_index=0
    )
    failed = _failed(verify(routes, wrong, INPUTS))
    assert failed == {"recommendation"}


def test_load_rule_applies_above_limit_only() -> None:
    light = dataclasses.replace(INPUTS, load_lb=20_000)
    route = _route(SHORT, WINDY)
    failed = _failed(verify([route], recommend([route]), light))
    assert failed == {"risk_table"}
