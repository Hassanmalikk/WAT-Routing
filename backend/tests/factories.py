import itertools

from planner.domain.geo import LatLon, RoutePath, haversine_m
from planner.domain.risk import Conditions

CALM = Conditions(wind_mph=5.0, gust_mph=8.0, rain_in_hr=0.0, snow_in_hr=0.0)


def straight_path(start: LatLon, end: LatLon, steps: int, speed_mps: float) -> RoutePath:
    points = [
        LatLon(
            start.lat + (end.lat - start.lat) * i / steps,
            start.lon + (end.lon - start.lon) * i / steps,
        )
        for i in range(steps + 1)
    ]
    distances = [0.0]
    for a, b in itertools.pairwise(points):
        distances.append(distances[-1] + haversine_m(a, b))
    return RoutePath(points, distances, [d / speed_mps for d in distances])
