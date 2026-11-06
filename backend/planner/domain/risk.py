from bisect import bisect_right
from dataclasses import dataclass
from enum import IntEnum


class RiskLevel(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4


WIND_BAND_FLOORS_MPH = (25.0, 35.0, 45.0, 55.0)
RAIN_BAND_FLOORS_IN_HR = (0.10, 0.25, 0.50)
RAIN_NO_TRAVEL_ABOVE_IN_HR = 1.00
SNOW_BAND_FLOORS_IN_HR = (0.5, 1.0, 2.0)
SNOW_NO_TRAVEL_ABOVE_IN_HR = 3.0

HIGH_WIND_LOAD_LIMIT_LB = 40_000
SEVERE_WIND_LOAD_LIMIT_LB = 30_000


@dataclass(frozen=True, slots=True)
class Conditions:
    wind_mph: float
    gust_mph: float
    rain_in_hr: float
    snow_in_hr: float


@dataclass(frozen=True, slots=True)
class Assessment:
    level: RiskLevel
    wind: RiskLevel
    rain: RiskLevel
    snow: RiskLevel
    load_adjusted: bool


def _band(value: float, floors: tuple[float, ...]) -> RiskLevel:
    return RiskLevel(bisect_right(floors, value))


def classify_wind(wind_mph: float, load_lb: int) -> tuple[RiskLevel, bool]:
    level = _band(wind_mph, WIND_BAND_FLOORS_MPH)
    if level is RiskLevel.SEVERE and load_lb > SEVERE_WIND_LOAD_LIMIT_LB:
        return RiskLevel.NO_TRAVEL, True
    if level is RiskLevel.HIGH and load_lb > HIGH_WIND_LOAD_LIMIT_LB:
        return RiskLevel.SEVERE, True
    return level, False


def classify_rain(rain_in_hr: float) -> RiskLevel:
    if rain_in_hr > RAIN_NO_TRAVEL_ABOVE_IN_HR:
        return RiskLevel.NO_TRAVEL
    return _band(rain_in_hr, RAIN_BAND_FLOORS_IN_HR)


def classify_snow(snow_in_hr: float) -> RiskLevel:
    if snow_in_hr > SNOW_NO_TRAVEL_ABOVE_IN_HR:
        return RiskLevel.NO_TRAVEL
    return _band(snow_in_hr, SNOW_BAND_FLOORS_IN_HR)


def assess(conditions: Conditions, load_lb: int) -> Assessment:
    wind, load_adjusted = classify_wind(conditions.wind_mph, load_lb)
    rain = classify_rain(conditions.rain_in_hr)
    snow = classify_snow(conditions.snow_in_hr)
    return Assessment(
        level=max(wind, rain, snow),
        wind=wind,
        rain=rain,
        snow=snow,
        load_adjusted=load_adjusted,
    )
