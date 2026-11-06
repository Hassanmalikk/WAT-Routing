import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from planner.domain.geo import LatLon, RoutePath
from planner.domain.hours_of_service import ScheduledStop, StopKind, elapsed_s

DESTINATION_SNAP_M = 1.0


@dataclass(frozen=True, slots=True)
class Waypoint:
    distance_m: float
    position: LatLon
    eta: datetime


@dataclass(frozen=True, slots=True)
class Stop:
    kind: StopKind
    distance_m: float
    position: LatLon
    start: datetime
    end: datetime


def checkpoint_distances(length_m: float, interval_m: float) -> list[float]:
    distances = [step * interval_m for step in range(math.floor(length_m / interval_m) + 1)]
    if length_m - distances[-1] > DESTINATION_SNAP_M:
        distances.append(length_m)
    else:
        distances[-1] = length_m
    return distances


def _eta(departure: datetime, driving_s: float, stops: Sequence[ScheduledStop]) -> datetime:
    return departure + timedelta(seconds=elapsed_s(driving_s, stops))


def plan_waypoints(
    path: RoutePath,
    interval_m: float,
    departure: datetime,
    stops: Sequence[ScheduledStop],
) -> list[Waypoint]:
    waypoints = []
    for distance in checkpoint_distances(path.length_m, interval_m):
        position, driving = path.at_distance(distance)
        waypoints.append(Waypoint(distance, position, _eta(departure, driving, stops)))
    return waypoints


def locate_stops(
    path: RoutePath, departure: datetime, stops: Sequence[ScheduledStop]
) -> list[Stop]:
    located = []
    for stop in stops:
        start = _eta(departure, stop.driving_s, stops)
        position, distance = path.at_driving_time(stop.driving_s)
        located.append(
            Stop(
                kind=stop.kind,
                distance_m=distance,
                position=position,
                start=start,
                end=start + timedelta(seconds=stop.duration_s),
            )
        )
    return located
