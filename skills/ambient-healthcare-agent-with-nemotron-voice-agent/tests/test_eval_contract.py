# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Self-contained contract checks discovered by SkillEvaluator."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]


def _load_grader():
    path = SKILL_DIR / "evals" / "grader.py"
    spec = importlib.util.spec_from_file_location("nva_eval_grader", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EvalContractTests(unittest.TestCase):
    def test_documented_welcome_matches_grader(self) -> None:
        grader = _load_grader()
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        section = skill_text.split("## Required Welcome", 1)[1]
        documented = section.split("```text", 1)[1].split("```", 1)[0].strip()
        self.assertEqual(documented, grader.WELCOME)

    def test_eval_dataset_has_three_unique_smoke_cases(self) -> None:
        dataset = json.loads((SKILL_DIR / "evals" / "evals.json").read_text(encoding="utf-8"))
        cases = dataset["evals"]
        self.assertEqual(dataset["skill_name"], "ambient-healthcare-agent-with-nemotron-voice-agent")
        self.assertEqual(len(cases), 3)
        self.assertEqual(len({case["id"] for case in cases}), 3)
        self.assertEqual(sum(case.get("expected_skill") is None for case in cases), 1)

    def test_welcome_grader_allows_only_target_skill_loader(self) -> None:
        grader = _load_grader()
        entry = {"id": "nva-ambient-explicit-welcome"}
        loader = {
            "function_name": "Skill",
            "arguments": {"skill": grader.TARGET_SKILL},
        }
        trajectory = {
            "steps": [
                {"source": "agent", "tool_calls": [loader]},
                {"source": "agent", "message": grader.WELCOME},
            ]
        }
        self.assertEqual(grader.grade(entry, trajectory)[0], 1.0)

        trajectory["steps"][0]["tool_calls"].append(
            {"function_name": "Bash", "arguments": {"command": "pwd"}}
        )
        self.assertEqual(grader.grade(entry, trajectory)[0], 0.5)


if __name__ == "__main__":
    unittest.main()
