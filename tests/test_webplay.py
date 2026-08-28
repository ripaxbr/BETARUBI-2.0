import os
import unittest

os.environ.pop("DATABASE_URL", None)
os.environ.setdefault("SECRET_KEY", "test-secret")

from app import app


class WebplaySmokeTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_home_is_webplay(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("WEBPLAY", body)
        self.assertNotIn("BETARUBI 2.0", body)

    def test_originals_route_is_available(self):
        response = self.client.get("/originais")
        self.assertEqual(response.status_code, 200)
        self.assertIn("WEBPLAY", response.get_data(as_text=True))

    def test_invalid_newsletter_is_rejected(self):
        response = self.client.post(
            "/api/newsletter/subscribe",
            json={"email": "not-an-email"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["ok"])

    def test_health_is_explicit_when_database_is_missing(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.get_json()["ok"])
        self.assertEqual(response.get_json()["service"], "WEBPLAY")


if __name__ == "__main__":
    unittest.main()
