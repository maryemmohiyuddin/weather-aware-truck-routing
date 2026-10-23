from datetime import datetime, timezone

from django.test import SimpleTestCase

from planner.logic.roads import dominant_road
from planner.logic.units import cm_to_inches, kmh_to_mph, mm_to_inches
from planner.logic.weather import floor_hour, parse_hourly_payload, select_reading


class UnitTests(SimpleTestCase):
    def test_conversions_are_exact_at_one_unit(self):
        self.assertAlmostEqual(cm_to_inches(2.54), 1.0, places=9)
        self.assertAlmostEqual(mm_to_inches(25.4), 1.0, places=9)
        self.assertAlmostEqual(kmh_to_mph(1.609344), 1.0, places=6)

    def test_snow_is_not_converted_as_if_it_were_millimeters(self):
        as_snow = cm_to_inches(2.54)
        as_rain = mm_to_inches(2.54)
        self.assertAlmostEqual(as_snow, 1.0, places=6)
        self.assertLess(as_rain, 0.2)


class HourMatchTests(SimpleTestCase):
    def test_wind_uses_the_eta_hour_and_precip_uses_the_next_hour(self):
        payload = {
            "hourly_units": {
                "wind_speed_10m": "km/h",
                "rain": "mm",
                "showers": "mm",
                "snowfall": "cm",
            },
            "hourly": {
                "time": [0, 3600, 7200],
                "wind_speed_10m": [0, 160.9344, 0],
                "rain": [0, 0, 25.4],
                "showers": [0, 0, 25.4],
                "snowfall": [0, 0, 2.54],
            },
        }
        hours = parse_hourly_payload(payload)
        eta = datetime.fromtimestamp(4000, tz=timezone.utc)
        self.assertEqual(floor_hour(eta), 3600)
        reading = select_reading(hours, eta)
        self.assertAlmostEqual(reading.wind_mph, 100, places=4)
        self.assertAlmostEqual(reading.rain_in_hr, 2.0, places=4)
        self.assertAlmostEqual(reading.snow_in_hr, 1.0, places=4)
        self.assertFalse(reading.missing)

    def test_rain_includes_showers(self):
        payload = {
            "hourly_units": {"wind_speed_10m": "km/h", "rain": "mm", "snowfall": "cm"},
            "hourly": {
                "time": [0],
                "wind_speed_10m": [0],
                "rain": [12.7],
                "showers": [12.7],
                "snowfall": [0],
            },
        }
        reading = parse_hourly_payload(payload)[0]
        self.assertAlmostEqual(reading.rain_in_hr, 1.0, places=6)

    def test_null_wind_is_missing_and_treated_as_zero(self):
        payload = {
            "hourly": {
                "time": [0],
                "wind_speed_10m": [None],
                "rain": [0],
                "showers": [0],
                "snowfall": [0],
            }
        }
        reading = parse_hourly_payload(payload)[0]
        self.assertTrue(reading.missing)
        self.assertEqual(reading.wind_mph, 0)

    def test_unexpected_snow_unit_is_rejected(self):
        payload = {
            "hourly_units": {"snowfall": "mm", "wind_speed_10m": "km/h", "rain": "mm"},
            "hourly": {"time": [], "wind_speed_10m": [], "rain": [], "snowfall": []},
        }
        with self.assertRaises(ValueError):
            parse_hourly_payload(payload)

    def test_missing_next_hour_falls_back_to_the_eta_hour(self):
        payload = {
            "hourly": {
                "time": [3600],
                "wind_speed_10m": [16.09344],
                "rain": [2.54],
                "showers": [0],
                "snowfall": [0],
            }
        }
        hours = parse_hourly_payload(payload)
        eta = datetime.fromtimestamp(3600, tz=timezone.utc)
        reading = select_reading(hours, eta)
        self.assertAlmostEqual(reading.wind_mph, 10, places=4)
        self.assertAlmostEqual(reading.rain_in_hr, 0.1, places=4)


class RoadLabelTests(SimpleTestCase):
    def test_longest_ref_wins_and_is_hyphenated(self):
        steps = [
            {"ref": "I 90", "name": "Indiana Toll Road", "distance_meters": 1000},
            {"ref": "I 80", "name": "Ohio Turnpike", "distance_meters": 8000},
            {"ref": "I 80; I 90", "name": "Ohio Turnpike", "distance_meters": 2000},
            {"ref": "", "name": "Main Street", "distance_meters": 20000},
        ]
        self.assertEqual(dominant_road(steps), "I-80")

    def test_name_is_used_when_there_is_no_ref(self):
        steps = [{"ref": "", "name": "Ohio Turnpike", "distance_meters": 100}]
        self.assertEqual(dominant_road(steps), "Ohio Turnpike")
