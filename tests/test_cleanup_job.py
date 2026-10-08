#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Fascode Network
# SPDX-License-Identifier: GPL-3.0-or-later

import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


MODULE_DIR = Path(__file__).parents[1] / "modules" / "cleanup"


def load_job(root, configuration):
    progress = []
    debug_messages = []
    warning_messages = []
    libcalamares = types.SimpleNamespace(
        globalstorage=types.SimpleNamespace(value=lambda key: str(root)),
        job=types.SimpleNamespace(
            configuration=configuration,
            setprogress=progress.append,
        ),
        utils=types.SimpleNamespace(
            debug=debug_messages.append,
            warning=warning_messages.append,
        ),
    )

    spec = importlib.util.spec_from_file_location(
        "cleanup_main_test", MODULE_DIR / "main.py"
    )
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(sys.modules, {"libcalamares": libcalamares}):
        with mock.patch.object(sys, "path", [str(MODULE_DIR), *sys.path]):
            spec.loader.exec_module(module)

    return module, progress, debug_messages, warning_messages


class CleanupJobTest(unittest.TestCase):
    def test_run_removes_paths_and_reports_progress(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            root = temporary / "target"
            config = temporary / "remove-files.conf"
            (root / "etc").mkdir(parents=True)
            (root / "etc/live-only").write_text("live\n", encoding="utf-8")
            config.write_text("/etc/live-only\n", encoding="utf-8")

            job, progress, debug_messages, warnings = load_job(
                root,
                {"removeFilesFile": str(config)},
            )

            self.assertIsNone(job.run())
            self.assertFalse((root / "etc/live-only").exists())
            self.assertEqual(progress, [1.0])
            self.assertEqual(
                debug_messages,
                ["Removed live-environment path /etc/live-only"],
            )
            self.assertEqual(warnings, [])

    def test_run_rejects_a_relative_configuration_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "target"
            root.mkdir()
            job, progress, debug_messages, warnings = load_job(
                root,
                {"removeFilesFile": "relative"},
            )

            result = job.run()

            self.assertEqual(
                result,
                (
                    "Target cleanup failed",
                    "removeFilesFile must be an absolute path.",
                ),
            )
            self.assertEqual(progress, [])
            self.assertEqual(debug_messages, [])
            self.assertEqual(
                warnings,
                ["removeFilesFile must be an absolute path."],
            )


if __name__ == "__main__":
    unittest.main()
