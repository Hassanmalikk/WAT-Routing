import itertools
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime

from planner.domain.assessment import RouteAssessment
from planner.domain.geo import METERS_PER_MILE
from planner.domain.recommendation import Recommendation

LEVEL_NAMES = ("Low", "Moderate", "High", "Severe", "No travel")
HIGH, SEVERE, NO_TRAVEL = 2, 3, 4

DISTANCE_TOLERANCE_M = 1.0
MILES_TOLERANCE = 0.05
AVERAGE_TOLERANCE = 0.001
TIME_TOLERANCE_S = 1.0

HOUR_S = 3_600.0
BREAK_DUE_AFTER_DRIVING_S = 8 * HOUR_S
REST_DUE_AFTER_DRIVING_S = 11 * HOUR_S
STOP_DURATIONS_S = {"break": 0.5 * HOUR_S, "rest": 10 * HOUR_S}


@dataclass(frozen=True, slots=True)
class PlanInputs:
    departure: datetime
    interval_m: float
    load_lb: int
    rest_breaks: bool


@dataclass(frozen=True, slots=True)
class Check:
    key: str
    title: str
    passed: bool
    detail: str


@dataclass(frozen=True, slots=True)
class Verification:
    checks: tuple[Check, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)


Routes = Sequence[RouteAssessment]


def _route(index: int) -> str:
    return f"Route {chr(65 + index)}"


def _mile(distance_m: float) -> str:
    return f"mile {distance_m / METERS_PER_MILE:.0f}"


def _wind_level(wind_mph: float, load_lb: int) -> tuple[int, bool]:
    if wind_mph >= 55:
        return 4, False
    if wind_mph >= 45:
        return (4, True) if load_lb > 30_000 else (3, False)
    if wind_mph >= 35:
        return (3, True) if load_lb > 40_000 else (2, False)
    return (1 if wind_mph >= 25 else 0), False


def _rain_level(rain_in_hr: float) -> int:
    if rain_in_hr > 1.00:
        return 4
    if rain_in_hr >= 0.50:
        return 3
    if rain_in_hr >= 0.25:
        return 2
    return 1 if rain_in_hr >= 0.10 else 0


def _snow_level(snow_in_hr: float) -> int:
    if snow_in_hr > 3.0:
        return 4
    if snow_in_hr >= 2.0:
        return 3
    if snow_in_hr >= 1.0:
        return 2
    return 1 if snow_in_hr >= 0.5 else 0


def _risk_table(routes: Routes, inputs: PlanInputs, _: Recommendation) -> list[str]:
    problems = []
    for index, route in enumerate(routes):
        for checkpoint in route.checkpoints:
            conditions, risk = checkpoint.conditions, checkpoint.risk
            wind, adjusted = _wind_level(conditions.wind_mph, inputs.load_lb)
            rain = _rain_level(conditions.rain_in_hr)
            snow = _snow_level(conditions.snow_in_hr)
            expected = (max(wind, rain, snow), wind, rain, snow, adjusted)
            actual = (risk.level, risk.wind, risk.rain, risk.snow, risk.load_adjusted)
            if expected != actual:
                problems.append(
                    f"{_route(index)}, {_mile(checkpoint.waypoint.distance_m)}: expected "
                    f"{LEVEL_NAMES[expected[0]]}, planner gave {LEVEL_NAMES[risk.level]}"
                )
    return problems


def _checkpoint_spacing(routes: Routes, inputs: PlanInputs, _: Recommendation) -> list[str]:
    problems = []
    for index, route in enumerate(routes):
        distances = [checkpoint.waypoint.distance_m for checkpoint in route.checkpoints]
        gaps = [end - start for start, end in itertools.pairwise(distances)]
        if abs(distances[0]) > DISTANCE_TOLERANCE_M:
            problems.append(f"{_route(index)}: first checkpoint is not at the origin")
        if abs(distances[-1] - route.path.length_m) > DISTANCE_TOLERANCE_M:
            problems.append(f"{_route(index)}: last checkpoint is not at the destination")
        if any(abs(gap - inputs.interval_m) > DISTANCE_TOLERANCE_M for gap in gaps[:-1]):
            problems.append(f"{_route(index)}: checkpoints are not evenly spaced")
        if gaps and not 0 < gaps[-1] <= inputs.interval_m + DISTANCE_TOLERANCE_M:
            problems.append(f"{_route(index)}: final gap exceeds the checkpoint interval")
    return problems


