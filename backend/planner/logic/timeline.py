"""Shift departure across the forecast that was already fetched.

Hour 0 is the departure that was typed. Hour N means leaving N hours later.
Arrival at each checkpoint moves by those same hours, and the weather is the
reading stored for that later hour. The slider does not call the network.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from planner.logic.recommend import explain_recommendation, rank_routes, round_half_up
from planner.logic.risk import classify_checkpoint
from planner.logic.sampling import summarize_checkpoints


def project_timeline(
    routes: list[dict],
    departure: datetime,
    load_lb: float,
    hours: int = 49,
) -> tuple[list[dict], list[dict]]:
    frames = []
    hour0: list[dict] = []
    for offset in range(hours):
        ranked = _rank_offset(routes, departure, load_lb, offset)
        if offset == 0:
            hour0 = ranked
        frames.append(
            {
                "offset": offset,
                "departure": _iso(departure + timedelta(hours=offset)),
                "recommendation": {
                    "route_id": ranked[0]["id"] if ranked else None,
                    "summary": explain_recommendation(ranked),
                },
                "routes": [_frame_route(item) for item in ranked],
            }
        )
    return hour0, frames


def _rank_offset(routes: list[dict], departure: datetime, load_lb: float, offset: int) -> list[dict]:
    shifted = departure + timedelta(hours=offset)
    prepared = []
    for route in routes:
        checkpoints = []
        for sample in route["samples"]:
            reading = sample["readings"][offset]
            risk = classify_checkpoint(
                reading["wind_mph"],
                reading["rain_in_hr"],
                reading["snow_in_hr"],
                load_lb,
            )
            eta = shifted + timedelta(seconds=float(sample["elapsed_seconds"]))
            checkpoints.append(
                {
                    "lat": sample["lat"],
                    "lon": sample["lon"],
                    "distance_miles": sample["distance_miles"],
                    "eta": _iso(eta),
                    "wind_mph": round(float(reading["wind_mph"]), 1),
                    "rain_in_hr": round(float(reading["rain_in_hr"]), 3),
                    "snow_in_hr": round(float(reading["snow_in_hr"]), 3),
                    "missing_weather": bool(reading["missing"]),
                    **risk,
                }
            )
        summary = summarize_checkpoints(checkpoints)
        prepared.append(
            {
                "id": route["id"],
                "name": route["name"],
                "source": route["source"],
                "via_label": route.get("via_label"),
                "via": route.get("via"),
                "distance_miles": route["distance_miles"],
                "duration_seconds": route["duration_seconds"],
                "geometry": route["geometry"],
                "checkpoints": checkpoints,
                "no_travel_miles": summary["miles"]["no_travel"],
                "severe_miles": summary["miles"]["severe"],
                "high_miles": summary["miles"]["high"],
                "average_risk": summary["average_risk"],
                "miles": summary["miles"],
            }
        )
    return _finish(prepared)


def _finish(prepared: list[dict]) -> list[dict]:
    ranked = rank_routes(prepared)
    for item in ranked:
        item["distance_miles"] = round_half_up(item["distance_miles"], 1)
        raw_miles = item["miles"]
        item["miles"] = {
            "no_travel": item["no_travel_miles"],
            "severe": item["severe_miles"],
            "high": item["high_miles"],
            "moderate": round_half_up(raw_miles["moderate"], 1),
            "low": round_half_up(raw_miles["low"], 1),
        }
        item["average_risk"] = round_half_up(item["average_risk"], 2)
        for checkpoint in item["checkpoints"]:
            checkpoint["distance_miles"] = round(checkpoint["distance_miles"], 2)
    return ranked


def _frame_route(item: dict) -> dict:
    return {
        "id": item["id"],
        "miles": item["miles"],
        "average_risk": item["average_risk"],
        "rank": item["rank"],
        "recommended": item["recommended"],
        "checkpoints": [
            {
                "eta": checkpoint["eta"],
                "wind_mph": checkpoint["wind_mph"],
                "rain_in_hr": checkpoint["rain_in_hr"],
                "snow_in_hr": checkpoint["snow_in_hr"],
                "wind_risk": checkpoint["wind_risk"],
                "wind_risk_after_load": checkpoint["wind_risk_after_load"],
                "rain_risk": checkpoint["rain_risk"],
                "snow_risk": checkpoint["snow_risk"],
                "risk": checkpoint["risk"],
                "load_adjusted": checkpoint["load_adjusted"],
                "load_note": checkpoint["load_note"],
                "missing_weather": checkpoint["missing_weather"],
                "distance_miles": checkpoint["distance_miles"],
            }
            for checkpoint in item["checkpoints"]
        ],
    }


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
