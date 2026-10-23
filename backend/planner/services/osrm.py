"""Driving routes from the public OSRM server.

OSRM's `alternatives` flag often returns only two routes. When that happens
we ask again with a via point offset to the side of the fastest route. The
via route is kept only if it stays at least 8 miles away from the routes we
already have. See planner.logic.routing.
"""

from __future__ import annotations

from planner.logic.geo import PathPoint, path_from_coordinates
from planner.logic.roads import dominant_road
from planner.logic.routing import is_distinct, via_points
from planner.logic.sampling import path_from_steps, scale_path
from planner.services.errors import UpstreamError
from planner.services.http import get_json

OSRM_URL = "https://router.project-osrm.org"
MAX_VIA_ATTEMPTS = 6


def get_three_routes(origin: dict, destination: dict) -> tuple[list[dict], dict, list[list[PathPoint]]]:
    raw = fetch_routes([origin, destination], alternatives=True)
    if not raw:
        raise UpstreamError("No driving route was found between those points.")

    kept: list[dict] = []
    paths: list[list[PathPoint]] = []
    for route in raw:
        path = route_path(route)
        if any(not is_distinct(path, existing) for existing in paths):
            continue
        route["source"] = "osrm"
        route["via"] = None
        kept.append(route)
        paths.append(path)
        if len(kept) == 3:
            break

    osrm_kept = len(kept)
    via_count = 0
    backups: list[tuple[dict, list[PathPoint]]] = []
    if len(kept) < 3:
        primary_distance = kept[0]["distance_miles"]
        attempts = 0
        for lat, lon in via_points(paths[0]):
            if attempts >= MAX_VIA_ATTEMPTS or len(kept) >= 3:
                break
            attempts += 1
            via = {"lat": lat, "lon": lon}
            try:
                routed = fetch_routes([origin, via, destination], alternatives=False)
            except UpstreamError:
                continue
            if not routed:
                continue
            route = routed[0]
            path = route_path(route)
            if any(not is_distinct(path, existing) for existing in paths):
                continue
            route["source"] = "via"
            route["via"] = {"lat": round(lat, 4), "lon": round(lon, 4)}
            if route["distance_miles"] <= primary_distance * 1.85:
                kept.append(route)
                paths.append(path)
                via_count += 1
            else:
                backups.append((route, path))
        if len(kept) < 3:
            backups.sort(key=lambda item: item[0]["distance_miles"])
            for route, path in backups:
                if any(not is_distinct(path, existing) for existing in paths):
                    continue
                kept.append(route)
                paths.append(path)
                via_count += 1
                if len(kept) == 3:
                    break

    chosen = kept[:3]
    chosen_paths = paths[:3]
    for index, route in enumerate(chosen):
        route["id"] = "ABC"[index]
        route["name"] = f"Route {route['id']}"
    meta = {
        "provider": "OSRM",
        "osrm_routes": osrm_kept,
        "via_routes": via_count,
        "note": _note(osrm_kept, via_count, len(chosen)),
    }
    return chosen, meta, chosen_paths


def fetch_routes(places: list[dict], alternatives: bool) -> list[dict]:
    coords = ";".join(f"{place['lon']:.6f},{place['lat']:.6f}" for place in places)
    payload = get_json(
        f"{OSRM_URL}/route/v1/driving/{coords}",
        params={
            "alternatives": "true" if alternatives else "false",
            "overview": "full",
            "geometries": "geojson",
            "steps": "true",
        },
        timeout=40,
        service="routing service",
    )
    if not isinstance(payload, dict):
        raise UpstreamError("The routing service returned an unexpected response.")
    if payload.get("code") != "Ok":
        raise UpstreamError(payload.get("message") or "No driving route was found between those points.")
    return [_parse_route(raw) for raw in payload.get("routes") or []]


def route_path(route: dict) -> list[PathPoint]:
    try:
        path = path_from_steps(route.get("steps") or [])
    except ValueError:
        path = []
    if len(path) < 2:
        path = path_from_coordinates(route["geometry"], route["duration_seconds"])
    return scale_path(path, route["distance_miles"], route["duration_seconds"])


def _parse_route(raw: dict) -> dict:
    steps = []
    for leg in raw.get("legs") or []:
        for step in leg.get("steps") or []:
            steps.append(
                {
                    "distance_meters": step.get("distance") or 0,
                    "duration_seconds": step.get("duration") or 0,
                    "coordinates": (step.get("geometry") or {}).get("coordinates") or [],
                    "name": step.get("name") or "",
                    "ref": step.get("ref") or "",
                }
            )
    geometry = [(lat, lon) for lon, lat in (raw.get("geometry") or {}).get("coordinates") or []]
    return {
        "distance_miles": (raw.get("distance") or 0) / 1609.344,
        "duration_seconds": raw.get("duration") or 0,
        "geometry": geometry,
        "steps": steps,
        "via_label": dominant_road(steps),
    }


def _note(osrm_routes: int, via_routes: int, returned: int) -> str:
    if via_routes == 0 and returned >= 3:
        return "All three routes are alternatives returned by OSRM."
    if via_routes == 0:
        route_word = "route" if returned == 1 else "routes"
        return (
            f"OSRM returned {returned} distinct {route_word}. "
            "A via point did not produce another route that stays off those roads."
        )
    via_word = "route was" if via_routes == 1 else "routes were"
    return (
        f"OSRM returned {osrm_routes} distinct "
        f"{'route' if osrm_routes == 1 else 'routes'}. "
        f"{via_routes} more {via_word} built by routing through a point offset "
        "to the side of the fastest route, so the corridor is actually different. "
        "The public OSRM server often does not return three alternatives on its own."
    )