def _eta_timeline(routes: Routes, inputs: PlanInputs, _: Recommendation) -> list[str]:
    problems = []
    for index, route in enumerate(routes):
        etas = [checkpoint.waypoint.eta for checkpoint in route.checkpoints]
        if route.departure != inputs.departure or etas[0] != inputs.departure:
            problems.append(f"{_route(index)}: first ETA is not the departure time")
        if any(later < earlier for earlier, later in itertools.pairwise(etas)):
            problems.append(f"{_route(index)}: ETAs go backwards along the route")
        if route.arrival != etas[-1]:
            problems.append(f"{_route(index)}: arrival differs from the destination ETA")
    return problems


def _segment_levels(routes: Routes, _: PlanInputs, __: Recommendation) -> list[str]:
    problems = []
    for index, route in enumerate(routes):
        pairs = list(itertools.pairwise(route.checkpoints))
        if len(pairs) != len(route.segments):
            problems.append(f"{_route(index)}: stretches do not join consecutive checkpoints")
            continue
        for segment, (start, end) in zip(route.segments, pairs, strict=True):
            joined = (
                abs(segment.start_m - start.waypoint.distance_m) <= DISTANCE_TOLERANCE_M
                and abs(segment.end_m - end.waypoint.distance_m) <= DISTANCE_TOLERANCE_M
            )
            if not joined or segment.level != max(start.risk.level, end.risk.level):
                problems.append(
                    f"{_route(index)}, {_mile(segment.start_m)}: stretch level is not the "
                    "worse of its two checkpoints"
                )
    return problems


def _mileage(routes: Routes, _: PlanInputs, __: Recommendation) -> list[str]:
    problems = []
    for index, route in enumerate(routes):
        by_level = [0.0] * len(LEVEL_NAMES)
        for segment in route.segments:
            by_level[segment.level] += (segment.end_m - segment.start_m) / METERS_PER_MILE
        reported = route.summary.miles_by_level
        if any(abs(a - b) > MILES_TOLERANCE for a, b in zip(by_level, reported, strict=True)):
            problems.append(f"{_route(index)}: miles per level differ from its stretches")
        if abs(sum(reported) - route.path.length_m / METERS_PER_MILE) > MILES_TOLERANCE:
            problems.append(f"{_route(index)}: risk miles do not add up to the route length")
    return problems


def _average_risk(routes: Routes, _: PlanInputs, __: Recommendation) -> list[str]:
    problems = []
    for index, route in enumerate(routes):
        lengths = [segment.end_m - segment.start_m for segment in route.segments]
        total = sum(lengths)
        expected = (
            sum(s.level * length for s, length in zip(route.segments, lengths, strict=True)) / total
            if total > 0
            else max(checkpoint.risk.level for checkpoint in route.checkpoints)
        )
        if abs(expected - route.summary.average_risk) > AVERAGE_TOLERANCE:
            problems.append(
                f"{_route(index)}: average risk should be {expected:.3f}, "
                f"planner gave {route.summary.average_risk:.3f}"
            )
    return problems


