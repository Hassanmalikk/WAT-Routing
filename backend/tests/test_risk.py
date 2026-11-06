import pytest

from planner.domain.risk import (
    Conditions,
    RiskLevel,
    assess,
    classify_rain,
    classify_snow,
    classify_wind,
)

LIGHT_LOAD = 10_000


@pytest.mark.parametrize(
    ("wind", "expected"),
    [
        (0.0, RiskLevel.LOW),
        (24.9, RiskLevel.LOW),
        (25.0, RiskLevel.MODERATE),
        (34.9, RiskLevel.MODERATE),
        (35.0, RiskLevel.HIGH),
        (44.9, RiskLevel.HIGH),
        (45.0, RiskLevel.SEVERE),
        (54.9, RiskLevel.SEVERE),
        (55.0, RiskLevel.NO_TRAVEL),
        (90.0, RiskLevel.NO_TRAVEL),
    ],
)
def test_wind_bands(wind: float, expected: RiskLevel) -> None:
    assert classify_wind(wind, LIGHT_LOAD) == (expected, False)


@pytest.mark.parametrize(
    ("rain", "expected"),
    [
        (0.0, RiskLevel.LOW),
        (0.099, RiskLevel.LOW),
        (0.10, RiskLevel.MODERATE),
        (0.249, RiskLevel.MODERATE),
        (0.25, RiskLevel.HIGH),
        (0.499, RiskLevel.HIGH),
        (0.50, RiskLevel.SEVERE),
        (1.00, RiskLevel.SEVERE),
        (1.001, RiskLevel.NO_TRAVEL),
    ],
)
def test_rain_bands(rain: float, expected: RiskLevel) -> None:
    assert classify_rain(rain) is expected


@pytest.mark.parametrize(
    ("snow", "expected"),
    [
        (0.0, RiskLevel.LOW),
        (0.49, RiskLevel.LOW),
        (0.5, RiskLevel.MODERATE),
        (0.99, RiskLevel.MODERATE),
        (1.0, RiskLevel.HIGH),
        (1.99, RiskLevel.HIGH),
        (2.0, RiskLevel.SEVERE),
        (3.0, RiskLevel.SEVERE),
        (3.01, RiskLevel.NO_TRAVEL),
    ],
)
def test_snow_bands(snow: float, expected: RiskLevel) -> None:
    assert classify_snow(snow) is expected


@pytest.mark.parametrize(
    ("wind", "load", "expected"),
    [
        (60.0, 1, (RiskLevel.NO_TRAVEL, False)),
        (50.0, 30_000, (RiskLevel.SEVERE, False)),
        (50.0, 30_001, (RiskLevel.NO_TRAVEL, True)),
        (40.0, 40_000, (RiskLevel.HIGH, False)),
        (40.0, 40_001, (RiskLevel.SEVERE, True)),
        (40.0, 35_000, (RiskLevel.HIGH, False)),
        (30.0, 80_000, (RiskLevel.MODERATE, False)),
    ],
)
def test_load_rules(wind: float, load: int, expected: tuple[RiskLevel, bool]) -> None:
    assert classify_wind(wind, load) == expected


def test_assessment_takes_worst_condition() -> None:
    assessment = assess(
        Conditions(wind_mph=30.0, gust_mph=40.0, rain_in_hr=0.3, snow_in_hr=0.0), LIGHT_LOAD
    )
    assert assessment.level is RiskLevel.HIGH
    assert (assessment.wind, assessment.rain, assessment.snow) == (
        RiskLevel.MODERATE,
        RiskLevel.HIGH,
        RiskLevel.LOW,
    )


def test_assessment_flags_load_adjustment() -> None:
    assessment = assess(
        Conditions(wind_mph=46.0, gust_mph=60.0, rain_in_hr=0.0, snow_in_hr=0.0), 35_000
    )
    assert assessment.level is RiskLevel.NO_TRAVEL
    assert assessment.load_adjusted


def test_gusts_do_not_drive_classification() -> None:
    assessment = assess(
        Conditions(wind_mph=10.0, gust_mph=70.0, rain_in_hr=0.0, snow_in_hr=0.0), LIGHT_LOAD
    )
    assert assessment.level is RiskLevel.LOW
