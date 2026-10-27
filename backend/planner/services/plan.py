"""Build the trip: three routes, checkpoint weather, risk, and the 48-hour grid."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math

from planner.logic.geo import downsample
from planner.logic.recommend import explain_recommendation
from planner.logic.risk import weather_intensity
from planner.logic.sampling import corridor_points, sample_path
from planner.logic.timeline import project_timeline
from planner.logic.weather import floor_hour
from planner.services.open_meteo import fetch_weather
from planner.services.osrm import get_three_routes

RISK_SCALE = {"low": 1, "moderate": 2, "high": 3, "severe": 4, "no_travel": 5}


def build_plan(plan_request: dict) -> dict:
    origin = plan_request["origin"]
    destination = plan_request["destination"]
    departure: datetime = plan_request["departure"]
    load_lb = plan_request["load_weight_lb"]
    interval = plan_request["sample_miles"]

    routes, routing, paths = get_three_routes(origin, destination)
    samples_by_route = [sample_path(path, interval) for path in paths]
    max_elapsed = max((samples[-1].seconds for samples in samples_by_route if samples), default=0)
    base = floor_hour(departure)
    # Cover a departure up to 48 hours later, plus the drive, plus the next rain hour.
    end = base + 48 * 3600 + int(math.ceil(max_elapsed)) + 3600

    corridor = corridor_points(paths)
    coords = [(point.lat, point.lon) for samples in samples_by_route for point in samples]
    coords.extend(corridor)
    book = fetch_weather(coords, base, end)

    shells = []
    for route, path, samples in zip(routes, paths, samples_by_route):
        rows = []
        for sample in samples:
            readings = []
            for offset in range(49):
                eta = departure + timedelta(hours=offset, seconds=sample.seconds)
                reading = book.reading(sample.lat, sample.lon, eta)
                readings.append(
                    {
                        "wind_mph": reading.wind_mph,
                        "rain_in_hr": reading.rain_in_hr,
                        "snow_in_hr": reading.snow_in_hr,
                        "missing": reading.missing,
                    }
                )
            rows.append(
                {
                    "lat": round(sample.lat, 5),
                    "lon": round(sample.lon, 5),
                    "distance_miles": sample.miles,
                    "elapsed_seconds": sample.seconds,
                    "readings": readings,
                }
            )
        shells.append(
            {
                "id": route["id"],
                "name": route["name"],
                "source": route["source"],
                "via_label": route.get("via_label"),
                "via": route.get("via"),
                "distance_miles": route["distance_miles"],
                "duration_seconds": route["duration_seconds"],
                "geometry": downsample([(point.lat, point.lon) for point in path], 700),
                "samples": rows,
            }
        )

    ranked, timeline = project_timeline(shells, departure, load_lb, 49)

    heatmap = []
    for lat, lon in corridor:
        intensity = []
        for hour in range(49):
            moment = datetime.fromtimestamp(base + hour * 3600, tz=timezone.utc)
            reading = book.reading(lat, lon, moment)
            intensity.append(
                round(weather_intensity(reading.wind_mph, reading.rain_in_hr, reading.snow_in_hr, load_lb), 3)
            )
        heatmap.append({"lat": round(lat, 4), "lon": round(lon, 4), "intensity": intensity})

    return {
        "origin": origin,
        "destination": destination,
        "departure": _iso(departure),
        "load_weight_lb": load_lb,
        "sample_miles": interval,
        "routing": routing,
        "recommendation": {
            "route_id": ranked[0]["id"] if ranked else None,
            "summary": explain_recommendation(ranked),
        },
        "routes": ranked,
        "timeline": timeline,
        "heatmap": {
            "base_time": _iso(datetime.fromtimestamp(base, tz=timezone.utc)),
            "hours": 49,
            "points": heatmap,
        },
        "risk_scale": RISK_SCALE,
    }


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
