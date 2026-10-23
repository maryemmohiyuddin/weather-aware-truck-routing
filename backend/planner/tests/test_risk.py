from django.test import SimpleTestCase

from planner.logic.risk import (
    RiskLevel,
    apply_load_rule,
    classify_checkpoint,
    classify_rain,
    classify_snow,
    classify_wind,
    weather_intensity,
)


class WindBandTests(SimpleTestCase):
    def test_boundaries(self):
        cases = [
            (0, RiskLevel.LOW),
            (24.99, RiskLevel.LOW),
            (25, RiskLevel.MODERATE),
            (34, RiskLevel.MODERATE),
            (34.9, RiskLevel.MODERATE),
            (35, RiskLevel.HIGH),
            (44, RiskLevel.HIGH),
            (44.99, RiskLevel.HIGH),
            (45, RiskLevel.SEVERE),
            (54, RiskLevel.SEVERE),
            (54.99, RiskLevel.SEVERE),
            (55, RiskLevel.NO_TRAVEL),
            (70, RiskLevel.NO_TRAVEL),
        ]
        for mph, expected in cases:
            self.assertEqual(classify_wind(mph), expected, mph)

    def test_negative_wind_is_treated_as_calm(self):
        self.assertEqual(classify_wind(-3), RiskLevel.LOW)


class RainBandTests(SimpleTestCase):
    def test_boundaries(self):
        cases = [
            (0, RiskLevel.LOW),
            (0.099, RiskLevel.LOW),
            (0.10, RiskLevel.MODERATE),
            (0.249, RiskLevel.MODERATE),
            (0.25, RiskLevel.HIGH),
            (0.499, RiskLevel.HIGH),
            (0.50, RiskLevel.SEVERE),
            (1, RiskLevel.SEVERE),
            (1.00, RiskLevel.SEVERE),
            (1.001, RiskLevel.NO_TRAVEL),
            (2, RiskLevel.NO_TRAVEL),
        ]
        for inches, expected in cases:
            self.assertEqual(classify_rain(inches), expected, inches)


class SnowBandTests(SimpleTestCase):
    def test_boundaries(self):
        cases = [
            (0, RiskLevel.LOW),
            (0.49, RiskLevel.LOW),
            (0.5, RiskLevel.MODERATE),
            (0.99, RiskLevel.MODERATE),
            (1, RiskLevel.HIGH),
            (1.0, RiskLevel.HIGH),
            (1.99, RiskLevel.HIGH),
            (2, RiskLevel.SEVERE),
            (3, RiskLevel.SEVERE),
            (3.0, RiskLevel.SEVERE),
            (3.01, RiskLevel.NO_TRAVEL),
        ]
        for inches, expected in cases:
            self.assertEqual(classify_snow(inches), expected, inches)


class LoadRuleTests(SimpleTestCase):
    def test_fifty_five_is_no_travel_for_any_load(self):
        self.assertEqual(apply_load_rule(55, 0), RiskLevel.NO_TRAVEL)
        self.assertEqual(apply_load_rule(55, 80000), RiskLevel.NO_TRAVEL)

    def test_severe_wind_and_load_over_30000_is_no_travel(self):
        self.assertEqual(apply_load_rule(45, 30001), RiskLevel.NO_TRAVEL)
        self.assertEqual(apply_load_rule(54, 30001), RiskLevel.NO_TRAVEL)
        self.assertEqual(apply_load_rule(54.99, 45000), RiskLevel.NO_TRAVEL)

    def test_exactly_30000_does_not_upgrade(self):
        self.assertEqual(apply_load_rule(45, 30000), RiskLevel.SEVERE)
        self.assertEqual(apply_load_rule(54, 30000), RiskLevel.SEVERE)

    def test_high_wind_and_load_over_40000_is_severe(self):
        self.assertEqual(apply_load_rule(35, 40001), RiskLevel.SEVERE)
        self.assertEqual(apply_load_rule(44, 40001), RiskLevel.SEVERE)
        self.assertEqual(apply_load_rule(44.99, 50000), RiskLevel.SEVERE)

    def test_exactly_40000_does_not_upgrade(self):
        self.assertEqual(apply_load_rule(35, 40000), RiskLevel.HIGH)
        self.assertEqual(apply_load_rule(44, 40000), RiskLevel.HIGH)

    def test_load_does_not_upgrade_moderate_wind(self):
        self.assertEqual(apply_load_rule(34.99, 80000), RiskLevel.MODERATE)
        self.assertEqual(apply_load_rule(25, 80000), RiskLevel.MODERATE)
        self.assertEqual(apply_load_rule(10, 80000), RiskLevel.LOW)

    def test_negative_load_is_rejected(self):
        with self.assertRaises(ValueError):
            apply_load_rule(20, -1)


class CheckpointTests(SimpleTestCase):
    def test_worst_condition_wins(self):
        result = classify_checkpoint(wind_mph=10, rain_in_hr=0.6, snow_in_hr=0, load_lb=80000)
        self.assertEqual(result["wind_risk"], "low")
        self.assertEqual(result["rain_risk"], "severe")
        self.assertEqual(result["risk"], "severe")
        self.assertFalse(result["load_adjusted"])

    def test_load_upgrade_can_set_the_checkpoint(self):
        result = classify_checkpoint(wind_mph=36, rain_in_hr=0, snow_in_hr=0, load_lb=50000)
        self.assertEqual(result["wind_risk"], "high")
        self.assertEqual(result["wind_risk_after_load"], "severe")
        self.assertEqual(result["risk"], "severe")
        self.assertTrue(result["load_adjusted"])
        self.assertIn("40,000", result["load_note"])

    def test_no_travel_wind_beats_calm_precip(self):
        result = classify_checkpoint(wind_mph=60, rain_in_hr=0, snow_in_hr=0, load_lb=0)
        self.assertEqual(result["risk"], "no_travel")
        self.assertFalse(result["load_adjusted"])
        self.assertIsNone(result["load_note"])

    def test_snow_no_travel_beats_moderate_wind(self):
        result = classify_checkpoint(wind_mph=30, rain_in_hr=0, snow_in_hr=3.2, load_lb=10000)
        self.assertEqual(result["snow_risk"], "no_travel")
        self.assertEqual(result["risk"], "no_travel")


class IntensityTests(SimpleTestCase):
    def test_calm_is_near_zero_and_no_travel_wind_is_one(self):
        self.assertEqual(weather_intensity(0, 0, 0, 0), 0)
        self.assertEqual(weather_intensity(55, 0, 0, 0), 1)

    def test_heavy_load_raises_high_wind(self):
        light = weather_intensity(40, 0, 0, 10000)
        heavy = weather_intensity(40, 0, 0, 50000)
        self.assertGreater(heavy, light)
        self.assertGreaterEqual(heavy, 45 / 55)

    def test_score_follows_the_worst_ingredient(self):
        self.assertAlmostEqual(weather_intensity(0, 0.5, 0, 0), 0.5)
        self.assertAlmostEqual(weather_intensity(0, 0, 1.5, 0), 0.5)
