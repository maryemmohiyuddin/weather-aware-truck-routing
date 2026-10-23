"""Pick the route a dispatcher should run.

Comparison uses the numbers a person sees on the card, so a 0.01 mile
difference that would round away cannot decide the order:

  miles          0.1 mile, half up
  average risk   0.01, half up
  travel time    nearest minute

Order, best first:
  1. fewest no-travel miles
  2. fewest severe miles
  3. fewest high miles
  4. lowest average risk
  5. shortest travel time

No-travel is its own first key, ahead of severe miles. A stretch that should
not be driven is worse than a severe stretch, so any no-travel miles lose to
a route that has none, even if that route has more severe miles.

Average risk is the mile-weighted score from the checkpoint summary:
low 1, moderate 2, high 3, severe 4, no-travel 5.

If every factor ties, the route that was listed first stays first.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

FACTORS = (
    ("no_travel_miles", "no-travel miles", "the fewest no-travel miles"),
    ("severe_miles", "severe miles", "the fewest severe miles"),
    ("high_miles", "high miles", "the fewest high miles"),
    ("average_risk", "average risk", "the lowest average risk"),
    ("duration_seconds", "travel time", "the shortest travel time"),
)


def round_half_up(value: float, places: int) -> float:
    quantum = Decimal("1").scaleb(-places)
    return float(Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP))


def comparison_fields(route: dict) -> dict:
    minutes = round_half_up(float(route["duration_seconds"]) / 60.0, 0)
    return {
        "no_travel_miles": round_half_up(float(route["no_travel_miles"]), 1),
        "severe_miles": round_half_up(float(route["severe_miles"]), 1),
        "high_miles": round_half_up(float(route["high_miles"]), 1),
        "average_risk": round_half_up(float(route["average_risk"]), 2),
        "duration_seconds": minutes * 60.0,
    }


def rank_routes(routes: list[dict]) -> list[dict]:
    prepared = []
    for route in routes:
        item = dict(route)
        item.update(comparison_fields(route))
        prepared.append(item)

    def sort_key(route: dict) -> tuple:
        return (
            route["no_travel_miles"],
            route["severe_miles"],
            route["high_miles"],
            route["average_risk"],
            route["duration_seconds"],
        )

    ordered = sorted(prepared, key=sort_key)
    ranked = []
    for index, route in enumerate(ordered, start=1):
        item = dict(route)
        item["rank"] = index
        item["recommended"] = index == 1
        ranked.append(item)
    return ranked


def explain_recommendation(ranked: list[dict]) -> str:
    if not ranked:
        return "No routes to compare."
    winner = ranked[0]
    if len(ranked) == 1:
        return f"{winner['name']} is the only route, so it is the recommendation."

    runner_up = ranked[1]
    earlier: list[str] = []
    for key, label, phrase in FACTORS:
        if winner[key] != runner_up[key]:
            return _deciding_sentence(ranked, key, label, phrase, earlier)
        earlier.append(label)
    return (
        f"{winner['name']} is recommended because it ties the other routes on "
        "no-travel miles, severe miles, high miles, average risk, and travel time. "
        "The first route returned is shown."
    )


def format_duration(seconds: float) -> str:
    minutes = int(round_half_up(seconds / 60.0, 0))
    hours, mins = divmod(minutes, 60)
    if hours <= 0:
        return f"{mins} min"
    if mins == 0:
        return f"{hours} h"
    return f"{hours} h {mins} min"


def _format_value(key: str, value: float) -> str:
    if key == "average_risk":
        return f"{value:.2f}"
    if key == "duration_seconds":
        return format_duration(value)
    return f"{value:.1f} mi"


def _deciding_sentence(ranked: list[dict], key: str, label: str, phrase: str, earlier: list[str]) -> str:
    winner = ranked[0]
    others = [f"{route['name']} has {_format_value(key, route[key])}" for route in ranked[1:]]
    if len(others) == 1:
        comparison = others[0]
    else:
        comparison = ", ".join(others[:-1]) + f", and {others[-1]}"
    text = (
        f"{winner['name']} is recommended because it has {phrase} "
        f"({_format_value(key, winner[key])}). {comparison}."
    )
    if key == "no_travel_miles":
        text += (
            " No-travel miles are checked before severe miles, because a stretch "
            "that should not be driven is worse than a severe one."
        )
    elif earlier:
        joined = _join(earlier)
        text += f" It was tied with {ranked[1]['name']} on {joined}."
    return text


def _join(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"
