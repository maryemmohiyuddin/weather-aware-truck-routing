"""Via points used when the router returns fewer than three distinct routes.

The offset starts from the fastest route itself, not from the straight line
between the cities, so the point is beside a road the truck would actually
be on. OSRM then snaps it to the nearest drivable road. A candidate is kept
only when it stays at least 8 miles away from the routes already chosen,
averaged along the two paths.
"""

from __future__ import annotations

from planner.logic.geo import PathPoint, bearing_degrees, destination_point, mean_separation_miles, point_at_distance

DISTINCT_MILES = 8.0


def is_distinct(left: list[PathPoint], right: list[PathPoint], threshold: float = DISTINCT_MILES) -> bool:
    return mean_separation_miles(left, right) >= threshold


def via_points(path: list[PathPoint]) -> list[tuple[float, float]]:
    if not path or path[-1].miles < 20:
        return []
    total = path[-1].miles
    candidates: list[tuple[float, float]] = []
    seen: set[tuple[float, float]] = set()
    for fraction in (0.5, 0.33, 0.66):
        mile = total * fraction
        here = point_at_distance(path, mile)
        ahead = point_at_distance(path, min(total, mile + max(1.0, total * 0.01)))
        if abs(ahead.lat - here.lat) < 1e-7 and abs(ahead.lon - here.lon) < 1e-7:
            continue
        bearing = bearing_degrees(here.lat, here.lon, ahead.lat, ahead.lon)
        for offset in (30, 55, 80):
            distance = min(float(offset), total * 0.25)
            if distance < 8:
                continue
            for side in (90, -90):
                lat, lon = destination_point(here.lat, here.lon, (bearing + side) % 360, distance)
                key = (round(lat, 3), round(lon, 3))
                if key in seen:
                    continue
                seen.add(key)
                candidates.append((lat, lon))
    return candidates
