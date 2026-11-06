import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from planner.domain.geo import lerp
from planner.domain.risk import Conditions

HOUR = timedelta(hours=1)


class ForecastGapError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class HourlySeries:
    start: datetime
    wind_mph: Sequence[float]
    gust_mph: Sequence[float]
    rain_in_hr: Sequence[float]
    snow_in_hr: Sequence[float]

    def at(self, moment: datetime) -> Conditions:
        offset = (moment - self.start) / HOUR
        floor = math.floor(offset)
        ceil = math.ceil(offset)
        if floor < 0 or ceil >= len(self.wind_mph):
            raise ForecastGapError(f"No forecast covers {moment.isoformat()}")
        fraction = offset - floor
        return Conditions(
            wind_mph=round(lerp(self.wind_mph[floor], self.wind_mph[ceil], fraction), 1),
            gust_mph=round(lerp(self.gust_mph[floor], self.gust_mph[ceil], fraction), 1),
            rain_in_hr=self.rain_in_hr[ceil],
            snow_in_hr=self.snow_in_hr[ceil],
        )


def floor_hour(moment: datetime) -> datetime:
    return moment.replace(minute=0, second=0, microsecond=0)


def ceil_hour(moment: datetime) -> datetime:
    floored = floor_hour(moment)
    return floored if floored == moment else floored + HOUR
