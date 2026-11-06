from datetime import UTC, datetime

from planner.domain.corridor import (
    FORECAST_HOURS,
    build_heatmap,
    cell_index,
    coarsest_needed_cell,
    corridor_grid,
    snap_to_cell,
)
from planner.domain.geo import METERS_PER_MILE, LatLon, haversine_m
from planner.domain.risk import Conditions, RiskLevel

BUFFER_M = 25 * METERS_PER_MILE
DEPARTURE = datetime(2026, 11, 7, 8, 30, tzinfo=UTC)


def test_snap_to_cell_returns_center() -> None:
    assert snap_to_cell(LatLon(40.04, -99.96), 0.1) == LatLon(40.05, -99.95)


def test_short_route_uses_finest_grid_and_covers_route() -> None:
    path = [LatLon(40.0, -100.0), LatLon(40.3, -100.0)]
    grid = corridor_grid([path], BUFFER_M, max_cells=500)
    assert grid.cell_deg == 0.1
    cells = {cell_index(cell, grid.cell_deg) for cell in grid.cells}
    assert cell_index(path[0], grid.cell_deg) in cells
    assert cell_index(path[1], grid.cell_deg) in cells
    assert all(
        min(haversine_m(cell, point) for point in path) <= BUFFER_M + 20_000 for cell in grid.cells
    )


def test_long_route_coarsens_within_budget() -> None:
    path = [LatLon(34.0, -118.0), LatLon(40.7, -74.0)]
    grid = corridor_grid([path], BUFFER_M, max_cells=240)
    assert grid.cell_deg > 0.1
    assert 0 < len(grid.cells) <= 240


def test_single_point_path_has_cells() -> None:
    grid = corridor_grid([[LatLon(40.0, -100.0)]], BUFFER_M, max_cells=240)
    assert grid.cells


def test_heatmap_covers_49_hours_per_cell() -> None:
    grid = corridor_grid([[LatLon(40.0, -100.0), LatLon(40.2, -100.0)]], BUFFER_M, 500)
    windy = Conditions(wind_mph=50.0, gust_mph=60.0, rain_in_hr=0.0, snow_in_hr=0.0)
    heatmap = build_heatmap(grid, lambda cell, moment: windy, DEPARTURE, load_lb=35_000)
    assert len(heatmap.hours) == FORECAST_HOURS + 1
    assert heatmap.hours[0] == DEPARTURE
    assert len(heatmap.risk) == len(grid.cells)
    assert all(len(row) == FORECAST_HOURS + 1 for row in heatmap.risk)
    assert heatmap.risk[0][0] == RiskLevel.NO_TRAVEL
    assert heatmap.wind_mph[0][0] == 50.0


def test_checkpoint_cells_coarsen_to_fit_budget() -> None:
    points = [LatLon(30.0 + i * 0.1, -100.0) for i in range(150)]
    assert coarsest_needed_cell(points, max_cells=200) == 0.1
    coarse = coarsest_needed_cell(points, max_cells=60)
    assert len({cell_index(point, coarse) for point in points}) <= 60
