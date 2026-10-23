"""Sample a driven path every 10, 25, or 50 miles.

Checkpoint miles are distance along the road, not straight-line distance.
The destination is always included, even when the route length is not a
multiple of the interval.

Miles of risk are assigned by the nearest checkpoint. An interior checkpoint
owns the road from the midpoint back to the previous checkpoint to the
midpoint toward the next one, so one severe sample counts about one interval
and the pieces add up to the route length.
"""

from __future__ import annotations

from planner.logic.geo import (
    METERS_PER_MILE,
    PathPoint,
    bearing_degrees,
    destination_point,
    haversine_miles,
    point_at_distance,
)
from planner.logic.risk import RiskLevel

ALLOWED_INTERVALS = (10, 25, 50)


def sample_distances(total_miles: float, interval: int) -> list[float]:
    if interval not in ALLOWED_INTERVALS:
        raise ValueError("sample interval must be 10, 25, or 50 miles")
    if total_miles < 0:
        raise ValueError("distance cannot be negative")
    if total_miles <= 1e-6:
        return [0.0]
    targets = [0.0]
    mile = float(interval)
    while mile < total_miles - 1e-6:
        targets.append(mile)
        mile += interval
    if targets[-1] < total_miles - 1e-6:
        targets.append(float(total_miles))
    return targets


def sample_path(path: list[PathPoint], interval: int) -> list[PathPoint]:
    if not path:
        raise ValueError("empty path")
    return [point_at_distance(path, mile) for mile in sample_distances(path[-1].miles, interval)]


def path_from_steps(steps: list[dict]) -> list[PathPoint]:
    """Walk OSRM steps. Time follows each step's duration, spread by geometry length."""
    points: list[PathPoint] = []
    cum_miles = 0.0
    cum_seconds = 0.0
    for step in steps:
        latlon = [(pair[1], pair[0]) for pair in step.get("coordinates") or []]
        if not latlon:
            continue
        lengths = [
            haversine_miles(a[0], a[1], b[0], b[1]) for a, b in zip(latlon, latlon[1:])
        ]
        geometry_miles = sum(lengths)
        step_miles = float(step.get("distance_meters") or 0) / METERS_PER_MILE
        step_seconds = float(step.get("duration_seconds") or 0)
        if not points:
            points.append(PathPoint(latlon[0][0], latlon[0][1], cum_miles, cum_seconds))
        elif haversine_miles(points[-1].lat, points[-1].lon, latlon[0][0], latlon[0][1]) > 0.05:
            points.append(PathPoint(latlon[0][0], latlon[0][1], cum_miles, cum_seconds))
        if geometry_miles <= 1e-9 or len(latlon) == 1:
            cum_miles += step_miles
            cum_seconds += step_seconds
            points.append(PathPoint(latlon[-1][0], latlon[-1][1], cum_miles, cum_seconds))
            continue
        for (lat, lon), segment in zip(latlon[1:], lengths):
            fraction = segment / geometry_miles
            cum_miles += step_miles * fraction
            cum_seconds += step_seconds * fraction
            points.append(PathPoint(lat, lon, cum_miles, cum_seconds))
    if not points:
        raise ValueError("route has no geometry")
    return _collapse_duplicates(points)


def scale_path(path: list[PathPoint], target_miles: float, target_seconds: float) -> list[PathPoint]:
    """Line the path's end up with the router's official distance and duration."""
    if not path:
        return path
    end_miles = path[-1].miles
    end_seconds = path[-1].seconds
    mile_factor = (target_miles / end_miles) if end_miles > 1e-9 and target_miles >= 0 else None
    second_factor = (target_seconds / end_seconds) if end_seconds > 1e-9 and target_seconds >= 0 else None
    scaled: list[PathPoint] = []
    for point in path:
        miles = point.miles if mile_factor is None else point.miles * mile_factor
        if second_factor is None:
            if end_miles > 1e-9 and target_seconds > 0:
                seconds = target_seconds * (point.miles / end_miles)
            else:
                seconds = 0.0
        else:
            seconds = point.seconds * second_factor
        scaled.append(PathPoint(point.lat, point.lon, miles, seconds))
    return scaled


def summarize_checkpoints(checkpoints: list[dict]) -> dict:
    """Distance-weighted risk from nearest-checkpoint ownership."""
    if not checkpoints:
        raise ValueError("no checkpoints")
    levels = [RiskLevel(item["risk"]) for item in checkpoints]
    distances = [float(item["distance_miles"]) for item in checkpoints]
    for earlier, later in zip(distances, distances[1:]):
        if later < earlier - 1e-6:
            raise ValueError("checkpoint distances must not decrease")
    totals = {level: 0.0 for level in RiskLevel}
    total_miles = distances[-1] - distances[0]
    if len(checkpoints) == 1 or total_miles <= 1e-9:
        return {
            "miles": {level.value: 0.0 for level in RiskLevel},
            "average_risk": float(levels[0].score),
            "total_miles": 0.0,
        }
    edges = [distances[0]]
    for earlier, later in zip(distances, distances[1:]):
        edges.append((earlier + later) / 2)
    edges.append(distances[-1])
    weighted = 0.0
    for index, level in enumerate(levels):
        span = max(0.0, edges[index + 1] - edges[index])
        totals[level] += span
        weighted += span * level.score
    return {
        "miles": {level.value: totals[level] for level in RiskLevel},
        "average_risk": weighted / total_miles,
        "total_miles": total_miles,
    }


def corridor_points(
    paths: list[list[PathPoint]],
    spacing_miles: float = 40,
    lateral_miles: float = 16,
    cap: int = 80,
) -> list[tuple[float, float]]:
    """Points along and just beside the routes, for the forecast heatmap."""
    raw: list[tuple[float, float]] = []
    for path in paths:
        if not path:
            continue
        total = path[-1].miles
        if total <= 0:
            raw.append((path[0].lat, path[0].lon))
            continue
        step = max(spacing_miles, total / 10)
        mile = 0.0
        while mile <= total + 1e-6:
            here = point_at_distance(path, min(mile, total))
            ahead = point_at_distance(path, min(total, mile + max(1.0, step * 0.25)))
            if abs(ahead.lat - here.lat) < 1e-7 and abs(ahead.lon - here.lon) < 1e-7:
                bearing = 0.0
            else:
                bearing = bearing_degrees(here.lat, here.lon, ahead.lat, ahead.lon)
            raw.append((here.lat, here.lon))
            for side in (90, -90):
                raw.append(destination_point(here.lat, here.lon, (bearing + side) % 360, lateral_miles))
            mile += step
    seen: set[tuple[float, float]] = set()
    unique: list[tuple[float, float]] = []
    for lat, lon in raw:
        key = (round(lat, 2), round(lon, 2))
        if key in seen:
            continue
        seen.add(key)
        unique.append((lat, lon))
    if len(unique) <= cap:
        return unique
    picked: list[tuple[float, float]] = []
    last = len(unique) - 1
    for index in range(cap):
        picked.append(unique[round(index * last / (cap - 1))])
    return picked


def _collapse_duplicates(points: list[PathPoint]) -> list[PathPoint]:
    cleaned = [points[0]]
    for point in points[1:]:
        previous = cleaned[-1]
        if abs(point.lat - previous.lat) < 1e-9 and abs(point.lon - previous.lon) < 1e-9:
            cleaned[-1] = point
        else:
            cleaned.append(point)
    return cleaned
