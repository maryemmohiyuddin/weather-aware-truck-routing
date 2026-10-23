"""Hourly forecast from Open-Meteo, batched and cached.

Coordinates are rounded to 0.01 degrees (about 0.7 miles) before the request.
Nearby checkpoints share one grid cell, which matches the resolution of the
forecast model and keeps the payload small. Uncached cells go out a few
batches at a time. Results stay in this process for 20 minutes. The slider
does not come back here: one response already holds hours 0 through 48.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import threading
import time

from planner.logic.weather import HourReading, parse_hourly_payload, select_reading
from planner.services.errors import UpstreamError
from planner.services.http import get_json

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
BATCH_SIZE = 40
WORKERS = 4
CACHE_TTL = 20 * 60
# Short enough that a hung forecast plus one retry stays inside the Hobby function.
REQUEST_TIMEOUT = 20

_lock = threading.Lock()
_cache: dict[tuple, tuple[float, dict[int, HourReading]]] = {}


class WeatherBook:
    def __init__(self, table: dict[tuple[float, float], dict[int, HourReading]]):
        self.table = table

    def reading(self, lat: float, lon: float, moment: datetime) -> HourReading:
        hours = self.table.get((round(lat, 2), round(lon, 2)))
        if not hours:
            return HourReading(0.0, 0.0, 0.0, missing=True)
        return select_reading(hours, moment)


def fetch_weather(coords: list[tuple[float, float]], start_unix: int, end_unix: int) -> WeatherBook:
    start_label = _hour_label(start_unix)
    end_label = _hour_label(end_unix)
    keys: list[tuple[float, float]] = []
    seen: set[tuple[float, float]] = set()
    for lat, lon in coords:
        key = (round(float(lat), 2), round(float(lon), 2))
        if key in seen:
            continue
        seen.add(key)
        keys.append(key)

    missing = [key for key in keys if _cache_get(key, start_label, end_label) is None]
    batches = list(_chunks(missing, BATCH_SIZE))
    if batches:
        workers = min(WORKERS, len(batches))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [
                pool.submit(_fetch_batch, batch, start_label, end_label) for batch in batches
            ]
            for future in futures:
                future.result()

    table = {}
    for key in keys:
        hours = _cache_get(key, start_label, end_label)
        if hours is None:
            raise UpstreamError("The weather service did not return that location.")
        table[key] = hours
    if table and not _covers(next(iter(table.values())), start_unix):
        raise UpstreamError(
            "The forecast does not cover that departure. Choose a time within the next 7 days."
        )
    return WeatherBook(table)


def _fetch_batch(batch, start_label, end_label):
    payload = get_json(
        FORECAST_URL,
        params={
            "latitude": ",".join(str(lat) for lat, _lon in batch),
            "longitude": ",".join(str(lon) for _lat, lon in batch),
            "hourly": "wind_speed_10m,rain,showers,snowfall",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
            "timeformat": "unixtime",
            "timezone": "UTC",
            "start_hour": start_label,
            "end_hour": end_label,
        },
        timeout=REQUEST_TIMEOUT,
        service="weather service",
    )
    if isinstance(payload, dict) and payload.get("error"):
        reason = payload.get("reason") or "The weather service rejected the forecast request."
        raise UpstreamError(_friendly_weather_error(str(reason)))
    items = payload if isinstance(payload, list) else [payload]
    if len(items) != len(batch):
        raise UpstreamError("The weather service returned an unexpected number of locations.")
    parsed_rows = []
    for item in items:
        if not isinstance(item, dict):
            raise UpstreamError("The weather service returned an unexpected forecast.")
        try:
            parsed_rows.append(parse_hourly_payload(item))
        except ValueError as exc:
            raise UpstreamError("The weather service changed its units. Forecasts were not used.") from exc
    for key, parsed in zip(batch, parsed_rows):
        _cache_set(key, start_label, end_label, parsed)


def _covers(hours: dict[int, HourReading], start_unix: int) -> bool:
    if not hours:
        return False
    target = start_unix - (start_unix % 3600)
    return any(abs(stamp - target) <= 3600 for stamp in hours)


def _hour_label(unix: int) -> str:
    floored = unix - (unix % 3600)
    return datetime.fromtimestamp(floored, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M")


def _friendly_weather_error(reason: str) -> str:
    if "out of allowed range" in reason or "start_hour" in reason:
        return "The forecast does not cover that departure. Choose a time within the next 7 days."
    return "The weather service could not build that forecast. Try again in a moment."


def _cache_get(key, start_label, end_label):
    cache_key = (key, start_label, end_label)
    with _lock:
        hit = _cache.get(cache_key)
        if not hit:
            return None
        saved, value = hit
        if time.time() - saved > CACHE_TTL:
            _cache.pop(cache_key, None)
            return None
        return value


def _cache_set(key, start_label, end_label, value):
    cache_key = (key, start_label, end_label)
    with _lock:
        _cache[cache_key] = (time.time(), value)
        if len(_cache) > 4000:
            oldest = sorted(_cache, key=lambda item: _cache[item][0])[:500]
            for item in oldest:
                _cache.pop(item, None)


def _chunks(items: list, size: int):
    for index in range(0, len(items), size):
        yield items[index : index + size]
