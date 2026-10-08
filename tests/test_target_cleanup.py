#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Fascode Network
# SPDX-License-Identifier: GPL-3.0-or-later

import importlib.util
import os
from pathlib import Path
import tempfile
import unittest


MODULE = (
    Path(__file__).parents[1]
    / "modules"
    / "cleanup"
    / "target_cleanup.py"
)
SPEC = importlib.util.spec_from_file_location("target_cleanup", MODULE)
target_cleanup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(target_cleanup)


class CleanupSafetyTest(unittest.TestCase):
    def test_removes_files_directories_and_symlinks_below_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            root = temporary / "target"
            outside = temporary / "outside"
            config = temporary / "remove-files.conf"

            (root / "etc/example").mkdir(parents=True)
            (root / "etc/example/config").write_text("live\n", encoding="utf-8")
            (root / "var/live/nested").mkdir(parents=True)
            (root / "var/live/nested/file").write_text("live\n", encoding="utf-8")
            outside.write_text("keep\n", encoding="utf-8")
            os.symlink(outside, root / "etc/example/link")
            config.write_text(
                "# live-only paths\n"
                "/etc/example/config\n"
                "/etc/example/link\n"
                "/var/live\n"
                "/missing\n",
                encoding="utf-8",
            )

            removed = target_cleanup.remove_configured_paths(root, config)

            self.assertEqual(
                removed,
                ["/etc/example/config", "/etc/example/link", "/var/live"],
            )
            self.assertEqual(outside.read_text(encoding="utf-8"), "keep\n")

    def test_rejects_invalid_input_before_removing_anything(self):
        invalid_paths = [
            "relative",
            "/",
            "//",
            "//etc/example",
            "/etc/../root",
            "/etc//example",
        ]
        for invalid in invalid_paths:
            with self.subTest(path=invalid), tempfile.TemporaryDirectory() as temporary:
                temporary = Path(temporary)
                root = temporary / "target"
                config = temporary / "remove-files.conf"
                (root / "keep").mkdir(parents=True)
                (root / "keep/file").write_text("keep\n", encoding="utf-8")
                config.write_text(f"/keep/file\n{invalid}\n", encoding="utf-8")

                with self.assertRaises(ValueError):
                    target_cleanup.remove_configured_paths(root, config)

                self.assertTrue((root / "keep/file").exists())

    def test_missing_configuration_is_a_noop(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "target"
            root.mkdir()
            self.assertEqual(
                target_cleanup.remove_configured_paths(root, root / "missing.conf"),
                [],
            )

    def test_rejects_a_parent_symlink_that_escapes_the_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            root = temporary / "target"
            outside = temporary / "outside"
            config = temporary / "remove-files.conf"

            (root / "safe").mkdir(parents=True)
            (root / "safe/file").write_text("keep\n", encoding="utf-8")
            outside.mkdir()
            (outside / "file").write_text("keep\n", encoding="utf-8")
            os.symlink(outside, root / "escape")
            config.write_text(
                "/safe/file\n/escape/file\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                target_cleanup.remove_configured_paths(root, config)

            self.assertTrue((root / "safe/file").exists())
            self.assertEqual(
                (outside / "file").read_text(encoding="utf-8"),
                "keep\n",
            )

    def test_refuses_to_use_the_host_root(self):
        with self.assertRaises(ValueError):
            target_cleanup.remove_configured_paths("/", "/does-not-exist")


if __name__ == "__main__":
    unittest.main()
