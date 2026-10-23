"""Unit conversions for Open-Meteo.

The forecast is requested in the API's native units on purpose:
  wind_speed_10m  kilometers per hour
  rain, showers   millimeters
  snowfall        centimeters of snow (not water equivalent, not millimeters)

Snowfall divided by 25.4 would be ten times too small. One inch of snow is
2.54 cm. Rain and showers are liquid depth, so those do use 25.4.
"""

from __future__ import annotations

from decimal import Decimal


def kmh_to_mph(kmh: float) -> float:
    return float(Decimal(str(kmh)) / Decimal("1.609344"))


def mm_to_inches(mm: float) -> float:
    return float(Decimal(str(mm)) / Decimal("25.4"))


def cm_to_inches(cm: float) -> float:
    return float(Decimal(str(cm)) / Decimal("2.54"))
