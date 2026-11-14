import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class AddonImportTests(unittest.TestCase):
    def test_imported_addon_function_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "math.rpa").write_text(
                "fn twice(value: Int) -> Int { return value + value }\n",
                encoding="utf-8",
            )
            (root / "main.rp").write_text(
                "import math.rpa\nprintln(math.twice(21))\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "-m", "rplus", str(root / "main.rp")],
                cwd=Path(__file__).parents[1],
                env={**os.environ, "PYTHONPATH": str(Path(__file__).parents[1])},
                capture_output=True,
                text=True,
                check=True,
            )
        self.assertEqual(result.stdout, "42\n")

    def test_addon_can_import_another_addon(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "base.rpa").write_text(
                "fn add_one(value: Int) -> Int { return value + 1 }\n",
                encoding="utf-8",
            )
            (root / "wrapper.rpa").write_text(
                "import base.rpa\nfn answer() -> Int { return base.add_one(41) }\n",
                encoding="utf-8",
            )
            (root / "main.rp").write_text(
                "import wrapper.rpa\nprintln(wrapper.answer())\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "-m", "rplus", str(root / "main.rp")],
                cwd=Path(__file__).parents[1],
                env={**os.environ, "PYTHONPATH": str(Path(__file__).parents[1])},
                capture_output=True,
                text=True,
                check=True,
            )
        self.assertEqual(result.stdout, "42\n")


if __name__ == "__main__":
    unittest.main()
