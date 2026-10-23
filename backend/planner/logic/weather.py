"""Turn an Open-Meteo hourly payload into the reading at a truck's ETA.

Wind on a timestamp is the instantaneous wind at that time. Rain and snow on
a timestamp are the totals for the preceding hour. For an ETA of 14:20 the
wind comes from 14:00, and the rain and snow come from 15:00 (the sum from
14:00 to 15:00). If that next hour is missing, rain and snow fall back to
the ETA's own hour.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from planner.logic.units import cm_to_inches, kmh_to_mph, mm_to_inches

HOUR = 3600


@dataclass(frozen=True)
class HourReading:
    wind_mph: float
    rain_in_hr: float
    snow_in_hr: float
    missing: bool


def floor_hour(moment: datetime) -> int:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    unix = int(moment.timestamp())
    return unix - (unix % HOUR)


def parse_hourly_payload(payload: dict) -> dict[int, HourReading]:
    units = payload.get("hourly_units") or {}
    if units.get("wind_speed_10m") not in (None, "km/h"):
        raise ValueError(f"unexpected wind unit: {units.get('wind_speed_10m')}")
    if units.get("rain") not in (None, "mm"):
        raise ValueError(f"unexpected rain unit: {units.get('rain')}")
    if units.get("snowfall") not in (None, "cm"):
        raise ValueError(f"unexpected snowfall unit: {units.get('snowfall')}")
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    winds = hourly.get("wind_speed_10m") or []
    rains = hourly.get("rain") or []
    showers = hourly.get("showers") or []
    snows = hourly.get("snowfall") or []
    parsed: dict[int, HourReading] = {}
    for index, stamp in enumerate(times):
        wind_raw = _at(winds, index)
        rain_raw = _at(rains, index)
        shower_raw = _at(showers, index)
        snow_raw = _at(snows, index)
        missing = wind_raw is None or rain_raw is None or snow_raw is None
        rain_mm = (rain_raw or 0) + (shower_raw or 0)
        parsed[int(stamp)] = HourReading(
            wind_mph=kmh_to_mph(wind_raw or 0),
            rain_in_hr=mm_to_inches(rain_mm),
            snow_in_hr=cm_to_inches(snow_raw or 0),
            missing=missing,
        )
    return parsed


def select_reading(hours: dict[int, HourReading], eta: datetime) -> HourReading:
    if not hours:
        return HourReading(0.0, 0.0, 0.0, missing=True)
    wind_hour = floor_hour(eta)
    wind = _nearest(hours, wind_hour)
    precip = _nearest(hours, wind_hour + HOUR)
    if precip is None:
        precip = wind
    if wind is None:
        return HourReading(0.0, 0.0, 0.0, missing=True)
    rain_source = precip if precip is not None else wind
    return HourReading(
        wind_mph=wind.wind_mph,
        rain_in_hr=rain_source.rain_in_hr,
        snow_in_hr=rain_source.snow_in_hr,
        missing=wind.missing or rain_source.missing,
    )


def _at(values: list, index: int):
    if index >= len(values):
        return None
    return values[index]


def _nearest(hours: dict[int, HourReading], target: int) -> HourReading | None:
    if target in hours:
        return hours[target]
    if not hours:
        return None
    nearest = min(hours, key=lambda stamp: abs(stamp - target))
    if abs(nearest - target) > 2 * HOUR:
        return None
    reading = hours[nearest]
    return HourReading(reading.wind_mph, reading.rain_in_hr, reading.snow_in_hr, missing=True)
