from django.test import SimpleTestCase

from planner.logic.recommend import explain_recommendation, rank_routes, round_half_up
from planner.logic.risk import classify_checkpoint
from planner.logic.sampling import summarize_checkpoints


def route(name, no_travel, severe, high, average, duration):
    return {
        "name": name,
        "no_travel_miles": no_travel,
        "severe_miles": severe,
        "high_miles": high,
        "average_risk": average,
        "duration_seconds": duration,
    }


class RankTests(SimpleTestCase):
    def test_no_travel_beats_a_route_with_lots_of_severe(self):
        ranked = rank_routes(
            [
                route("Route A", 10, 0, 0, 5, 1000),
                route("Route B", 0, 200, 0, 4, 5000),
            ]
        )
        self.assertEqual(ranked[0]["name"], "Route B")
        self.assertTrue(ranked[0]["recommended"])
        self.assertEqual(ranked[1]["rank"], 2)
        text = explain_recommendation(ranked)
        self.assertIn("fewest no-travel miles", text)
        self.assertIn("worse than a severe", text)

    def test_severe_miles_then_high_miles(self):
        ranked = rank_routes(
            [
                route("Route A", 0, 40, 0, 4, 1000),
                route("Route B", 0, 10, 80, 3, 9000),
                route("Route C", 0, 10, 20, 2, 9000),
            ]
        )
        self.assertEqual([item["name"] for item in ranked], ["Route C", "Route B", "Route A"])
        text = explain_recommendation(ranked)
        self.assertIn("fewest high miles", text)
        self.assertIn("severe miles", text)

    def test_average_risk_then_travel_time(self):
        ranked = rank_routes(
            [
                route("Route A", 0, 0, 0, 2.2, 3000),
                route("Route B", 0, 0, 0, 1.4, 8000),
                route("Route C", 0, 0, 0, 1.4, 4000),
            ]
        )
        self.assertEqual([item["name"] for item in ranked], ["Route C", "Route B", "Route A"])
        text = explain_recommendation(ranked)
        self.assertIn("shortest travel time", text)

    def test_average_risk_decides_when_miles_match(self):
        ranked = rank_routes(
            [
                route("Route A", 0, 0, 10, 2.4, 1000),
                route("Route B", 0, 0, 10, 1.8, 5000),
            ]
        )
        self.assertEqual(ranked[0]["name"], "Route B")
        self.assertIn("lowest average risk", explain_recommendation(ranked))

    def test_full_tie_keeps_the_first_route(self):
        ranked = rank_routes(
            [
                route("Route B", 0, 5, 5, 2, 3600),
                route("Route A", 0, 5, 5, 2, 3600),
            ]
        )
        self.assertEqual(ranked[0]["name"], "Route B")
        self.assertIn("ties the other routes", explain_recommendation(ranked))

    def test_rounding_matches_the_tenth_of_a_mile_on_the_card(self):
        self.assertEqual(round_half_up(10.05, 1), 10.1)
        self.assertEqual(round_half_up(10.04, 1), 10.0)
        ranked = rank_routes(
            [
                route("Route A", 0, 10.06, 0, 2, 1000),
                route("Route B", 0, 10.04, 0, 2, 1000),
            ]
        )
        self.assertEqual(ranked[0]["name"], "Route B")
        self.assertEqual(ranked[0]["severe_miles"], 10.0)
        self.assertEqual(ranked[1]["severe_miles"], 10.1)

    def test_only_route(self):
        ranked = rank_routes([route("Route A", 1, 1, 1, 2, 60)])
        self.assertIn("only route", explain_recommendation(ranked))


class LoadChangesTheRecommendationTests(SimpleTestCase):
    def test_heavy_load_can_change_which_route_wins(self):
        def build(name, wind, rain, load, duration):
            checkpoints = []
            for index in range(5):
                result = classify_checkpoint(wind, rain, 0, load)
                checkpoints.append({"distance_miles": index * 25, "risk": result["risk"]})
            summary = summarize_checkpoints(checkpoints)
            return route(
                name,
                summary["miles"]["no_travel"],
                summary["miles"]["severe"],
                summary["miles"]["high"],
                summary["average_risk"],
                duration,
            )

        light = rank_routes(
            [
                build("Windy", wind=36, rain=0, load=10000, duration=5 * 3600),
                build("Wet", wind=0, rain=0.8, load=10000, duration=4 * 3600),
            ]
        )
        heavy = rank_routes(
            [
                build("Windy", wind=36, rain=0, load=50000, duration=5 * 3600),
                build("Wet", wind=0, rain=0.8, load=50000, duration=4 * 3600),
            ]
        )
        self.assertEqual(light[0]["name"], "Windy")
        self.assertEqual(heavy[0]["name"], "Wet")
