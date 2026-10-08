#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Fascode Network
# SPDX-License-Identifier: GPL-3.0-or-later

"""Cleanup helpers for explicitly-listed live-environment files."""

import os
import shutil


DEFAULT_CONFIG = "/etc/calamares/remove-files.conf"


def _configured_paths(config_path):
    """Return validated absolute target paths from *config_path*."""

    if not os.path.exists(config_path):
        return []

    paths = []
    with open(config_path, encoding="utf-8") as config:
        for line_number, line in enumerate(config, start=1):
            path = line.strip()
            if not path or path.startswith("#"):
                continue
            if (
                not path.startswith("/")
                or path.startswith("//")
                or path == "/"
                or "\0" in path
            ):
                raise ValueError(
                    f"{config_path}:{line_number}: expected a non-root absolute path"
                )
            if os.path.normpath(path) != path:
                raise ValueError(
                    f"{config_path}:{line_number}: path is not normalized: {path}"
                )
            paths.append(path)

    return paths


def remove_configured_paths(root, config_path=DEFAULT_CONFIG):
    """Remove configured paths below *root* and return those that existed."""

    target_root = os.path.realpath(root)
    if target_root == "/" or not os.path.isdir(target_root):
        raise ValueError(f"unsafe or missing target root: {root}")

    # Validate the complete input before removing anything. Resolving each
    # parent prevents an absolute or escaping symlink inside the target from
    # redirecting deletion to the live environment.
    configured = _configured_paths(config_path)
    targets = []
    for path in configured:
        target = os.path.normpath(os.path.join(target_root, path.lstrip("/")))
        parent = os.path.realpath(os.path.dirname(target))
        if (
            target == target_root
            or os.path.commonpath((target_root, target)) != target_root
            or os.path.commonpath((target_root, parent)) != target_root
        ):
            raise ValueError(f"path escapes target root: {path}")
        targets.append((path, target))

    removed = []
    for path, target in targets:
        if os.path.islink(target) or os.path.isfile(target):
            os.unlink(target)
        elif os.path.isdir(target):
            shutil.rmtree(target)
        elif os.path.lexists(target):
            os.unlink(target)
        else:
            continue

        if os.path.lexists(target):
            raise OSError(f"failed to remove target path: {path}")
        removed.append(path)

    return removed
