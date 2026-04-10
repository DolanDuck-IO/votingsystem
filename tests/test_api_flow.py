import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from haechi_voting.api import create_app


class ApiFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "voting.db"
        self.app = create_app(database_path=database_path)
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.client.close()
        self.temp_dir.cleanup()

    def test_end_to_end_api_flow(self) -> None:
        create_response = self.client.post(
            "/elections",
            json={
                "election_id": "api-demo",
                "title": "API Demo Election",
                "contests": [
                    {
                        "contest_id": "chair",
                        "title": "Chair",
                        "candidates": ["alice", "bob", "carol"],
                        "min_selections": 1,
                        "max_selections": 1,
                    },
                    {
                        "contest_id": "budget",
                        "title": "Budget",
                        "candidates": ["approve", "reject"],
                        "min_selections": 1,
                        "max_selections": 1,
                    },
                ],
            },
        )
        self.assertEqual(create_response.status_code, 200)

        prepared_a = self.client.post(
            "/elections/api-demo/ballots/prepare",
            json={"selections": {"chair": ["alice"], "budget": ["approve"]}},
        )
        self.assertEqual(prepared_a.status_code, 200)
        ballot_a = prepared_a.json()["ballot_id"]

        cast_a = self.client.post(f"/elections/api-demo/ballots/{ballot_a}/cast")
        self.assertEqual(cast_a.status_code, 200)
        self.assertEqual(cast_a.json()["status"], "cast")

        prepared_b = self.client.post(
            "/elections/api-demo/ballots/prepare",
            json={"selections": {"chair": ["bob"], "budget": ["reject"]}},
        )
        self.assertEqual(prepared_b.status_code, 200)
        ballot_b = prepared_b.json()["ballot_id"]

        challenged_b = self.client.post(f"/elections/api-demo/ballots/{ballot_b}/challenge")
        self.assertEqual(challenged_b.status_code, 200)
        self.assertEqual(challenged_b.json()["status"], "challenged")

        tally_response = self.client.post("/elections/api-demo/tally")
        self.assertEqual(tally_response.status_code, 200)
        self.assertEqual(tally_response.json()["cast_ballot_count"], 1)

        verify_response = self.client.get("/elections/api-demo/verify")
        self.assertEqual(verify_response.status_code, 200)
        self.assertTrue(verify_response.json()["success"])

        record_response = self.client.get("/elections/api-demo/record")
        self.assertEqual(record_response.status_code, 200)
        self.assertEqual(record_response.json()["cast_ballot_count"], 1)
        self.assertEqual(record_response.json()["challenged_ballot_count"], 1)

        logs_response = self.client.get("/elections/api-demo/audit-logs")
        self.assertEqual(logs_response.status_code, 200)
        self.assertGreaterEqual(len(logs_response.json()), 5)

    def test_frontend_route_serves_html(self) -> None:
        response = self.client.get("/app")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("VotingSystem", response.text)
        self.assertIn("value-modal", response.text)
        self.assertIn("管理员", response.text)
        self.assertIn("投票设备", response.text)
        self.assertIn("验证者", response.text)

        static_response = self.client.get("/static/app.js")
        self.assertEqual(static_response.status_code, 200)
        self.assertIn("javascript", static_response.headers["content-type"])

    def test_invalid_ballot_returns_400(self) -> None:
        self.client.post(
            "/elections",
            json={
                "election_id": "invalid-demo",
                "title": "Invalid Demo Election",
                "contests": [
                    {
                        "contest_id": "chair",
                        "title": "Chair",
                        "candidates": ["alice", "bob"],
                        "min_selections": 1,
                        "max_selections": 1,
                    }
                ],
            },
        )
        invalid_response = self.client.post(
            "/elections/invalid-demo/ballots/prepare",
            json={"selections": {"chair": ["mallory"]}},
        )
        self.assertEqual(invalid_response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
