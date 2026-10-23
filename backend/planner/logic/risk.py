"""Weather and load risk for one checkpoint.

Bands follow the assessment table. Weather values are continuous, so the
boundaries are defined here rather than left as gaps or overlaps.

Wind (mph), half-open until the no-travel line:
  low        wind < 25
  moderate   25 <= wind < 35     (the table's 25–34 band; 34.9 stays moderate)
  high       35 <= wind < 45
  severe     45 <= wind < 55
  no travel  wind >= 55

Rain (inches per hour). A number that sits on two columns takes the worse
class. 1.00 is still severe, because no-travel is only strictly above 1.00:
  low        rain < 0.10
  moderate   0.10 <= rain < 0.25
  high       0.25 <= rain < 0.50
  severe     0.50 <= rain <= 1.00
  no travel  rain > 1.00

Snow (inches per hour), same boundary rule. 3.0 is severe; no-travel is above 3.0:
  low        snow < 0.5
  moderate   0.5 <= snow < 1.0
  high       1.0 <= snow < 2.0
  severe     2.0 <= snow <= 3.0
  no travel  snow > 3.0

Load is applied to the wind reading only, and only ever raises the class:
  wind >= 55                         no travel, any load
  45 <= wind < 55 and load > 30000   no travel
  35 <= wind < 45 and load > 40000   severe
Exactly 30,000 lb or 40,000 lb does not trigger a load rule.

The checkpoint risk is the worst class among wind (after the load rule),
rain, and snow. Clear weather is Low. There is no separate "none" class.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from enum import Enum
import math


class RiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    SEVERE = "severe"
    NO_TRAVEL = "no_travel"

    @property
    def score(self) -> int:
        return {
            RiskLevel.LOW: 1,
            RiskLevel.MODERATE: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.SEVERE: 4,
            RiskLevel.NO_TRAVEL: 5,
        }[self]


def worst_risk(*levels: RiskLevel) -> RiskLevel:
    if not levels:
        raise ValueError("need at least one risk level")
    return max(levels, key=lambda level: level.score)


def _decimal(value: float | int | str | Decimal) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise TypeError("expected a number")
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        raise ValueError("expected a finite number")
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("expected a number") from exc


def _nonnegative(value: float | int | str | Decimal) -> Decimal:
    number = _decimal(value)
    if number < 0:
        return Decimal("0")
    return number


def classify_wind(mph: float) -> RiskLevel:
    wind = _nonnegative(mph)
    if wind >= 55:
        return RiskLevel.NO_TRAVEL
    if wind >= 45:
        return RiskLevel.SEVERE
    if wind >= 35:
        return RiskLevel.HIGH
    if wind >= 25:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def classify_rain(inches_per_hour: float) -> RiskLevel:
    rain = _nonnegative(inches_per_hour)
    if rain > 1:
        return RiskLevel.NO_TRAVEL
    if rain >= Decimal("0.50"):
        return RiskLevel.SEVERE
    if rain >= Decimal("0.25"):
        return RiskLevel.HIGH
    if rain >= Decimal("0.10"):
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def classify_snow(inches_per_hour: float) -> RiskLevel:
    snow = _nonnegative(inches_per_hour)
    if snow > 3:
        return RiskLevel.NO_TRAVEL
    if snow >= 2:
        return RiskLevel.SEVERE
    if snow >= 1:
        return RiskLevel.HIGH
    if snow >= Decimal("0.5"):
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def apply_load_rule(wind_mph: float, load_lb: float) -> RiskLevel:
    """Wind class after the load rules. Rain and snow are not changed."""
    wind = _nonnegative(wind_mph)
    load = _decimal(load_lb)
    if load < 0:
        raise ValueError("load weight cannot be negative")
    if wind >= 55:
        return RiskLevel.NO_TRAVEL
    if wind >= 45 and load > 30000:
        return RiskLevel.NO_TRAVEL
    if wind >= 35 and load > 40000:
        return RiskLevel.SEVERE
    return classify_wind(wind)


def load_note(wind_mph: float, load_lb: float) -> str | None:
    """Short sentence when the load rule changes the wind class. None otherwise."""
    before = classify_wind(wind_mph)
    after = apply_load_rule(wind_mph, load_lb)
    if after == before:
        return None
    if after == RiskLevel.NO_TRAVEL:
        return (
            "Wind is in the 45–54 mph band and the load is over 30,000 lb, "
            "so this checkpoint is no-travel."
        )
    if after == RiskLevel.SEVERE:
        return (
            "Wind is in the 35–44 mph band and the load is over 40,000 lb, "
            "so wind risk is raised to severe."
        )
    return None


def classify_checkpoint(
    wind_mph: float,
    rain_in_hr: float,
    snow_in_hr: float,
    load_lb: float,
) -> dict:
    wind_before = classify_wind(wind_mph)
    wind_after = apply_load_rule(wind_mph, load_lb)
    rain = classify_rain(rain_in_hr)
    snow = classify_snow(snow_in_hr)
    overall = worst_risk(wind_after, rain, snow)
    return {
        "wind_risk": wind_before.value,
        "wind_risk_after_load": wind_after.value,
        "rain_risk": rain.value,
        "snow_risk": snow.value,
        "risk": overall.value,
        "load_adjusted": wind_after != wind_before,
        "load_note": load_note(wind_mph, load_lb),
    }


def weather_intensity(wind_mph: float, rain_in_hr: float, snow_in_hr: float, load_lb: float) -> float:
    """Continuous 0–1 severity for the heatmap.

    1.0 means the reading has reached a no-travel threshold. The same load
    rules used for checkpoints raise the score, so a heavy load still shows
    up on the corridor. Inside a band the score moves with the weather,
    which is what makes the time slider look smooth.
    """
    wind = float(_nonnegative(wind_mph))
    rain = float(_nonnegative(rain_in_hr))
    snow = float(_nonnegative(snow_in_hr))
    score = max(wind / 55.0, rain / 1.0, snow / 3.0)
    if wind >= 55 or (45 <= wind < 55 and float(_decimal(load_lb)) > 30000):
        score = max(score, 1.0)
    elif 35 <= wind < 45 and float(_decimal(load_lb)) > 40000:
        score = max(score, 45 / 55)
    if score < 0:
        return 0.0
    if score > 1:
        return 1.0
    return score
