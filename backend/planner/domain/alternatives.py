import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from planner.domain.geo import LatLon, RoutePath, haversine_m

DUPLICATE_OVERLAP_RATIO = 0.97
FOOTPRINT_PRECISION = 5
DETOUR_BOX_FRACTION = 0.06
MIN_DETOUR_HALF_SIZE_M = 3_000.0
MAX_DETOUR_HALF_SIZE_M = 60_000.0
METERS_PER_DEGREE = 111_195.0


@dataclass(frozen=True, slots=True)
class Box:
    south_west: LatLon
    north_east: LatLon

    def contains(self, point: LatLon) -> bool:
        return (
            self.south_west.lat <= point.lat <= self.north_east.lat
            and self.south_west.lon <= point.lon <= self.north_east.lon
        )


def _footprint(path: RoutePath) -> frozenset[tuple[float, float]]:
    return frozenset(
        (round(point.lat, FOOTPRINT_PRECISION), round(point.lon, FOOTPRINT_PRECISION))
        for point in path.points
    )


def distinct_routes(candidates: Iterable[RoutePath], limit: int) -> list[RoutePath]:
    selected: list[RoutePath] = []
    footprints: list[frozenset[tuple[float, float]]] = []
    for candidate in candidates:
        footprint = _footprint(candidate)
        if all(
            len(footprint & other) / min(len(footprint), len(other)) < DUPLICATE_OVERLAP_RATIO
            for other in footprints
        ):
            selected.append(candidate)
            footprints.append(footprint)
            if len(selected) == limit:
                break
    return selected


def detour_boxes(paths: Sequence[RoutePath], origin: LatLon, destination: LatLon) -> list[Box]:
    half_size_m = min(
        max(DETOUR_BOX_FRACTION * haversine_m(origin, destination), MIN_DETOUR_HALF_SIZE_M),
        MAX_DETOUR_HALF_SIZE_M,
    )
    boxes = []
    for path in paths:
        middle, _ = path.at_distance(path.length_m / 2)
        d_lat = half_size_m / METERS_PER_DEGREE
        d_lon = d_lat / max(math.cos(math.radians(middle.lat)), 0.01)
        box = Box(
            LatLon(middle.lat - d_lat, middle.lon - d_lon),
            LatLon(middle.lat + d_lat, middle.lon + d_lon),
        )
        if not (box.contains(origin) or box.contains(destination)):
            boxes.append(box)
    return boxes
