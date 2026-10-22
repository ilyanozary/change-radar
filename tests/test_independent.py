"""Integration check against labels authored before first analyzer invocation."""

import json
import subprocess
import sys
import unittest
from pathlib import Path


class IndependentEvaluationTests(unittest.TestCase):
    def test_predeclared_fixture_labels_and_evidence(self):
        root = Path(__file__).resolve().parents[1]
        run = subprocess.run(
            [sys.executable, str(root / "scripts/evaluate_independent.py")],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        result = json.loads(run.stdout)
        self.assertEqual(set(result["scenarios"]), {"orders", "inheritance", "auth"})
        for name, scenario in result["scenarios"].items():
            with self.subTest(scenario=name):
                self.assertFalse(scenario["missed"])
                self.assertFalse(scenario["false_positive"])
                self.assertFalse(scenario["missing_edges"])
                self.assertFalse(scenario["unexpected_edges"])
                self.assertFalse(scenario["invalid_evidence"])
                self.assertFalse(scenario["missing_endpoints"])
