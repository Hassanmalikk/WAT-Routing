import math
from bisect import bisect_left, bisect_right
from collections.abc import Sequence
from dataclasses import dataclass

EARTH_RADIUS_M = 6_371_008.8
METERS_PER_MILE = 1_609.344


@dataclass(frozen=True, slots=True)
class LatLon:
    lat: float
    lon: float


def haversine_m(a: LatLon, b: LatLon) -> float:
    phi1, phi2 = math.radians(a.lat), math.radians(b.lat)
    d_phi = phi2 - phi1
    d_lambda = math.radians(b.lon - a.lon)
    h = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


def lerp(a: float, b: float, fraction: float) -> float:
    return a + (b - a) * fraction


@dataclass(frozen=True, slots=True)
class RoutePath:
    points: Sequence[LatLon]
    distances_m: Sequence[float]
    driving_s: Sequence[float]

    def __post_init__(self) -> None:
        if not self.points or not (
            len(self.points) == len(self.distances_m) == len(self.driving_s)
        ):
            raise ValueError("Route path arrays must be non-empty and of equal length")

    @property
    def length_m(self) -> float:
        return self.distances_m[-1]

    @property
    def total_driving_s(self) -> float:
        return self.driving_s[-1]

    def _bracket(self, values: Sequence[float], target: float) -> tuple[int, float]:
        index = min(max(bisect_right(values, target) - 1, 0), len(values) - 2)
        span = values[index + 1] - values[index]
        fraction = 0.0 if span <= 0 else (target - values[index]) / span
        return index, min(max(fraction, 0.0), 1.0)

    def _position(self, index: int, fraction: float) -> LatLon:
        if len(self.points) == 1:
            return self.points[0]
        a, b = self.points[index], self.points[index + 1]
        return LatLon(lerp(a.lat, b.lat, fraction), lerp(a.lon, b.lon, fraction))

    def at_distance(self, distance_m: float) -> tuple[LatLon, float]:
        if len(self.points) == 1:
            return self.points[0], self.driving_s[0]
        index, fraction = self._bracket(self.distances_m, distance_m)
        driving = lerp(self.driving_s[index], self.driving_s[index + 1], fraction)
        return self._position(index, fraction), driving

    def at_driving_time(self, driving_s: float) -> tuple[LatLon, float]:
        if len(self.points) == 1:
            return self.points[0], self.distances_m[0]
        index, fraction = self._bracket(self.driving_s, driving_s)
        distance = lerp(self.distances_m[index], self.distances_m[index + 1], fraction)
        return self._position(index, fraction), distance

    def slice(self, start_m: float, end_m: float) -> list[LatLon]:
        start, _ = self.at_distance(start_m)
        end, _ = self.at_distance(end_m)
        first = bisect_right(self.distances_m, start_m)
        last = bisect_left(self.distances_m, end_m, lo=first)
        return [start, *self.points[first:last], end]


def simplify(points: Sequence[LatLon], tolerance_m: float) -> list[LatLon]:
    if len(points) < 3:
        return list(points)
    ref_lat = math.radians(sum(p.lat for p in points) / len(points))
    scale_x = math.cos(ref_lat) * math.pi / 180 * EARTH_RADIUS_M
    scale_y = math.pi / 180 * EARTH_RADIUS_M
    xy = [(p.lon * scale_x, p.lat * scale_y) for p in points]
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    tolerance_sq = tolerance_m**2
    while stack:
        first, last = stack.pop()
        (x1, y1), (x2, y2) = xy[first], xy[last]
        dx, dy = x2 - x1, y2 - y1
        length_sq = dx * dx + dy * dy
        worst_index, worst_sq = -1, tolerance_sq
        for i in range(first + 1, last):
            px, py = xy[i]
            if length_sq == 0:
                dist_sq = (px - x1) ** 2 + (py - y1) ** 2
            else:
                t = min(max(((px - x1) * dx + (py - y1) * dy) / length_sq, 0.0), 1.0)
                dist_sq = (px - x1 - t * dx) ** 2 + (py - y1 - t * dy) ** 2
            if dist_sq > worst_sq:
                worst_index, worst_sq = i, dist_sq
        if worst_index != -1:
            keep[worst_index] = True
            stack.extend(((first, worst_index), (worst_index, last)))
    return [point for point, kept in zip(points, keep, strict=True) if kept]
