import unittest

from haechi_voting.demo import run_demo


class DemoFlowTest(unittest.TestCase):
    def test_demo_flow_verifies(self) -> None:
        result = run_demo()
        self.assertEqual(result["cast_ballots"], 2)
        self.assertEqual(result["challenged_ballots"], 1)
        self.assertTrue(result["verification"]["success"])


if __name__ == "__main__":
    unittest.main()
