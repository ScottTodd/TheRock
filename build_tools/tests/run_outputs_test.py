#!/usr/bin/env python
"""Unit tests for run_outputs.py (RunOutputRoot)."""

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.fspath(Path(__file__).parent.parent))

from _therock_utils.run_outputs import RunOutputRoot


class TestRunOutputRootProperties(unittest.TestCase):
    """Tests for RunOutputRoot basic properties."""

    def test_prefix_without_external_repo(self):
        """Test prefix for main ROCm/TheRock repo (no external_repo)."""
        root = RunOutputRoot(
            bucket="therock-ci-artifacts",
            external_repo="",
            run_id="12345678901",
            platform="linux",
        )
        self.assertEqual(root.prefix, "12345678901-linux")

    def test_prefix_with_external_repo(self):
        """Test prefix for external/fork repos."""
        root = RunOutputRoot(
            bucket="therock-ci-artifacts-external",
            external_repo="ROCm-TheRock/",
            run_id="12345678901",
            platform="linux",
        )
        self.assertEqual(root.prefix, "ROCm-TheRock/12345678901-linux")

    def test_s3_uri(self):
        """Test S3 URI construction."""
        root = RunOutputRoot(
            bucket="therock-ci-artifacts",
            external_repo="",
            run_id="12345678901",
            platform="linux",
        )
        self.assertEqual(root.s3_uri, "s3://therock-ci-artifacts/12345678901-linux")

    def test_s3_uri_with_external_repo(self):
        """Test S3 URI with external repo prefix."""
        root = RunOutputRoot(
            bucket="therock-ci-artifacts-external",
            external_repo="ROCm-TheRock/",
            run_id="12345678901",
            platform="windows",
        )
        self.assertEqual(
            root.s3_uri,
            "s3://therock-ci-artifacts-external/ROCm-TheRock/12345678901-windows",
        )

    def test_https_url(self):
        """Test HTTPS URL construction."""
        root = RunOutputRoot(
            bucket="therock-ci-artifacts",
            external_repo="",
            run_id="12345678901",
            platform="linux",
        )
        self.assertEqual(
            root.https_url,
            "https://therock-ci-artifacts.s3.amazonaws.com/12345678901-linux",
        )

    def test_local_path(self):
        """Test local path construction."""
        root = RunOutputRoot(
            bucket="local",
            external_repo="",
            run_id="local-123",
            platform="linux",
        )
        staging_dir = Path("/tmp/staging")
        expected = staging_dir / "local-123-linux"
        self.assertEqual(root.local_path(staging_dir), expected)

    def test_local_path_with_external_repo(self):
        """Test local path with external repo prefix."""
        root = RunOutputRoot(
            bucket="local",
            external_repo="ROCm-TheRock/",
            run_id="12345",
            platform="windows",
        )
        staging_dir = Path("/tmp/staging")
        expected = staging_dir / "ROCm-TheRock" / "12345-windows"
        self.assertEqual(root.local_path(staging_dir), expected)


class TestRunOutputRootArtifactPaths(unittest.TestCase):
    """Tests for artifact-related path methods."""

    def setUp(self):
        self.root = RunOutputRoot(
            bucket="therock-ci-artifacts",
            external_repo="",
            run_id="12345678901",
            platform="linux",
        )

    def test_artifact_s3_key(self):
        """Test S3 key for artifact file."""
        key = self.root.artifact_s3_key("blas_lib_gfx94X.tar.xz")
        self.assertEqual(key, "12345678901-linux/blas_lib_gfx94X.tar.xz")

    def test_artifact_s3_uri(self):
        """Test S3 URI for artifact file."""
        uri = self.root.artifact_s3_uri("blas_lib_gfx94X.tar.xz")
        self.assertEqual(
            uri, "s3://therock-ci-artifacts/12345678901-linux/blas_lib_gfx94X.tar.xz"
        )

    def test_artifact_https_url(self):
        """Test HTTPS URL for artifact file."""
        url = self.root.artifact_https_url("blas_lib_gfx94X.tar.xz")
        self.assertEqual(
            url,
            "https://therock-ci-artifacts.s3.amazonaws.com/12345678901-linux/blas_lib_gfx94X.tar.xz",
        )

    def test_artifact_index_s3_key(self):
        """Test S3 key for artifact index file."""
        key = self.root.artifact_index_s3_key("gfx94X-dcgpu")
        self.assertEqual(key, "12345678901-linux/index-gfx94X-dcgpu.html")

    def test_artifact_index_s3_uri(self):
        """Test S3 URI for artifact index file."""
        uri = self.root.artifact_index_s3_uri("gfx94X-dcgpu")
        self.assertEqual(
            uri, "s3://therock-ci-artifacts/12345678901-linux/index-gfx94X-dcgpu.html"
        )

    def test_artifact_index_url(self):
        """Test HTTPS URL for artifact index file."""
        url = self.root.artifact_index_url("gfx94X-dcgpu")
        self.assertEqual(
            url,
            "https://therock-ci-artifacts.s3.amazonaws.com/12345678901-linux/index-gfx94X-dcgpu.html",
        )


