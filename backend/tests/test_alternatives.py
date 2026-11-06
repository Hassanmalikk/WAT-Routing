from planner.domain.alternatives import detour_boxes, distinct_routes
from planner.domain.geo import LatLon
from tests.factories import straight_path

NORTH = straight_path(LatLon(40.0, -100.0), LatLon(41.0, -100.0), steps=100, speed_mps=25.0)
EAST = straight_path(LatLon(40.0, -100.0), LatLon(40.0, -99.0), steps=100, speed_mps=25.0)
DIAGONAL = straight_path(LatLon(40.0, -100.0), LatLon(41.0, -99.0), steps=100, speed_mps=30.0)


def test_duplicates_are_removed() -> None:
    assert distinct_routes([NORTH, NORTH, EAST], limit=3) == [NORTH, EAST]


def test_limit_is_respected_in_order() -> None:
    assert distinct_routes([NORTH, EAST, DIAGONAL], limit=2) == [NORTH, EAST]


def test_same_geometry_with_different_timing_is_duplicate() -> None:
    slower = straight_path(LatLon(40.0, -100.0), LatLon(41.0, -100.0), steps=100, speed_mps=20.0)
    assert distinct_routes([NORTH, slower], limit=3) == [NORTH]


def test_detour_box_surrounds_route_midpoint() -> None:
    [box] = detour_boxes([NORTH], NORTH.points[0], NORTH.points[-1])
    assert box.contains(LatLon(40.5, -100.0))
    assert not box.contains(NORTH.points[0])
    assert not box.contains(NORTH.points[-1])


def test_detour_box_skipped_when_it_would_cover_an_endpoint() -> None:
    short = straight_path(LatLon(40.0, -100.0), LatLon(40.001, -100.0), steps=2, speed_mps=10.0)
    assert detour_boxes([short], short.points[0], short.points[-1]) == []
