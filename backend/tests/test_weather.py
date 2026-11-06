from datetime import UTC, datetime, timedelta

import pytest

from planner.domain.weather import ForecastGapError, HourlySeries, ceil_hour, floor_hour

START = datetime(2026, 11, 7, 0, tzinfo=UTC)
SERIES = HourlySeries(
    start=START,
    wind_mph=[10.0, 20.0, 30.0],
    gust_mph=[15.0, 25.0, 35.0],
    rain_in_hr=[0.0, 0.2, 0.4],
    snow_in_hr=[0.0, 0.5, 1.5],
)


def test_wind_interpolates_between_hours() -> None:
    conditions = SERIES.at(START + timedelta(minutes=30))
    assert conditions.wind_mph == 15.0
    assert conditions.gust_mph == 20.0


def test_precipitation_uses_the_hour_that_contains_the_moment() -> None:
    conditions = SERIES.at(START + timedelta(minutes=30))
    assert conditions.rain_in_hr == 0.2
    assert conditions.snow_in_hr == 0.5


def test_exact_hour_reads_that_hour() -> None:
    conditions = SERIES.at(START + timedelta(hours=2))
    assert conditions.wind_mph == 30.0
    assert conditions.rain_in_hr == 0.4


@pytest.mark.parametrize(
    "moment", [START - timedelta(minutes=1), START + timedelta(hours=2, minutes=1)]
)
def test_outside_series_raises(moment: datetime) -> None:
    with pytest.raises(ForecastGapError):
        SERIES.at(moment)


def test_hour_rounding() -> None:
    moment = datetime(2026, 11, 7, 5, 20, 10, tzinfo=UTC)
    assert floor_hour(moment) == datetime(2026, 11, 7, 5, tzinfo=UTC)
    assert ceil_hour(moment) == datetime(2026, 11, 7, 6, tzinfo=UTC)
    assert ceil_hour(START) == START
