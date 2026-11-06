from datetime import UTC, datetime, timedelta
from functools import partial
from typing import Annotated, Literal

from django.utils import timezone
from ninja import Field, Schema
from pydantic import AwareDatetime, PlainSerializer, field_validator

from planner.domain.assessment import RouteAssessment, Segment
from planner.domain.geo import METERS_PER_MILE
from planner.domain.hours_of_service import StopKind
from planner.domain.recommendation import DecidingFactor
from planner.domain.risk import RiskLevel
from planner.domain.sampling import Stop

MAX_LOAD_LB = 80_000
PAST_DEPARTURE_TOLERANCE = timedelta(minutes=15)
MAX_DEPARTURE_AHEAD = timedelta(days=14)

Rounded1 = Annotated[float, PlainSerializer(partial(round, ndigits=1))]
Rounded2 = Annotated[float, PlainSerializer(partial(round, ndigits=2))]
Rounded3 = Annotated[float, PlainSerializer(partial(round, ndigits=3))]
Coordinate = Annotated[float, PlainSerializer(partial(round, ndigits=5))]
Level = Annotated[int, Field(ge=RiskLevel.LOW, le=RiskLevel.NO_TRAVEL)]


class Error(Schema):
    detail: str


class Point(Schema):
    lat: Coordinate = Field(ge=-90, le=90)
    lon: Coordinate = Field(ge=-180, le=180)


class TripIn(Schema):
    origin: Point
    destination: Point
    departure: AwareDatetime
    load_lb: int = Field(ge=1, le=MAX_LOAD_LB)
    interval_mi: Literal[10, 25, 50]
    rest_breaks: bool = True

    @field_validator("departure")
    @classmethod
    def departure_in_planning_window(cls, value: datetime) -> datetime:
        now = timezone.now()
        if value < now - PAST_DEPARTURE_TOLERANCE:
            raise ValueError("Departure time cannot be in the past")
        if value > now + MAX_DEPARTURE_AHEAD:
            raise ValueError("Departure time must be within the next 14 days")
        return value.astimezone(UTC)


class PlaceOut(Schema):
    label: str
    position: Point


class ConditionsOut(Schema):
    wind_mph: Rounded1
    gust_mph: Rounded1
    rain_in_hr: Rounded3
    snow_in_hr: Rounded3


class AssessmentOut(Schema):
    level: Level
    wind: Level
    rain: Level
    snow: Level
    load_adjusted: bool


class CheckpointOut(Schema):
    mile: Rounded2
    position: Point
    eta: datetime
    conditions: ConditionsOut
    risk: AssessmentOut


class SegmentOut(Schema):
    level: Level
    start_mile: Rounded2
    end_mile: Rounded2
    coordinates: list[tuple[Coordinate, Coordinate]]

    @staticmethod
    def resolve_start_mile(segment: Segment) -> float:
        return segment.start_m / METERS_PER_MILE

    @staticmethod
    def resolve_end_mile(segment: Segment) -> float:
        return segment.end_m / METERS_PER_MILE

    @staticmethod
    def resolve_coordinates(segment: Segment) -> list[tuple[float, float]]:
        return [(point.lon, point.lat) for point in segment.path]


class StopOut(Schema):
    kind: StopKind
    mile: Rounded2
    position: Point
    start: datetime
    end: datetime

    @staticmethod
    def resolve_mile(stop: Stop) -> float:
        return stop.distance_m / METERS_PER_MILE


class SummaryOut(Schema):
    low_mi: Rounded1
    moderate_mi: Rounded1
    high_mi: Rounded1
    severe_mi: Rounded1
    no_travel_mi: Rounded1
    average_risk: Rounded2


class RouteOut(Schema):
    distance_mi: Rounded1
    driving_s: int
    duration_s: int
    departure: datetime
    arrival: datetime
    summary: SummaryOut
    checkpoints: list[CheckpointOut]
    segments: list[SegmentOut]
    stops: list[StopOut]

    @staticmethod
    def resolve_distance_mi(route: RouteAssessment) -> float:
        return route.path.length_m / METERS_PER_MILE

    @staticmethod
    def resolve_driving_s(route: RouteAssessment) -> int:
        return round(route.path.total_driving_s)

    @staticmethod
    def resolve_duration_s(route: RouteAssessment) -> int:
        return round(route.duration_s)

    @staticmethod
    def resolve_summary(route: RouteAssessment) -> SummaryOut:
        miles = route.summary.miles
        return SummaryOut(
            low_mi=miles(RiskLevel.LOW),
            moderate_mi=miles(RiskLevel.MODERATE),
            high_mi=miles(RiskLevel.HIGH),
            severe_mi=miles(RiskLevel.SEVERE),
            no_travel_mi=miles(RiskLevel.NO_TRAVEL),
            average_risk=route.summary.average_risk,
        )


class RecommendationOut(Schema):
    index: int
    deciding_factor: DecidingFactor
    runner_up_index: int | None


class HeatmapOut(Schema):
    cell_deg: float
    cells: list[Point]
    hours: list[datetime]
    risk: list[list[Level]]
    wind_mph: list[list[float]]
    rain_in_hr: list[list[float]]
    snow_in_hr: list[list[float]]


class CheckOut(Schema):
    key: str
    title: str
    passed: bool
    detail: str


class VerificationOut(Schema):
    passed: bool
    checks: list[CheckOut]


class TripPlanOut(Schema):
    routes: list[RouteOut]
    recommendation: RecommendationOut
    heatmap: HeatmapOut
    verification: VerificationOut
