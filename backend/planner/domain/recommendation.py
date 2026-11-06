from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from planner.domain.assessment import RouteAssessment
from planner.domain.risk import RiskLevel


class DecidingFactor(StrEnum):
    ONLY_ROUTE = "only_route"
    NO_TRAVEL_MILES = "no_travel_miles"
    SEVERE_MILES = "severe_miles"
    HIGH_MILES = "high_miles"
    AVERAGE_RISK = "average_risk"
    TRAVEL_TIME = "travel_time"
    TIE = "tie"


CRITERIA = (
    DecidingFactor.NO_TRAVEL_MILES,
    DecidingFactor.SEVERE_MILES,
    DecidingFactor.HIGH_MILES,
    DecidingFactor.AVERAGE_RISK,
    DecidingFactor.TRAVEL_TIME,
)


@dataclass(frozen=True, slots=True)
class Recommendation:
    index: int
    deciding_factor: DecidingFactor
    runner_up_index: int | None


def ranking_key(route: RouteAssessment) -> tuple[float, ...]:
    summary = route.summary
    return (
        round(summary.miles(RiskLevel.NO_TRAVEL), 1),
        round(summary.miles(RiskLevel.SEVERE), 1),
        round(summary.miles(RiskLevel.HIGH), 1),
        round(summary.average_risk, 3),
        round(route.duration_s / 60),
    )


def recommend(routes: Sequence[RouteAssessment]) -> Recommendation:
    if not routes:
        raise ValueError("Cannot recommend from an empty set of routes")
    keys = [ranking_key(route) for route in routes]
    order = sorted(range(len(routes)), key=keys.__getitem__)
    best = order[0]
    if len(order) == 1:
        return Recommendation(best, DecidingFactor.ONLY_ROUTE, None)
    runner_up = order[1]
    factor = next(
        (
            criterion
            for criterion, best_value, other_value in zip(
                CRITERIA, keys[best], keys[runner_up], strict=True
            )
            if best_value != other_value
        ),
        DecidingFactor.TIE,
    )
    return Recommendation(best, factor, runner_up)
