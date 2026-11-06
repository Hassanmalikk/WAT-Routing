import pytest

from planner.domain.hours_of_service import (
    HOUR_S,
    ScheduledStop,
    StopKind,
    elapsed_s,
    schedule_stops,
)

BREAK = StopKind.BREAK
REST = StopKind.REST


@pytest.mark.parametrize(
    ("driving_hours", "expected"),
    [
        (5, []),
        (8, []),
        (9, [(BREAK, 8)]),
        (11, [(BREAK, 8)]),
        (12, [(BREAK, 8), (REST, 11)]),
        (19.5, [(BREAK, 8), (REST, 11), (BREAK, 19)]),
        (23, [(BREAK, 8), (REST, 11), (BREAK, 19), (REST, 22)]),
    ],
)
def test_schedule(driving_hours: float, expected: list[tuple[StopKind, float]]) -> None:
    stops = schedule_stops(driving_hours * HOUR_S)
    assert [(stop.kind, stop.driving_s / HOUR_S) for stop in stops] == expected


def test_elapsed_adds_only_completed_stops() -> None:
    stops = (
        ScheduledStop(BREAK, 8 * HOUR_S, 0.5 * HOUR_S),
        ScheduledStop(REST, 11 * HOUR_S, 10 * HOUR_S),
    )
    assert elapsed_s(8 * HOUR_S, stops) == 8 * HOUR_S
    assert elapsed_s(9 * HOUR_S, stops) == 9.5 * HOUR_S
    assert elapsed_s(12 * HOUR_S, stops) == 22.5 * HOUR_S
