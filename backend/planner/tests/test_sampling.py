from django.test import SimpleTestCase

from planner.logic.geo import destination_point, haversine_miles, path_from_coordinates, point_at_distance
from planner.logic.sampling import (
    path_from_steps,
    sample_distances,
    sample_path,
    scale_path,
    summarize_checkpoints,
)


class SampleDistanceTests(SimpleTestCase):
    def test_exact_multiples(self):
        self.assertEqual(sample_distances(50, 25), [0.0, 25.0, 50.0])
        self.assertEqual(sample_distances(50, 50), [0.0, 50.0])
        self.assertEqual(sample_distances(25, 25), [0.0, 25.0])

    def test_destination_is_kept_when_the_length_is_not_a_multiple(self):
        self.assertEqual(sample_distances(60, 50), [0.0, 50.0, 60.0])
        self.assertEqual(sample_distances(60, 25), [0.0, 25.0, 50.0, 60.0])

    def test_short_route_is_origin_and_destination(self):
        self.assertEqual(sample_distances(8, 10), [0.0, 8.0])
        self.assertEqual(sample_distances(0, 10), [0.0])

    def test_ten_mile_spacing(self):
        self.assertEqual(sample_distances(30, 10), [0.0, 10.0, 20.0, 30.0])

    def test_invalid_interval(self):
        with self.assertRaises(ValueError):
            sample_distances(40, 15)
        with self.assertRaises(ValueError):
            sample_distances(-1, 10)


class SampleAlongPathTests(SimpleTestCase):
    def test_samples_follow_the_road_not_the_straight_line(self):
        corner = destination_point(40, -90, 0, 30)
        end = destination_point(corner[0], corner[1], 90, 40)
        coords = [destination_point(40, -90, 0, mile) for mile in range(31)]
        coords += [destination_point(corner[0], corner[1], 90, mile) for mile in range(1, 41)]
        path = path_from_coordinates(coords, duration_seconds=7000)
        samples = sample_path(path, 50)
        self.assertEqual(len(samples), 3)
        self.assertAlmostEqual(samples[0].miles, 0, places=2)
        self.assertAlmostEqual(samples[-1].miles, path[-1].miles, places=2)
        self.assertGreater(path[-1].miles, 69)
        self.assertLess(path[-1].miles, 71)
        expected = destination_point(corner[0], corner[1], 90, 20)
        self.assertLess(haversine_miles(samples[1].lat, samples[1].lon, expected[0], expected[1]), 0.3)
        straight = destination_point(40, -90, bearing_to(end), 50)
        self.assertGreater(haversine_miles(samples[1].lat, samples[1].lon, straight[0], straight[1]), 5)

    def test_time_is_proportional_when_the_path_has_one_speed(self):
        coords = [destination_point(41, -87, 0, mile) for mile in range(0, 51, 5)]
        path = path_from_coordinates(coords, duration_seconds=5000)
        samples = sample_path(path, 25)
        self.assertEqual([round(sample.miles, 2) for sample in samples], [0, 25, 50])
        self.assertAlmostEqual(samples[1].seconds, 2500, delta=5)
        self.assertAlmostEqual(samples[2].seconds, 5000, delta=5)


class StepPathTests(SimpleTestCase):
    def test_step_duration_is_spread_along_the_step(self):
        miles = haversine_miles(40, -90, 41, -90)
        steps = [
            {
                "coordinates": [[-90, 40], [-90, 41]],
                "distance_meters": miles * 1609.344,
                "duration_seconds": 3600,
            }
        ]
        path = path_from_steps(steps)
        self.assertAlmostEqual(path[-1].miles, miles, delta=0.05)
        self.assertAlmostEqual(path[-1].seconds, 3600, delta=0.1)
        middle = point_at_distance(path, miles / 2)
        self.assertAlmostEqual(middle.seconds, 1800, delta=1)
        self.assertAlmostEqual(middle.lat, 40.5, delta=0.02)

    def test_scale_path_matches_the_official_distance(self):
        path = path_from_coordinates([(40, -90), (41, -90)], duration_seconds=100)
        scaled = scale_path(path, target_miles=80, target_seconds=4000)
        self.assertAlmostEqual(scaled[-1].miles, 80, places=3)
        self.assertAlmostEqual(scaled[-1].seconds, 4000, places=3)


class OwnedMilesTests(SimpleTestCase):
    def test_interior_checkpoint_owns_one_interval(self):
        checkpoints = [
            {"distance_miles": 0, "risk": "low"},
            {"distance_miles": 25, "risk": "severe"},
            {"distance_miles": 50, "risk": "low"},
            {"distance_miles": 75, "risk": "low"},
        ]
        summary = summarize_checkpoints(checkpoints)
        self.assertAlmostEqual(summary["miles"]["severe"], 25)
        self.assertAlmostEqual(summary["miles"]["low"], 50)
        self.assertAlmostEqual(sum(summary["miles"].values()), 75)
        self.assertAlmostEqual(summary["average_risk"], 2.0)

    def test_two_checkpoints_split_the_route(self):
        summary = summarize_checkpoints(
            [
                {"distance_miles": 0, "risk": "severe"},
                {"distance_miles": 50, "risk": "low"},
            ]
        )
        self.assertAlmostEqual(summary["miles"]["severe"], 25)
        self.assertAlmostEqual(summary["miles"]["low"], 25)

    def test_zero_length_uses_the_only_checkpoint(self):
        summary = summarize_checkpoints([{"distance_miles": 0, "risk": "high"}])
        self.assertEqual(summary["total_miles"], 0)
        self.assertAlmostEqual(summary["average_risk"], 3)


def bearing_to(point):
    from planner.logic.geo import bearing_degrees

    return bearing_degrees(40, -90, point[0], point[1])
