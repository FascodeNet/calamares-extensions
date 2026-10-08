#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Fascode Network
# SPDX-License-Identifier: GPL-3.0-or-later

"""Calamares cleanup job for removing live-environment files."""

import os

import libcalamares

try:
    from .target_cleanup import DEFAULT_CONFIG, remove_configured_paths
except ImportError:
    from target_cleanup import DEFAULT_CONFIG, remove_configured_paths


def pretty_name():
    return "Remove live-environment files."


def run():
    """Remove configured paths after package removal has completed."""

    root = libcalamares.globalstorage.value("rootMountPoint")
    if not isinstance(root, str) or not root:
        message = "The target root mount point is missing."
        libcalamares.utils.warning(message)
        return ("Target cleanup failed", message)

    config_path = libcalamares.job.configuration.get(
        "removeFilesFile", DEFAULT_CONFIG
    )
    if not isinstance(config_path, str) or not os.path.isabs(config_path):
        message = "removeFilesFile must be an absolute path."
        libcalamares.utils.warning(message)
        return ("Target cleanup failed", message)

    try:
        removed = remove_configured_paths(root, config_path)
    except (OSError, ValueError) as error:
        message = "Could not clean the install target: {!s}".format(error)
        libcalamares.utils.warning(message)
        return ("Target cleanup failed", message)

    for path in removed:
        libcalamares.utils.debug(
            "Removed live-environment path {!s}".format(path)
        )

    libcalamares.job.setprogress(1.0)
    return None
