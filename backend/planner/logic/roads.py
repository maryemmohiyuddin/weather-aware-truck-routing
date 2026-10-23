"""A short label for the road a route spends the most miles on."""

from __future__ import annotations


def dominant_road(steps: list[dict]) -> str | None:
    ref_miles: dict[str, float] = {}
    name_miles: dict[str, float] = {}
    for step in steps:
        distance = float(step.get("distance_meters") or 0)
        for ref in _split_refs(step.get("ref") or ""):
            ref_miles[ref] = ref_miles.get(ref, 0) + distance
        name = (step.get("name") or "").strip()
        if name:
            name_miles[name] = name_miles.get(name, 0) + distance
    if ref_miles:
        best = max(ref_miles, key=ref_miles.get)
        return _pretty_ref(best)
    if name_miles:
        return max(name_miles, key=name_miles.get)
    return None


def _split_refs(ref: str) -> list[str]:
    parts = []
    for piece in ref.split(";"):
        cleaned = piece.strip()
        if cleaned:
            parts.append(cleaned)
    return parts


def _pretty_ref(ref: str) -> str:
    parts = ref.split()
    if len(parts) == 2 and parts[1].replace("-", "").isdigit():
        return f"{parts[0]}-{parts[1]}"
    return ref
