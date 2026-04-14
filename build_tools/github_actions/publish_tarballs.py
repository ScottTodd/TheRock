#!/usr/bin/env python3
# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: MIT

"""Publish tarballs from the artifacts bucket to the release tarball bucket.

Copies .tar.gz tarballs from the workflow run's artifacts bucket
(e.g. therock-dev-artifacts/{run_id}-linux/tarballs/) to the release
tarball bucket (e.g. therock-dev-tarball/v3/).

Example with ``--run-id 12345 --platform linux --release-type dev``:

    s3://therock-dev-artifacts/12345-linux/tarballs/therock-dist-linux-gfx94X-dcgpu-7.10.0.tar.gz
      -> s3://therock-dev-tarball/v3/therock-dist-linux-gfx94X-dcgpu-7.10.0.tar.gz

Usage:
    python build_tools/github_actions/publish_tarballs.py \\
        --run-id 12345 --platform linux --release-type dev --dry-run
"""

import argparse
import logging
import platform as platform_module
import sys
from pathlib import Path

_BUILD_TOOLS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BUILD_TOOLS_DIR))

from _therock_utils.s3_buckets import get_release_bucket_config
from _therock_utils.storage_backend import create_storage_backend
from _therock_utils.storage_location import StorageLocation
from _therock_utils.workflow_outputs import WorkflowOutputRoot

logger = logging.getLogger(__name__)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Publish tarballs to release bucket")
    parser.add_argument("--run-id", required=True, help="Source workflow run ID")
    parser.add_argument(
        "--platform",
        default=platform_module.system().lower(),
        choices=["linux", "windows"],
        help="Platform (default: current system)",
    )
    parser.add_argument(
        "--release-type",
        required=True,
        choices=["dev", "nightly", "prerelease"],
        help="Release type (determines source and destination buckets)",
    )
    parser.add_argument(
        "--s3-subdir",
        default="v3",
        help="Destination subdirectory in the tarball bucket (default: v3)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print plan without copying"
    )
    args = parser.parse_args(argv)

    # Lookup source workflow output folder, e.g.
    #   bucket: 'therock-dev-artifacts'
    #   relative_path: '12345-linux/tarballs'
    source = WorkflowOutputRoot.from_workflow_run(
        run_id=args.run_id, platform=args.platform, release_type=args.release_type
    ).tarballs()
    logger.info(f"Source: {source.s3_uri}")

    # Determine destination e.g. 'v3' subfolder in 'therock-dev-tarball' bucket.
    dest_bucket = get_release_bucket_config(args.release_type, "tarball")
    dest = StorageLocation(dest_bucket.name, relative_path=args.s3_subdir)
    logger.info(f"Destination: {dest.s3_uri}")

    # Copy from source to destination.
    backend = create_storage_backend(dry_run=args.dry_run)
    count = backend.copy_directory(source, dest, include=["*.tar.gz"])

    logger.info("Published %d tarballs", count)
    if count == 0:
        logger.warning("No tarballs found at source location")
    return 0 if count > 0 else 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sys.exit(main(sys.argv[1:]))
