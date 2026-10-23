"""Place search. Photon first, Nominatim if Photon is empty or down.

Both are OpenStreetMap geocoders and need no API key. Requests send a
User-Agent, the browser debounces typing, and identical queries are cached
for an hour. Results are biased toward the middle of the United States.
"""

from __future__ import annotations

import threading
import time

from planner.services.errors import UpstreamError
from planner.services.http import get_json

PHOTON_URL = "https://photon.komoot.io/api/"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
PLACE_VALUES = {
    "city",
    "town",
    "village",
    "hamlet",
    "suburb",
    "locality",
    "county",
    "state",
    "municipality",
    "administrative",
}

_lock = threading.Lock()
_cache: dict[str, tuple[float, list[dict]]] = {}
CACHE_TTL = 60 * 60


def search_places(query: str) -> list[dict]:
    pasted = _parse_coords(query)
    if pasted:
        return [pasted]
    key = " ".join(query.lower().split())
    cached = _cache_get(key)
    if cached is not None:
        return cached
    try:
        results = _from_photon(query)
    except UpstreamError:
        results = []
    if not results:
        results = _from_nominatim(query)
    _cache_set(key, results)
    return results


def _from_photon(query: str) -> list[dict]:
    payload = get_json(
        PHOTON_URL,
        params={"q": query, "limit": 8, "lat": 39.8, "lon": -98.6},
        timeout=12,
        service="place search",
    )
    features = payload.get("features") if isinstance(payload, dict) else None
    if not features:
        return []
    query_has_digit = any(character.isdigit() for character in query)
    ranked: list[tuple[int, dict]] = []
    for feature in features:
        props = feature.get("properties") or {}
        coords = (feature.get("geometry") or {}).get("coordinates") or []
        if len(coords) < 2:
            continue
        lon, lat = coords[0], coords[1]
        label = _label(props)
        if not label:
            continue
        value = (props.get("osm_value") or "").lower()
        osm_key = (props.get("osm_key") or "").lower()
        is_place = osm_key in {"place", "boundary"} or value in PLACE_VALUES
        if not query_has_digit and not is_place and props.get("type") == "house":
            continue
        ranked.append((0 if is_place else 1, {"label": label, "lat": lat, "lon": lon}))
    if not ranked and not query_has_digit:
        return _from_photon_loose(features)
    ranked.sort(key=lambda item: item[0])
    return _dedupe([place for _rank, place in ranked])[:5]


def _from_photon_loose(features: list) -> list[dict]:
    places = []
    for feature in features:
        props = feature.get("properties") or {}
        coords = (feature.get("geometry") or {}).get("coordinates") or []
        if len(coords) < 2:
            continue
        label = _label(props)
        if label:
            places.append({"label": label, "lat": coords[1], "lon": coords[0]})
    return _dedupe(places)[:5]


def _from_nominatim(query: str) -> list[dict]:
    payload = get_json(
        NOMINATIM_URL,
        params={
            "q": query,
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": 5,
            "countrycodes": "us",
        },
        timeout=12,
        service="place search",
    )
    if not isinstance(payload, list):
        return []
    places = []
    for item in payload:
        try:
            lat = float(item["lat"])
            lon = float(item["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        label = (item.get("display_name") or "").strip()
        if label:
            places.append({"label": label, "lat": lat, "lon": lon})
    return _dedupe(places)[:5]


def _label(props: dict) -> str:
    house = props.get("housenumber")
    street = props.get("street")
    name = props.get("name")
    city = props.get("city") or props.get("county")
    state = props.get("state")
    country = props.get("country")
    if house and street:
        line = f"{house} {street}"
        if name and name not in line:
            line = f"{name}, {line}"
    elif name:
        line = name
    else:
        line = street
    parts = []
    for part in (line, city, state, country):
        if not part:
            continue
        text = str(part).strip()
        if parts and parts[-1].lower() == text.lower():
            continue
        parts.append(text)
    return ", ".join(parts)


def _dedupe(places: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for place in places:
        key = place["label"].lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(place)
    return unique


def _parse_coords(query: str) -> dict | None:
    text = query.replace(" ", "")
    if "," not in text:
        return None
    left, right = text.split(",", 1)
    try:
        lat = float(left)
        lon = float(right)
    except ValueError:
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return {"label": f"{lat:.4f}, {lon:.4f}", "lat": lat, "lon": lon}


def _cache_get(key: str):
    with _lock:
        hit = _cache.get(key)
        if not hit:
            return None
        saved, value = hit
        if time.time() - saved > CACHE_TTL:
            _cache.pop(key, None)
            return None
        return value


def _cache_set(key: str, value: list[dict]) -> None:
    with _lock:
        _cache[key] = (time.time(), value)
