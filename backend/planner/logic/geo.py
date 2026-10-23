"""Small geographic helpers. Distances are statute miles."""

from __future__ import annotations

from dataclasses import dataclass
import math

EARTH_RADIUS_MILES = 3958.7613
METERS_PER_MILE = 1609.344


@dataclass(frozen=True)
class PathPoint:
    lat: float
    lon: float
    miles: float
    seconds: float


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(a))


def bearing_degrees(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_lambda = math.radians(lon2 - lon1)
    y = math.sin(d_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(d_lambda)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def destination_point(lat: float, lon: float, bearing_deg: float, distance_miles: float) -> tuple[float, float]:
    delta = distance_miles / EARTH_RADIUS_MILES
    theta = math.radians(bearing_deg)
    phi1 = math.radians(lat)
    lambda1 = math.radians(lon)
    phi2 = math.asin(math.sin(phi1) * math.cos(delta) + math.cos(phi1) * math.sin(delta) * math.cos(theta))
    lambda2 = lambda1 + math.atan2(
        math.sin(theta) * math.sin(delta) * math.cos(phi1),
        math.cos(delta) - math.sin(phi1) * math.sin(phi2),
    )
    lon2 = (math.degrees(lambda2) + 540) % 360 - 180
    return math.degrees(phi2), lon2


def point_at_distance(path: list[PathPoint], miles: float) -> PathPoint:
    if not path:
        raise ValueError("empty path")
    if miles <= path[0].miles:
        start = path[0]
        return PathPoint(start.lat, start.lon, start.miles, start.seconds)
    if miles >= path[-1].miles:
        return path[-1]
    for left, right in zip(path, path[1:]):
        if right.miles >= miles:
            span = right.miles - left.miles
            fraction = 0 if span == 0 else (miles - left.miles) / span
            return PathPoint(
                lat=left.lat + (right.lat - left.lat) * fraction,
                lon=left.lon + (right.lon - left.lon) * fraction,
                miles=miles,
                seconds=left.seconds + (right.seconds - left.seconds) * fraction,
            )
    return path[-1]


def path_from_coordinates(coords: list[tuple[float, float]], duration_seconds: float) -> list[PathPoint]:
    """Build cumulative miles along a lat/lon line. Time is proportional to distance."""
    if not coords:
        raise ValueError("route has no geometry")
    points: list[PathPoint] = []
    miles = 0.0
    previous: tuple[float, float] | None = None
    for lat, lon in coords:
        if previous is not None:
            miles += haversine_miles(previous[0], previous[1], lat, lon)
        points.append(PathPoint(lat, lon, miles, 0.0))
        previous = (lat, lon)
    total = points[-1].miles
    if total <= 0 or duration_seconds <= 0:
        return points
    return [
        PathPoint(point.lat, point.lon, point.miles, duration_seconds * (point.miles / total))
        for point in points
    ]


def mean_separation_miles(left: list[PathPoint], right: list[PathPoint], samples: int = 20) -> float:
    """Average distance between two paths, sampled by fraction of each path's length."""
    if not left or not right:
        return 0.0
    total = 0.0
    for index in range(samples):
        fraction = 0 if samples == 1 else index / (samples - 1)
        a = point_at_distance(left, left[-1].miles * fraction)
        b = point_at_distance(right, right[-1].miles * fraction)
        total += haversine_miles(a.lat, a.lon, b.lat, b.lon)
    return total / samples


def downsample(coords: list[tuple[float, float]], max_points: int = 700) -> list[list[float]]:
    if len(coords) <= max_points:
        return [[lat, lon] for lat, lon in coords]
    if max_points < 2:
        lat, lon = coords[0]
        return [[lat, lon]]
    chosen: list[list[float]] = []
    last_index = len(coords) - 1
    for index in range(max_points - 1):
        source = round(index * last_index / (max_points - 1))
        lat, lon = coords[source]
        chosen.append([lat, lon])
    lat, lon = coords[-1]
    chosen.append([lat, lon])
    return chosen
