from django.test import SimpleTestCase


class ApiTests(SimpleTestCase):
    def test_health(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_plan_rejects_a_bad_body(self):
        response = self.client.post("/api/plan/", {"origin": {}}, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_geocode_short_query_does_not_call_out(self):
        response = self.client.get("/api/geocode/", {"q": "a"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [])
