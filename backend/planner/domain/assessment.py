import itertools
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from planner.domain.geo import METERS_PER_MILE, LatLon, RoutePath, simplify
from planner.domain.risk import Assessment, Conditions, RiskLevel
from planner.domain.sampling import Stop, Waypoint

SEGMENT_SIMPLIFY_TOLERANCE_M = 15.0


@dataclass(frozen=True, slots=True)
class Checkpoint:
    waypoint: Waypoint
    conditions: Conditions
    risk: Assessment

    @property
    def mile(self) -> float:
        return self.waypoint.distance_m / METERS_PER_MILE

    @property
    def position(self) -> LatLon:
        return self.waypoint.position

    @property
    def eta(self) -> datetime:
        return self.waypoint.eta


@dataclass(frozen=True, slots=True)
class Segment:
    level: RiskLevel
    start_m: float
    end_m: float
    path: Sequence[LatLon]

    @property
    def length_m(self) -> float:
        return self.end_m - self.start_m


@dataclass(frozen=True, slots=True)
class RiskSummary:
    miles_by_level: tuple[float, ...]
    average_risk: float

    def miles(self, level: RiskLevel) -> float:
        return self.miles_by_level[level]


@dataclass(frozen=True, slots=True)
class RouteAssessment:
    path: RoutePath
    departure: datetime
    arrival: datetime
    checkpoints: Sequence[Checkpoint]
    segments: Sequence[Segment]
    stops: Sequence[Stop]
    summary: RiskSummary

    @property
    def duration_s(self) -> float:
        return (self.arrival - self.departure).total_seconds()


def build_segments(path: RoutePath, checkpoints: Sequence[Checkpoint]) -> list[Segment]:
    segments = []
    for start, end in itertools.pairwise(checkpoints):
        start_m, end_m = start.waypoint.distance_m, end.waypoint.distance_m
        segments.append(
            Segment(
                level=max(start.risk.level, end.risk.level),
                start_m=start_m,
                end_m=end_m,
                path=simplify(path.slice(start_m, end_m), SEGMENT_SIMPLIFY_TOLERANCE_M),
            )
        )
    return segments


def summarize(segments: Sequence[Segment], checkpoints: Sequence[Checkpoint]) -> RiskSummary:
    meters = [0.0] * len(RiskLevel)
    for segment in segments:
        meters[segment.level] += segment.length_m
    total_m = sum(meters)
    if total_m > 0:
        average = sum(level * length for level, length in enumerate(meters)) / total_m
    else:
        average = float(max(checkpoint.risk.level for checkpoint in checkpoints))
    return RiskSummary(
        miles_by_level=tuple(length / METERS_PER_MILE for length in meters),
        average_risk=average,
    )


def assess_route(
    path: RoutePath,
    departure: datetime,
    checkpoints: Sequence[Checkpoint],
    stops: Sequence[Stop],
) -> RouteAssessment:
    segments = build_segments(path, checkpoints)
    return RouteAssessment(
        path=path,
        departure=departure,
        arrival=checkpoints[-1].eta,
        checkpoints=checkpoints,
        segments=segments,
        stops=stops,
        summary=summarize(segments, checkpoints),
    )
