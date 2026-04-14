#!/usr/bin/env python
"""Unit tests for publish_tarballs.py."""

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.fspath(Path(__file__).parent.parent.parent))

from github_actions.publish_tarballs import main


class TestPublishTarballsMain(unittest.TestCase):
    """Tests for the main() CLI entry point."""

    @mock.patch("_therock_utils.storage_backend.S3StorageBackend.copy_directory")
    def test_dev_linux_copies_from_artifacts_to_tarball_bucket(self, mock_copy):
        mock_copy.return_value = 2
        rc = main(
            [
                "--run-id",
                "123",
                "--platform",
                "linux",
                "--release-type",
                "dev",
                "--dry-run",
            ]
        )

        self.assertEqual(rc, 0)
        mock_copy.assert_called_once()
        source, dest = mock_copy.call_args.args[0], mock_copy.call_args.args[1]
        self.assertEqual(source.bucket, "therock-dev-artifacts")
        self.assertEqual(source.relative_path, "123-linux/tarballs")
        self.assertEqual(dest.bucket, "therock-dev-tarball")
        self.assertEqual(dest.relative_path, "v3")

    @mock.patch("_therock_utils.storage_backend.S3StorageBackend.copy_directory")
    def test_nightly_windows_copies_from_artifacts_to_tarball_bucket(self, mock_copy):
        mock_copy.return_value = 1
        main(
            [
                "--run-id",
                "99",
                "--platform",
                "windows",
                "--release-type",
                "nightly",
                "--dry-run",
            ]
        )

        source, dest = mock_copy.call_args.args[0], mock_copy.call_args.args[1]
        self.assertEqual(source.bucket, "therock-nightly-artifacts")
        self.assertEqual(source.relative_path, "99-windows/tarballs")
        self.assertEqual(dest.bucket, "therock-nightly-tarball")
        self.assertEqual(dest.relative_path, "v3")

    @mock.patch("_therock_utils.storage_backend.S3StorageBackend.copy_directory")
    def test_returns_nonzero_when_empty(self, mock_copy):
        mock_copy.return_value = 0
        rc = main(
            [
                "--run-id",
                "123",
                "--platform",
                "linux",
                "--release-type",
                "dev",
                "--dry-run",
            ]
        )
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
