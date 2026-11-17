#!/usr/bin/env python3
"""
Deterministic Unit Test Suite for NulKast ChromeOS Studio (`tests/test_chromeos_toolkit.py`).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts import chromeos_toolkit


class ChromeOsToolkitTestSuite(unittest.TestCase):
    def test_01_classify_nocturne_firmware_string(self) -> None:
        info = chromeos_toolkit.classify_board("Google_Nocturne.10984.90.0")
        self.assertTrue(info["known"])
        self.assertEqual(info["board"], "nocturne")
        self.assertEqual(info["arch"], "x86_64")
        self.assertTrue(info["mrchromebox_rw_legacy"])

    def test_02_generate_custom_chromeos_script_and_play_store_safety(self) -> None:
        res = chromeos_toolkit.generate_custom_chromeos_script(lock_updates=True)
        self.assertTrue(res["ok"])
        script_text = Path(res["script_path"]).read_text(encoding="utf-8")

        # Verify kernel turbo flags
        self.assertIn("kvm-intel.vmentry_l1d_flush=never", script_text)
        self.assertIn("mitigations=off", script_text)

        # Verify GPU & compositor flags
        self.assertIn("--enable-gpu-rasterization", script_text)
        self.assertIn("--enable-zero-copy", script_text)
        self.assertIn("--ash-disable-blur", script_text)

        # Verify tracker domains blocked while Play Store domains are preserved
        self.assertIn("0.0.0.0 uma.google.com", script_text)
        self.assertIn("0.0.0.0 graph.facebook.com", script_text)
        for preserved in chromeos_toolkit.PLAY_STORE_PRESERVED_DOMAINS:
            self.assertNotIn(f"0.0.0.0 {preserved}", script_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