class TestRunOutputRootLogPaths(unittest.TestCase):
    """Tests for log-related path methods."""

    def setUp(self):
        self.root = RunOutputRoot(
            bucket="therock-ci-artifacts",
            external_repo="",
            run_id="12345678901",
            platform="linux",
        )

    def test_logs_prefix(self):
        """Test S3 prefix for logs directory."""
        prefix = self.root.logs_prefix("gfx94X-dcgpu")
        self.assertEqual(prefix, "12345678901-linux/logs/gfx94X-dcgpu")

    def test_logs_s3_uri(self):
        """Test S3 URI for logs directory."""
        uri = self.root.logs_s3_uri("gfx94X-dcgpu")
        self.assertEqual(
            uri, "s3://therock-ci-artifacts/12345678901-linux/logs/gfx94X-dcgpu"
        )

    def test_logs_https_url(self):
        """Test HTTPS URL for logs directory."""
        url = self.root.logs_https_url("gfx94X-dcgpu")
        self.assertEqual(
            url,
            "https://therock-ci-artifacts.s3.amazonaws.com/12345678901-linux/logs/gfx94X-dcgpu",
        )

    def test_log_file_s3_key(self):
        """Test S3 key for a specific log file."""
        key = self.root.log_file_s3_key("gfx94X-dcgpu", "build.log")
        self.assertEqual(key, "12345678901-linux/logs/gfx94X-dcgpu/build.log")

    def test_log_index_url(self):
        """Test HTTPS URL for log index."""
        url = self.root.log_index_url("gfx94X-dcgpu")
        self.assertEqual(
            url,
            "https://therock-ci-artifacts.s3.amazonaws.com/12345678901-linux/logs/gfx94X-dcgpu/index.html",
        )

    def test_build_time_analysis_url(self):
        """Test HTTPS URL for build time analysis."""
        url = self.root.build_time_analysis_url("gfx94X-dcgpu")
        self.assertEqual(
            url,
            "https://therock-ci-artifacts.s3.amazonaws.com/12345678901-linux/logs/gfx94X-dcgpu/build_time_analysis.html",
        )


class TestRunOutputRootManifestPaths(unittest.TestCase):
    """Tests for manifest-related path methods."""

    def setUp(self):
        self.root = RunOutputRoot(
            bucket="therock-ci-artifacts",
            external_repo="",
            run_id="12345678901",
            platform="linux",
        )

    def test_manifests_prefix(self):
        """Test S3 prefix for manifests directory."""
        prefix = self.root.manifests_prefix("gfx94X-dcgpu")
        self.assertEqual(prefix, "12345678901-linux/manifests/gfx94X-dcgpu")

    def test_manifest_s3_key(self):
        """Test S3 key for manifest file."""
        key = self.root.manifest_s3_key("gfx94X-dcgpu")
        self.assertEqual(
            key, "12345678901-linux/manifests/gfx94X-dcgpu/therock_manifest.json"
        )

    def test_manifest_s3_uri(self):
        """Test S3 URI for manifest file."""
        uri = self.root.manifest_s3_uri("gfx94X-dcgpu")
        self.assertEqual(
            uri,
            "s3://therock-ci-artifacts/12345678901-linux/manifests/gfx94X-dcgpu/therock_manifest.json",
        )

    def test_manifest_url(self):
        """Test HTTPS URL for manifest file."""
        url = self.root.manifest_url("gfx94X-dcgpu")
        self.assertEqual(
            url,
            "https://therock-ci-artifacts.s3.amazonaws.com/12345678901-linux/manifests/gfx94X-dcgpu/therock_manifest.json",
        )


