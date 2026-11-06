from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

HOUR_S = 3_600.0
BREAK_AFTER_DRIVING_S = 8 * HOUR_S
BREAK_DURATION_S = 0.5 * HOUR_S
SHIFT_DRIVING_LIMIT_S = 11 * HOUR_S
REST_DURATION_S = 10 * HOUR_S


class StopKind(StrEnum):
    BREAK = "break"
    REST = "rest"


@dataclass(frozen=True, slots=True)
class ScheduledStop:
    kind: StopKind
    driving_s: float
    duration_s: float


def schedule_stops(total_driving_s: float) -> tuple[ScheduledStop, ...]:
    stops: list[ScheduledStop] = []
    shift_start = 0.0
    while True:
        break_at = shift_start + BREAK_AFTER_DRIVING_S
        if break_at >= total_driving_s:
            break
        stops.append(ScheduledStop(StopKind.BREAK, break_at, BREAK_DURATION_S))
        rest_at = shift_start + SHIFT_DRIVING_LIMIT_S
        if rest_at >= total_driving_s:
            break
        stops.append(ScheduledStop(StopKind.REST, rest_at, REST_DURATION_S))
        shift_start = rest_at
    return tuple(stops)


def elapsed_s(driving_s: float, stops: Sequence[ScheduledStop]) -> float:
    return driving_s + sum(stop.duration_s for stop in stops if stop.driving_s < driving_s)
