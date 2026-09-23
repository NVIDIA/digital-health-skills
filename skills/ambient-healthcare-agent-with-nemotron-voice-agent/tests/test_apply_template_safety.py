# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Safety checks for the Generic template applier."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"


def _load_applier():
    path = SCRIPTS_DIR / "apply_generic_agent_template.py"
    spec = importlib.util.spec_from_file_location("nva_template_applier", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


class DatabaseArtifactSafetyTests(unittest.TestCase):
    def test_existing_directory_is_merged_without_deleting_unrelated_files(self) -> None:
        applier = _load_applier()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            generic_dir = root / "nva" / "src" / "examples" / "generic"
            target = generic_dir / "ambient_healthcare_appointment_database"
            source.mkdir(parents=True)
            target.mkdir(parents=True)
            (source / "db.py").write_text("new\n", encoding="utf-8")
            (target / "db.py").write_text("old\n", encoding="utf-8")
            (target / "local-notes.txt").write_text("preserve\n", encoding="utf-8")

            result = applier._copy_database_artifacts(source, generic_dir)

            self.assertEqual(result, target)
            self.assertEqual((target / "db.py").read_text(encoding="utf-8"), "new\n")
            self.assertEqual(
                (target / "local-notes.txt").read_text(encoding="utf-8"),
                "preserve\n",
            )

    def test_symlinked_target_is_rejected_without_touching_destination(self) -> None:
        applier = _load_applier()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            generic_dir = root / "nva" / "src" / "examples" / "generic"
            outside = root / "outside"
            source.mkdir(parents=True)
            generic_dir.mkdir(parents=True)
            outside.mkdir()
            (source / "db.py").write_text("new\n", encoding="utf-8")
            sentinel = outside / "sentinel.txt"
            sentinel.write_text("unchanged\n", encoding="utf-8")
            target = generic_dir / "ambient_healthcare_appointment_database"
            target.symlink_to(outside, target_is_directory=True)

            with self.assertRaisesRegex(RuntimeError, "symlinked database target"):
                applier._copy_database_artifacts(source, generic_dir)

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "unchanged\n")
            self.assertFalse((outside / "db.py").exists())


if __name__ == "__main__":
    unittest.main()
