import itertools
import math
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from planner.domain.geo import LatLon, haversine_m, lerp
from planner.domain.risk import Conditions, assess

CELL_SIZES_DEG = (0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.75, 1.0, 1.5, 2.0)
METERS_PER_DEGREE = 111_195.0
FORECAST_HOURS = 48

CellIndex = tuple[int, int]


@dataclass(frozen=True, slots=True)
class Grid:
    cell_deg: float
    cells: Sequence[LatLon]


@dataclass(frozen=True, slots=True)
class Heatmap:
    cell_deg: float
    cells: Sequence[LatLon]
    hours: Sequence[datetime]
    risk: Sequence[Sequence[int]]
    wind_mph: Sequence[Sequence[float]]
    rain_in_hr: Sequence[Sequence[float]]
    snow_in_hr: Sequence[Sequence[float]]


def cell_index(point: LatLon, cell_deg: float) -> CellIndex:
    return math.floor(point.lat / cell_deg), math.floor(point.lon / cell_deg)


def cell_center(index: CellIndex, cell_deg: float) -> LatLon:
    return LatLon(round((index[0] + 0.5) * cell_deg, 4), round((index[1] + 0.5) * cell_deg, 4))


def snap_to_cell(point: LatLon, cell_deg: float) -> LatLon:
    return cell_center(cell_index(point, cell_deg), cell_deg)


def coarsest_needed_cell(points: Sequence[LatLon], max_cells: int) -> float:
    for cell_deg in CELL_SIZES_DEG:
        if len({cell_index(point, cell_deg) for point in points}) <= max_cells:
            return cell_deg
    return CELL_SIZES_DEG[-1]


def _traversed_cells(paths: Iterable[Sequence[LatLon]], cell_deg: float) -> set[CellIndex]:
    step_deg = cell_deg / 2
    traversed: set[CellIndex] = set()
    for path in paths:
        for a, b in itertools.pairwise(path):
            steps = max(1, math.ceil(max(abs(b.lat - a.lat), abs(b.lon - a.lon)) / step_deg))
            for step in range(steps + 1):
                fraction = step / steps
                point = LatLon(lerp(a.lat, b.lat, fraction), lerp(a.lon, b.lon, fraction))
                traversed.add(cell_index(point, cell_deg))
        if len(path) == 1:
            traversed.add(cell_index(path[0], cell_deg))
    return traversed


def _corridor_cells(
    paths: Sequence[Sequence[LatLon]], cell_deg: float, buffer_m: float, limit: float
) -> set[CellIndex]:
    corridor: set[CellIndex] = set()
    reach_lat = math.ceil(buffer_m / (cell_deg * METERS_PER_DEGREE))
    for base in _traversed_cells(paths, cell_deg):
        center = cell_center(base, cell_deg)
        lon_scale = max(math.cos(math.radians(center.lat)), 0.01)
        reach_lon = math.ceil(buffer_m / (cell_deg * METERS_PER_DEGREE * lon_scale))
        corridor.add(base)
        for d_lat in range(-reach_lat, reach_lat + 1):
            for d_lon in range(-reach_lon, reach_lon + 1):
                index = (base[0] + d_lat, base[1] + d_lon)
                if index not in corridor and (
                    haversine_m(center, cell_center(index, cell_deg)) <= buffer_m
                ):
                    corridor.add(index)
        if len(corridor) > limit:
            break
    return corridor


def corridor_grid(paths: Sequence[Sequence[LatLon]], buffer_m: float, max_cells: int) -> Grid:
    for cell_deg in CELL_SIZES_DEG:
        limit = math.inf if cell_deg == CELL_SIZES_DEG[-1] else max_cells
        indices = _corridor_cells(paths, cell_deg, buffer_m, limit)
        if len(indices) <= limit:
            break
    return Grid(cell_deg, [cell_center(index, cell_deg) for index in sorted(indices)])


def build_heatmap(
    grid: Grid,
    conditions_at: Callable[[LatLon, datetime], Conditions],
    departure: datetime,
    load_lb: int,
) -> Heatmap:
    hours = [departure + timedelta(hours=offset) for offset in range(FORECAST_HOURS + 1)]
    risk, wind, rain, snow = [], [], [], []
    for cell in grid.cells:
        samples = [conditions_at(cell, moment) for moment in hours]
        risk.append([int(assess(sample, load_lb).level) for sample in samples])
        wind.append([sample.wind_mph for sample in samples])
        rain.append([sample.rain_in_hr for sample in samples])
        snow.append([sample.snow_in_hr for sample in samples])
    return Heatmap(grid.cell_deg, grid.cells, hours, risk, wind, rain, snow)
