from datetime import datetime, timedelta, timezone

from django.test import SimpleTestCase

from planner.validate import ValidationError, parse_plan_request

NOW = datetime(2026, 10, 23, 16, 0, tzinfo=timezone.utc)


def payload(**overrides):
    body = {
        "origin": {"label": "Chicago", "lat": 41.88, "lon": -87.63},
        "destination": {"label": "Detroit", "lat": 42.33, "lon": -83.05},
        "departure": "2026-10-24T13:00:00Z",
        "load_weight_lb": 35000,
        "sample_miles": 25,
    }
    body.update(overrides)
    return body


class ValidateTests(SimpleTestCase):
    def test_happy_path(self):
        parsed = parse_plan_request(payload(), now=NOW)
        self.assertEqual(parsed["sample_miles"], 25)
        self.assertEqual(parsed["load_weight_lb"], 35000)
        self.assertEqual(parsed["departure"].tzinfo, timezone.utc)

    def test_points_too_close(self):
        with self.assertRaises(ValidationError):
            parse_plan_request(
                payload(destination={"label": "Nearby", "lat": 41.881, "lon": -87.63}),
                now=NOW,
            )

    def test_load_boundaries(self):
        parse_plan_request(payload(load_weight_lb=0), now=NOW)
        parse_plan_request(payload(load_weight_lb=30000), now=NOW)
        with self.assertRaises(ValidationError):
            parse_plan_request(payload(load_weight_lb=-1), now=NOW)

    def test_interval_and_departure_window(self):
        with self.assertRaises(ValidationError):
            parse_plan_request(payload(sample_miles=15), now=NOW)
        too_soon = (NOW - timedelta(days=3)).isoformat()
        too_late = (NOW + timedelta(days=8)).isoformat()
        with self.assertRaises(ValidationError):
            parse_plan_request(payload(departure=too_soon), now=NOW)
        with self.assertRaises(ValidationError):
            parse_plan_request(payload(departure=too_late), now=NOW)
