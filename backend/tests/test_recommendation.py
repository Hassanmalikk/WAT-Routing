from datetime import UTC, datetime, timedelta

import pytest

from planner.domain.assessment import RiskSummary, RouteAssessment
from planner.domain.geo import LatLon
from planner.domain.recommendation import DecidingFactor, recommend
from tests.factories import straight_path

DEPARTURE = datetime(2026, 11, 7, 8, tzinfo=UTC)
PATH = straight_path(LatLon(40.0, -100.0), LatLon(41.0, -100.0), steps=2, speed_mps=25.0)


def _route(
    *,
    no_travel: float = 0.0,
    severe: float = 0.0,
    high: float = 0.0,
    average: float = 0.0,
    hours: float = 10.0,
) -> RouteAssessment:
    return RouteAssessment(
        path=PATH,
        departure=DEPARTURE,
        arrival=DEPARTURE + timedelta(hours=hours),
        checkpoints=[],
        segments=[],
        stops=[],
        summary=RiskSummary((0.0, 0.0, high, severe, no_travel), average),
    )


@pytest.mark.parametrize(
    ("better", "worse", "factor"),
    [
        (_route(severe=500, hours=30), _route(no_travel=1), DecidingFactor.NO_TRAVEL_MILES),
        (_route(high=500, hours=30), _route(severe=5), DecidingFactor.SEVERE_MILES),
        (_route(average=3.0, hours=30), _route(high=5), DecidingFactor.HIGH_MILES),
        (_route(average=0.5, hours=30), _route(average=0.6), DecidingFactor.AVERAGE_RISK),
        (_route(hours=9), _route(hours=10), DecidingFactor.TRAVEL_TIME),
    ],
)
def test_criteria_are_applied_in_priority_order(
    better: RouteAssessment, worse: RouteAssessment, factor: DecidingFactor
) -> None:
    recommendation = recommend([worse, better])
    assert recommendation.index == 1
    assert recommendation.runner_up_index == 0
    assert recommendation.deciding_factor is factor


def test_runner_up_is_second_best() -> None:
    recommendation = recommend([_route(hours=12), _route(hours=9), _route(hours=10)])
    assert (recommendation.index, recommendation.runner_up_index) == (1, 2)


def test_float_noise_does_not_break_ties() -> None:
    recommendation = recommend([_route(severe=10.0), _route(severe=10.0000001, hours=9)])
    assert recommendation.index == 1
    assert recommendation.deciding_factor is DecidingFactor.TRAVEL_TIME


def test_identical_routes_tie_on_first() -> None:
    recommendation = recommend([_route(), _route()])
    assert recommendation.index == 0
    assert recommendation.deciding_factor is DecidingFactor.TIE


def test_single_route() -> None:
    recommendation = recommend([_route()])
    assert recommendation.index == 0
    assert recommendation.deciding_factor is DecidingFactor.ONLY_ROUTE
    assert recommendation.runner_up_index is None


def test_empty_input_rejected() -> None:
    with pytest.raises(ValueError, match="empty"):
        recommend([])
