"""Check the trip form before any routing or weather calls."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from planner.logic.geo import haversine_miles

MAX_LOAD_LB = 250_000


class ValidationError(Exception):
    pass


def parse_plan_request(data, now: datetime | None = None) -> dict:
    if not isinstance(data, dict):
        raise ValidationError("The request body has to be a JSON object.")
    origin = _place(data.get("origin"), "origin")
    destination = _place(data.get("destination"), "destination")
    if haversine_miles(origin["lat"], origin["lon"], destination["lat"], destination["lon"]) < 1:
        raise ValidationError("Pick an origin and a destination at least 1 mile apart.")
    departure = _departure(data.get("departure"), now or datetime.now(timezone.utc))
    load = _load(data.get("load_weight_lb"))
    interval = _interval(data.get("sample_miles", 25))
    return {
        "origin": origin,
        "destination": destination,
        "departure": departure,
        "load_weight_lb": load,
        "sample_miles": interval,
    }


def _place(value, field: str) -> dict:
    if not isinstance(value, dict):
        raise ValidationError(f"Enter an {field}.")
    try:
        lat = float(value["lat"])
        lon = float(value["lon"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValidationError(f"The {field} needs a latitude and a longitude.") from exc
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValidationError(f"The {field} coordinates are out of range.")
    label = str(value.get("label") or "").strip()
    if not label:
        label = f"{lat:.4f}, {lon:.4f}"
    return {"label": label[:180], "lat": lat, "lon": lon}


def _departure(value, now: datetime) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("Choose a departure date and time.")
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValidationError("The departure time could not be read.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    parsed = parsed.astimezone(timezone.utc)
    if parsed < now - timedelta(days=2):
        raise ValidationError("That departure is too far in the past. Choose a time within the last 2 days.")
    if parsed > now + timedelta(days=7):
        raise ValidationError("That departure is too far ahead. Choose a time within the next 7 days.")
    return parsed


def _load(value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError("Enter the load weight in pounds.")
    load = float(value)
    if load < 0:
        raise ValidationError("Load weight cannot be negative.")
    if load > MAX_LOAD_LB:
        raise ValidationError("Load weight has to be 250,000 lb or less.")
    return load


def _interval(value) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError("Sample interval must be 10, 25, or 50 miles.")
    if float(value) not in (10.0, 25.0, 50.0):
        raise ValidationError("Sample interval must be 10, 25, or 50 miles.")
    return int(value)
