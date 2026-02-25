import os
import shutil
import tempfile
from unittest import TestCase
from unittest.mock import patch

from r2d2_backend import create_app


class BackEndTest(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="r2d2_backend_tests_")
        self.db_path = os.path.join(self.temp_dir, "test.sqlite3")
        os.environ["DATABASE_PATH"] = self.db_path
        os.environ["APP_SECRET_KEY"] = "unit-test-secret"
        os.environ["APP_ENV"] = "development"
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        os.environ.pop("DATABASE_PATH", None)
        os.environ.pop("APP_SECRET_KEY", None)
        os.environ.pop("APP_ENV", None)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _auth_headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    def _register_user(self, email="user@example.com", password="Password123!"):
        response = self.client.post(
            "/api/auth/register",
            json={"email": email, "password": password},
        )
        self.assertEqual(response.status_code, 200)
        return response.json["token"]

    def test_register_and_login_success(self):
        register_response = self.client.post(
            "/api/auth/register",
            json={"email": "first@example.com", "password": "Password123!"},
        )
        self.assertEqual(register_response.status_code, 200)
        self.assertIn("token", register_response.json)
        self.assertEqual(register_response.json["user"]["email"], "first@example.com")

        login_response = self.client.post(
            "/api/auth/login",
            json={"email": "first@example.com", "password": "Password123!"},
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertIn("token", login_response.json)
        self.assertEqual(login_response.json["user"]["email"], "first@example.com")

    def test_register_duplicate_user(self):
        self._register_user(email="duplicate@example.com")
        duplicate_response = self.client.post(
            "/api/auth/register",
            json={"email": "duplicate@example.com", "password": "Password123!"},
        )
        self.assertEqual(duplicate_response.status_code, 409)
        self.assertEqual(duplicate_response.json["error"], "User already exists.")

    def test_register_rejects_weak_password(self):
        response = self.client.post(
            "/api/auth/register",
            json={"email": "weak@example.com", "password": "weakpass"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Password must", response.json["error"])

    def test_auth_me_requires_token(self):
        response = self.client.get("/api/auth/me")
        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.json)

    def test_auth_me_success(self):
        token = self._register_user(email="me@example.com")
        response = self.client.get("/api/auth/me", headers=self._auth_headers(token))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["user"]["email"], "me@example.com")

    def test_market_research_requires_auth(self):
        response = self.client.post("/api/market-research", json={"prompt": "Apple"})
        self.assertEqual(response.status_code, 401)

    @patch("r2d2_backend.api.run_chain")
    def test_market_research_route_success(self, mock_run_chain):
        token = self._register_user()
        mock_run_chain.side_effect = ["Google, Microsoft", "Detailed analysis"]
        response = self.client.post(
            "/api/market-research",
            json={"prompt": "Apple"},
            headers=self._auth_headers(token),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["id"], "Apple")
        self.assertEqual(response.json["competitors"], "Google, Microsoft")
        self.assertEqual(response.json["analysis"], "Detailed analysis")
        self.assertEqual(response.json["analyze"], "Detailed analysis")
        self.assertIn("structured", response.json)
        self.assertEqual(mock_run_chain.call_count, 2)

    @patch("r2d2_backend.api.run_chain")
    def test_personalize_email_requires_prompt(self, mock_run_chain):
        token = self._register_user()
        mock_run_chain.return_value = "unused"
        response = self.client.post(
            "/api/personalize-email",
            json={},
            headers=self._auth_headers(token),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)

    @patch("r2d2_backend.api.run_chain")
    def test_personalize_email_success(self, mock_run_chain):
        token = self._register_user()
        mock_run_chain.return_value = "Improved email copy"
        response = self.client.post(
            "/api/personalize-email",
            json={"prompt": "Dear team, following up on the proposal."},
            headers=self._auth_headers(token),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"], "Improved email copy")
        self.assertIn("structured", response.json)
        self.assertEqual(response.json["structured"]["rewrittenBody"], "Improved email copy")
        self.assertIn("quality", response.json["structured"])
        self.assertIn("clarityScore", response.json["structured"]["quality"])

    @patch("r2d2_backend.api.run_chain")
    def test_crm_welcome_route_success(self, mock_run_chain):
        token = self._register_user()
        mock_run_chain.return_value = "Welcome message"
        response = self.client.post(
            "/api/crm",
            json={"customerName": "Jane", "productName": "R2D2"},
            headers=self._auth_headers(token),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"], "Welcome message")
        self.assertIn("structured", response.json)

    def test_crm_rejects_mixed_payload_shapes(self):
        token = self._register_user()
        response = self.client.post(
            "/api/crm",
            json={
                "customerName": "Jane",
                "productName": "R2D2",
                "prospectName": "Alex",
                "followUpReason": "Pricing",
                "note": "Met at conference",
            },
            headers=self._auth_headers(token),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)

    @patch("r2d2_backend.api.run_chain")
    def test_marketing_post_success(self, mock_run_chain):
        token = self._register_user()
        mock_run_chain.return_value = "Marketing post"
        response = self.client.post(
            "/api/marketing",
            json={
                "platform": "LinkedIn",
                "postObjective": "Drive signups",
                "postContent": "R2D2 product update",
            },
            headers=self._auth_headers(token),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"], "Marketing post")
        self.assertIn("structured", response.json)

    @patch("r2d2_backend.api.run_chain")
    def test_missing_openai_key_returns_503(self, mock_run_chain):
        token = self._register_user()
        mock_run_chain.side_effect = RuntimeError("OPENAI_API_KEY is not set.")
        response = self.client.post(
            "/api/market-research",
            json={"prompt": "Apple"},
            headers=self._auth_headers(token),
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["error"], "OPENAI_API_KEY is not set.")

    @patch("r2d2_backend.api.run_chain")
    def test_market_research_history_returns_only_current_user(self, mock_run_chain):
        token_user_1 = self._register_user(email="user1@example.com")
        token_user_2 = self._register_user(email="user2@example.com")

        mock_run_chain.side_effect = [
            "Competitors A",
            "Analysis A",
            "Competitors B",
            "Analysis B",
        ]

        response_user_1 = self.client.post(
            "/api/market-research",
            json={"prompt": "CompanyOne"},
            headers=self._auth_headers(token_user_1),
        )
        self.assertEqual(response_user_1.status_code, 200)

        response_user_2 = self.client.post(
            "/api/market-research",
            json={"prompt": "CompanyTwo"},
            headers=self._auth_headers(token_user_2),
        )
        self.assertEqual(response_user_2.status_code, 200)

        history_user_1 = self.client.get(
            "/api/market-research/history?limit=10",
            headers=self._auth_headers(token_user_1),
        )
        self.assertEqual(history_user_1.status_code, 200)
        self.assertEqual(len(history_user_1.json["data"]), 1)
        self.assertEqual(history_user_1.json["data"][0]["id"], "CompanyOne")

        history_user_2 = self.client.get(
            "/api/market-research/history?limit=10",
            headers=self._auth_headers(token_user_2),
        )
        self.assertEqual(history_user_2.status_code, 200)
        self.assertEqual(len(history_user_2.json["data"]), 1)
        self.assertEqual(history_user_2.json["data"][0]["id"], "CompanyTwo")

    @patch("r2d2_backend.api.run_chain")
    def test_history_supports_feature_filter(self, mock_run_chain):
        token = self._register_user()
        mock_run_chain.return_value = "Improved email copy"
        self.client.post(
            "/api/personalize-email",
            json={"prompt": "Follow up for proposal"},
            headers=self._auth_headers(token),
        )

        history_response = self.client.get(
            "/api/history?feature=personalize_email",
            headers=self._auth_headers(token),
        )
        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(len(history_response.json["data"]), 1)
        item = history_response.json["data"][0]
        self.assertEqual(item["feature"], "personalize_email")
        self.assertEqual(item["output"]["data"], "Improved email copy")

    def test_history_limit_validation(self):
        token = self._register_user()
        response = self.client.get(
            "/api/history?limit=invalid",
            headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)

    def test_sales_call_pipeline_requires_auth(self):
        response = self.client.post(
            "/api/sales-call-pipeline",
            json={"transcriptNotes": "Call notes"},
        )
        self.assertEqual(response.status_code, 401)

    @patch("r2d2_backend.api.run_chain")
    def test_sales_call_pipeline_success(self, mock_run_chain):
        token = self._register_user()
        mock_run_chain.return_value = """
SUMMARY:
The prospect likes the solution but needs internal sign-off.

OBJECTIONS:
- Budget approval is still pending.
- Team is concerned about onboarding timeline.

NEXT_ACTIONS:
- Send a phased implementation plan by Friday.
- Schedule a technical deep-dive with the IT lead.

FOLLOW_UP_EMAIL_1:
Hi Alex, thanks for your time today. I attached a phased implementation plan and can walk through it this week.

FOLLOW_UP_EMAIL_2:
Hi Alex, appreciate the discussion. Based on your priorities, I drafted a timeline and can review it with your IT lead.

FOLLOW_UP_EMAIL_3:
Hi Alex, great call today. I summarized next steps and can align on owners and dates in a quick follow-up meeting.
"""

        response = self.client.post(
            "/api/sales-call-pipeline",
            json={"transcriptNotes": "Prospect asked about onboarding and budget."},
            headers=self._auth_headers(token),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("structured", response.json)
        structured = response.json["structured"]
        self.assertIn("summary", structured)
        self.assertGreaterEqual(len(structured.get("objections", [])), 1)
        self.assertGreaterEqual(len(structured.get("nextActions", [])), 1)
        self.assertEqual(len(structured.get("followUpEmails", [])), 3)
        self.assertIn("quality", structured)
        self.assertIn("clarityScore", structured["quality"])
        self.assertIn("ctaPresent", structured["quality"])

    def test_sales_call_pipeline_export_formats(self):
        token = self._register_user()
        pipeline = {
            "summary": "Prospect is interested but wants pricing clarity.",
            "objections": ["Budget constraints", "Needs legal review"],
            "nextActions": ["Send pricing options", "Book legal walkthrough"],
            "followUpEmails": [
                "Hi team, sharing pricing options and next steps.",
                "Hi team, following up with legal review details.",
                "Hi team, can we schedule a 20-minute alignment call?",
            ],
            "quality": {
                "clarityScore": 92,
                "ctaPresent": True,
                "spamRiskWording": [],
                "sensitiveDataWarnings": [],
            },
        }

        expected_types = {
            "json": "application/json",
            "csv": "text/csv",
            "markdown": "text/markdown",
            "pdf": "application/pdf",
        }

        for export_format, expected_type in expected_types.items():
            response = self.client.post(
                "/api/sales-call-pipeline/export",
                json={"format": export_format, "pipeline": pipeline},
                headers=self._auth_headers(token),
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn(expected_type, response.content_type)
            self.assertIn("attachment;", response.headers.get("Content-Disposition", ""))
            self.assertGreater(len(response.data), 10)

    def test_sales_call_pipeline_export_rejects_invalid_pipeline_shape(self):
        token = self._register_user()
        invalid_pipeline = {
            "summary": "ok",
            "objections": "should be list",
            "nextActions": [],
            "followUpEmails": [],
            "quality": {},
        }

        response = self.client.post(
            "/api/sales-call-pipeline/export",
            json={"format": "json", "pipeline": invalid_pipeline},
            headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)
