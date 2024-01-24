from app import app
from unittest import TestCase


class BackEndTest(TestCase):
    def test_marketing_route(self):
        with app.test_client() as client:
            data = {"prompt": "apple"}

            res = client.post("/api/market-research", json=data)
            self.assertEqual(res.status_code, 200)
            self.assertIn("competitors", res.json)
            
    def test__route(self):
        with app.test_client() as client:
            data = {"prompt": "Dear Behnam, what happend to your interview?"}
            res = client.post("/api/personalize-email", json=data)
            self.assertEqual(res.status_code, 200)
            self.assertIn("data", res.json)
