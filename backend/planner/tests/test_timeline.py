from datetime import datetime, timezone

from django.test import SimpleTestCase

from planner.logic.timeline import project_timeline


def _calm():
    return {"wind_mph": 0.0, "rain_in_hr": 0.0, "snow_in_hr": 0.0, "missing": False}


def _storm():
    return {"wind_mph": 60.0, "rain_in_hr": 0.0, "snow_in_hr": 0.0, "missing": False}


def _row(miles, seconds, readings):
    return {
        "lat": 41.0,
        "lon": -87.0,
        "distance_miles": miles,
        "elapsed_seconds": seconds,
        "readings": readings,
    }


def _route(name, duration, readings):
    return {
        "id": name[-1],
        "name": name,
        "source": "osrm",
        "via_label": "I-80",
        "via": None,
        "distance_miles": 100.0,
        "duration_seconds": duration,
        "geometry": [(41.0, -87.0), (40.0, -75.0)],
        "samples": [
            _row(0.0, 0, readings),
            _row(100.0, duration, readings),
        ],
    }


class TimelineTests(SimpleTestCase):
    def test_a_later_hour_can_change_the_winner_and_the_arrival(self):
        calm = [_calm() for _ in range(5)]
        storm_later = [_calm(), _calm(), _calm(), _calm(), _storm()]
        departure = datetime(2026, 10, 27, 18, 0, tzinfo=timezone.utc)
        ranked, frames = project_timeline(
            [
                _route("Route A", 3600, storm_later),
                _route("Route B", 7200, calm),
            ],
            departure,
            10000,
            hours=5,
        )

        self.assertEqual(ranked[0]["name"], "Route A")
        self.assertEqual(frames[0]["recommendation"]["route_id"], "A")
        self.assertEqual(frames[0]["routes"][0]["checkpoints"][1]["eta"], "2026-10-27T19:00:00Z")

        later = frames[4]
        self.assertEqual(later["departure"], "2026-10-27T22:00:00Z")
        self.assertEqual(later["recommendation"]["route_id"], "B")
        self.assertIn("no-travel", later["recommendation"]["summary"])
        by_id = {item["id"]: item for item in later["routes"]}
        self.assertEqual(by_id["A"]["miles"]["no_travel"], 100.0)
        self.assertEqual(by_id["B"]["miles"]["no_travel"], 0.0)
        self.assertEqual(by_id["A"]["checkpoints"][1]["risk"], "no_travel")
        self.assertEqual(by_id["A"]["checkpoints"][1]["eta"], "2026-10-27T23:00:00Z")
        self.assertEqual(by_id["B"]["checkpoints"][0]["risk"], "low")
