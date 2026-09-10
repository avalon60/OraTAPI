# Author: cbostock / DGGIU
# Created: 10-Sep-2026
# Verify CLI help and startup with an isolated profile configuration.

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class CliHelpTests(unittest.TestCase):
    def test_help_without_active_profile(self):
        for flag in ("--help", "-h"):
            with self.subTest(flag=flag), tempfile.TemporaryDirectory() as home:
                result = self.run_cli(home, flag)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertIn("Oracle Table API Generator", result.stdout)
                self.assertIn("--conn_name", result.stdout)
                self.assertTrue(result.stdout.rstrip().endswith(
                    "WARNING: No active OraTAPI profile is configured. "
                    "Run quick_config, or use profile_mgr to activate a profile."
                ))
                self.assertFalse((Path(home) / "OraTAPI").exists())

    def test_startup_without_active_profile(self):
        with tempfile.TemporaryDirectory() as home:
            result = self.run_cli(home)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stderr, "")
            self.assertIn("ERROR: No active OraTAPI profile is configured.", result.stdout)

    def test_help_with_active_profile(self):
        with tempfile.TemporaryDirectory() as home:
            config_dir = Path(home) / "OraTAPI" / "configs" / "basic" / "resources" / "config"
            config_dir.mkdir(parents=True)
            config_path = (Path(__file__).resolve().parents[1] / "src" / "oratapi"
                           / "ora_tapi_package_data" / "resources" / "config" / "OraTAPI.ini")
            config = config_path.read_text()
            (config_dir / "OraTAPI.ini").write_text(config)
            (Path(home) / "OraTAPI" / "active_config").write_text("basic")
            result = self.run_cli(home, "--help")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            self.assertIn("Oracle Table API Generator", result.stdout)
            self.assertNotIn("WARNING:", result.stdout)

    @staticmethod
    def run_cli(home, *args):
        env = os.environ.copy()
        env["HOME"] = home
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
        return subprocess.run(
            [sys.executable, "-m", "oratapi.controller.ora_tapi", *args],
            env=env, capture_output=True, text=True, check=False,
        )