class TestRunOutputRootFuturePaths(unittest.TestCase):
    """Tests for future output types (python packages, native packages, reports)."""

    def setUp(self):
        self.root = RunOutputRoot(
            bucket="therock-ci-artifacts",
            external_repo="",
            run_id="12345678901",
            platform="linux",
        )

    def test_python_prefix(self):
        """Test S3 prefix for Python packages."""
        prefix = self.root.python_prefix("gfx94X-dcgpu")
        self.assertEqual(prefix, "12345678901-linux/python/gfx94X-dcgpu")

    def test_python_s3_uri(self):
        """Test S3 URI for Python packages directory."""
        uri = self.root.python_s3_uri("gfx94X-dcgpu")
        self.assertEqual(
            uri, "s3://therock-ci-artifacts/12345678901-linux/python/gfx94X-dcgpu"
        )

    def test_python_package_s3_key(self):
        """Test S3 key for a Python package file."""
        key = self.root.python_package_s3_key("gfx94X-dcgpu", "rocm_sdk-1.0.0.whl")
        self.assertEqual(
            key, "12345678901-linux/python/gfx94X-dcgpu/rocm_sdk-1.0.0.whl"
        )

    def test_packages_prefix(self):
        """Test S3 prefix for native packages."""
        prefix = self.root.packages_prefix("gfx94X-dcgpu")
        self.assertEqual(prefix, "12345678901-linux/packages/gfx94X-dcgpu")

    def test_packages_s3_uri(self):
        """Test S3 URI for native packages directory."""
        uri = self.root.packages_s3_uri("gfx94X-dcgpu")
        self.assertEqual(
            uri, "s3://therock-ci-artifacts/12345678901-linux/packages/gfx94X-dcgpu"
        )

    def test_native_package_s3_key(self):
        """Test S3 key for a native package file."""
        key = self.root.native_package_s3_key("gfx94X-dcgpu", "rocm-sdk_1.0.0.deb")
        self.assertEqual(
            key, "12345678901-linux/packages/gfx94X-dcgpu/rocm-sdk_1.0.0.deb"
        )

    def test_reports_prefix(self):
        """Test S3 prefix for reports."""
        prefix = self.root.reports_prefix("gfx94X-dcgpu")
        self.assertEqual(prefix, "12345678901-linux/reports/gfx94X-dcgpu")

    def test_reports_s3_uri(self):
        """Test S3 URI for reports directory."""
        uri = self.root.reports_s3_uri("gfx94X-dcgpu")
        self.assertEqual(
            uri, "s3://therock-ci-artifacts/12345678901-linux/reports/gfx94X-dcgpu"
        )

    def test_report_s3_key(self):
        """Test S3 key for a report file."""
        key = self.root.report_s3_key("gfx94X-dcgpu", "test_results.html")
        self.assertEqual(
            key, "12345678901-linux/reports/gfx94X-dcgpu/test_results.html"
        )

    def test_report_url(self):
        """Test HTTPS URL for a report file."""
        url = self.root.report_url("gfx94X-dcgpu", "test_results.html")
        self.assertEqual(
            url,
            "https://therock-ci-artifacts.s3.amazonaws.com/12345678901-linux/reports/gfx94X-dcgpu/test_results.html",
        )


