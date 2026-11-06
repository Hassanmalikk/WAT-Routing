import pytest

from planner.domain.geo import LatLon, RoutePath, haversine_m, simplify
from tests.factories import straight_path

ORIGIN = LatLon(40.0, -100.0)
DESTINATION = LatLon(41.0, -100.0)


def test_haversine_one_degree_of_latitude() -> None:
    assert haversine_m(ORIGIN, DESTINATION) == pytest.approx(111_195, rel=1e-3)


def test_path_rejects_mismatched_arrays() -> None:
    with pytest.raises(ValueError, match="equal length"):
        RoutePath([ORIGIN, DESTINATION], [0.0], [0.0, 1.0])


def test_at_distance_interpolates_position_and_time() -> None:
    path = straight_path(ORIGIN, DESTINATION, steps=4, speed_mps=25.0)
    position, driving = path.at_distance(path.length_m / 2)
    assert position.lat == pytest.approx(40.5)
    assert driving == pytest.approx(path.total_driving_s / 2)


def test_at_distance_clamps_to_route_ends() -> None:
    path = straight_path(ORIGIN, DESTINATION, steps=4, speed_mps=25.0)
    assert path.at_distance(-10.0)[0] == ORIGIN
    end, driving = path.at_distance(path.length_m + 10.0)
    assert end == DESTINATION
    assert driving == path.total_driving_s


def test_at_driving_time_locates_position() -> None:
    path = straight_path(ORIGIN, DESTINATION, steps=10, speed_mps=25.0)
    position, distance = path.at_driving_time(path.total_driving_s * 0.25)
    assert position.lat == pytest.approx(40.25)
    assert distance == pytest.approx(path.length_m * 0.25)


def test_single_point_path() -> None:
    path = RoutePath([ORIGIN], [0.0], [0.0])
    assert path.at_distance(5.0) == (ORIGIN, 0.0)
    assert path.at_driving_time(5.0) == (ORIGIN, 0.0)


def test_slice_includes_interior_vertices_and_exact_ends() -> None:
    path = straight_path(ORIGIN, DESTINATION, steps=10, speed_mps=25.0)
    sliced = path.slice(path.distances_m[2] + 1.0, path.distances_m[5])
    assert len(sliced) == 4
    assert sliced[1:3] == list(path.points[3:5])
    assert sliced[-1].lat == pytest.approx(path.points[5].lat)


def test_simplify_drops_collinear_points_and_keeps_corners() -> None:
    line = [LatLon(40.0, -100.0 + i * 0.01) for i in range(50)]
    corner = LatLon(40.5, -99.5)
    simplified = simplify([*line, corner], tolerance_m=10.0)
    assert simplified == [line[0], line[-1], corner]


def test_simplify_short_inputs_untouched() -> None:
    assert simplify([ORIGIN, DESTINATION], 10.0) == [ORIGIN, DESTINATION]