def _hours_of_service(routes: Routes, inputs: PlanInputs, _: Recommendation) -> list[str]:
    problems = []
    for index, route in enumerate(routes):
        name = _route(index)
        driving_total = route.path.total_driving_s
        stop_total = sum((stop.end - stop.start).total_seconds() for stop in route.stops)
        if abs(route.duration_s - driving_total - stop_total) > TIME_TOLERANCE_S:
            problems.append(f"{name}: trip time is not driving time plus stops")
        if not inputs.rest_breaks:
            if route.stops:
                problems.append(f"{name}: stops were added although they are switched off")
            continue
        since_break = since_rest = previous_driving = stopped = 0.0
        for stop in route.stops:
            driving = (stop.start - inputs.departure).total_seconds() - stopped
            since_break += driving - previous_driving
            since_rest += driving - previous_driving
            duration = (stop.end - stop.start).total_seconds()
            if abs(duration - STOP_DURATIONS_S[stop.kind]) > TIME_TOLERANCE_S:
                problems.append(f"{name}: {stop.kind} at {_mile(stop.distance_m)} is too short")
            if not 0 <= stop.distance_m <= route.path.length_m + DISTANCE_TOLERANCE_M:
                problems.append(f"{name}: {stop.kind} is placed off the route")
            if since_break > BREAK_DUE_AFTER_DRIVING_S + TIME_TOLERANCE_S:
                problems.append(f"{name}: over 8 h of driving before {_mile(stop.distance_m)}")
            if since_rest > REST_DUE_AFTER_DRIVING_S + TIME_TOLERANCE_S:
                problems.append(f"{name}: over 11 h of driving before {_mile(stop.distance_m)}")
            since_break = 0.0
            since_rest = 0.0 if stop.kind == "rest" else since_rest
            previous_driving, stopped = driving, stopped + duration
        remaining = driving_total - previous_driving
        if since_break + remaining > BREAK_DUE_AFTER_DRIVING_S + TIME_TOLERANCE_S:
            problems.append(f"{name}: over 8 h of driving without a 30 min break")
        if since_rest + remaining > REST_DUE_AFTER_DRIVING_S + TIME_TOLERANCE_S:
            problems.append(f"{name}: over 11 h of driving without a 10 h rest")
    return problems


def _priority(route: RouteAssessment) -> tuple[float, ...]:
    miles = route.summary.miles_by_level
    return (
        round(miles[NO_TRAVEL], 1),
        round(miles[SEVERE], 1),
        round(miles[HIGH], 1),
        round(route.summary.average_risk, 3),
        round(route.duration_s / 60),
    )


def _recommendation(routes: Routes, _: PlanInputs, chosen: Recommendation) -> list[str]:
    best = _priority(routes[chosen.index])
    return [
        f"{_route(index)} ranks ahead of the recommended {_route(chosen.index)}"
        for index, route in enumerate(routes)
        if _priority(route) < best
    ]


Rule = Callable[[Routes, PlanInputs, Recommendation], list[str]]

RULES: tuple[tuple[str, str, str, Rule], ...] = (
    (
        "risk_table",
        "Risk table and load rules",
        "Every checkpoint level matches the wind, rain and snow bands and the load limits.",
        _risk_table,
    ),
    (
        "checkpoint_spacing",
        "Checkpoint spacing",
        "Checkpoints start at the origin, repeat at the chosen interval and end at the "
        "destination.",
        _checkpoint_spacing,
    ),
    (
        "eta_timeline",
        "Arrival times",
        "ETAs start at departure, never go backwards and end at the arrival time.",
        _eta_timeline,
    ),
    (
        "segment_levels",
        "Stretch levels",
        "Every stretch between two checkpoints takes the worse of their two levels.",
        _segment_levels,
    ),
    (
        "mileage",
        "Mileage",
        "Miles per risk level match the stretches and add up to the route length.",
        _mileage,
    ),
    (
        "average_risk",
        "Average risk",
        "The mile-weighted average risk is recomputed and matches.",
        _average_risk,
    ),
    (
        "hours_of_service",
        "Hours of service",
        "No more than 8 h of driving without a 30 min break or 11 h without a 10 h rest.",
        _hours_of_service,
    ),
    (
        "recommendation",
        "Recommendation order",
        "No route beats the recommended one on no-travel, severe and high miles, average "
        "risk, then time.",
        _recommendation,
    ),
)


def verify(routes: Routes, recommendation: Recommendation, inputs: PlanInputs) -> Verification:
    checks = []
    for key, title, success, rule in RULES:
        problems = rule(routes, inputs, recommendation)
        detail = success if not problems else "; ".join(problems[:3])
        if len(problems) > 3:
            detail += f"; and {len(problems) - 3} more"
        checks.append(Check(key, title, not problems, detail))
    return Verification(tuple(checks))