class TestRunOutputRootFactoryMethods(unittest.TestCase):
    """Tests for RunOutputRoot factory methods."""

    def test_for_local_default_platform(self):
        """Test for_local with default platform detection."""
        root = RunOutputRoot.for_local(run_id="test-123")
        self.assertEqual(root.bucket, "local")
        self.assertEqual(root.external_repo, "")
        self.assertEqual(root.run_id, "test-123")
        # Platform should be detected from system
        self.assertIn(root.platform, ["linux", "windows", "darwin"])

    def test_for_local_explicit_platform(self):
        """Test for_local with explicit platform."""
        root = RunOutputRoot.for_local(run_id="test-456", platform="windows")
        self.assertEqual(root.run_id, "test-456")
        self.assertEqual(root.platform, "windows")
        self.assertEqual(root.prefix, "test-456-windows")

    def test_for_local_custom_bucket(self):
        """Test for_local with custom bucket name."""
        root = RunOutputRoot.for_local(
            run_id="test-789", platform="linux", bucket="custom-bucket"
        )
        self.assertEqual(root.bucket, "custom-bucket")

    @mock.patch("_therock_utils.run_outputs.retrieve_bucket_info")
    def test_from_workflow_run_main_repo(self, mock_retrieve):
        """Test from_workflow_run for main ROCm/TheRock repo."""
        mock_retrieve.return_value = ("", "therock-ci-artifacts")

        root = RunOutputRoot.from_workflow_run(run_id="12345678901", platform="linux")

        self.assertEqual(root.bucket, "therock-ci-artifacts")
        self.assertEqual(root.external_repo, "")
        self.assertEqual(root.run_id, "12345678901")
        self.assertEqual(root.platform, "linux")
        self.assertEqual(root.prefix, "12345678901-linux")

    @mock.patch("_therock_utils.run_outputs.retrieve_bucket_info")
    def test_from_workflow_run_fork(self, mock_retrieve):
        """Test from_workflow_run for fork/external repo."""
        mock_retrieve.return_value = ("MyOrg-TheRock/", "therock-ci-artifacts-external")

        root = RunOutputRoot.from_workflow_run(run_id="12345678901", platform="windows")

        self.assertEqual(root.bucket, "therock-ci-artifacts-external")
        self.assertEqual(root.external_repo, "MyOrg-TheRock/")
        self.assertEqual(root.prefix, "MyOrg-TheRock/12345678901-windows")

    @mock.patch("_therock_utils.run_outputs.retrieve_bucket_info")
    def test_from_workflow_run_with_github_repository(self, mock_retrieve):
        """Test from_workflow_run passes github_repository to retrieve_bucket_info."""
        mock_retrieve.return_value = ("", "therock-ci-artifacts")

        RunOutputRoot.from_workflow_run(
            run_id="123", platform="linux", github_repository="ROCm/TheRock"
        )

        mock_retrieve.assert_called_once_with(
            github_repository="ROCm/TheRock", workflow_run=None
        )

    @mock.patch("_therock_utils.run_outputs.retrieve_bucket_info")
    def test_from_workflow_run_with_workflow_run_dict(self, mock_retrieve):
        """Test from_workflow_run passes workflow_run dict to retrieve_bucket_info."""
        mock_retrieve.return_value = ("", "therock-ci-artifacts")
        workflow_run = {"id": 123, "repository": {"full_name": "ROCm/TheRock"}}

        RunOutputRoot.from_workflow_run(
            run_id="123", platform="linux", workflow_run=workflow_run
        )

        mock_retrieve.assert_called_once_with(
            github_repository=None, workflow_run=workflow_run
        )


class TestRunOutputRootImmutability(unittest.TestCase):
    """Tests that RunOutputRoot is immutable (frozen dataclass)."""

    def test_cannot_modify_bucket(self):
        """Test that bucket cannot be modified after creation."""
        root = RunOutputRoot(
            bucket="original",
            external_repo="",
            run_id="123",
            platform="linux",
        )
        with self.assertRaises(AttributeError):
            root.bucket = "modified"

    def test_cannot_modify_run_id(self):
        """Test that run_id cannot be modified after creation."""
        root = RunOutputRoot(
            bucket="bucket",
            external_repo="",
            run_id="original",
            platform="linux",
        )
        with self.assertRaises(AttributeError):
            root.run_id = "modified"


if __name__ == "__main__":
    unittest.main()
