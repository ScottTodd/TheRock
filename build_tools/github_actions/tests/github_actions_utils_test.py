import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, os.fspath(Path(__file__).parent.parent))
from github_actions_utils import (
    gha_query_workflow_run_by_id,
    gha_query_workflow_runs_for_commit,
    gha_query_last_successful_workflow_run,
)

# Note: these tests use the network and require GITHUB_TOKEN to avoid rate limits.


class GitHubActionsUtilsTest(unittest.TestCase):
    @unittest.skipUnless(
        os.getenv("GITHUB_TOKEN"),
        "GITHUB_TOKEN not set, skipping test that requires GitHub API access",
    )
    def test_gha_query_workflow_run_by_id(self):
        """Test querying a workflow run by its ID."""
        workflow_run = gha_query_workflow_run_by_id("ROCm/TheRock", "18022609292")
        self.assertEqual(workflow_run["repository"]["full_name"], "ROCm/TheRock")

        # Verify fields we depend on in RunOutputRoot and find_artifacts_for_commit
        self.assertIn("id", workflow_run)
        self.assertIn("head_repository", workflow_run)
        self.assertIn("full_name", workflow_run["head_repository"])
        self.assertIn("updated_at", workflow_run)
        self.assertIn("status", workflow_run)
        self.assertIn("html_url", workflow_run)

    @unittest.skipUnless(
        os.getenv("GITHUB_TOKEN"),
        "GITHUB_TOKEN not set, skipping test that requires GitHub API access",
    )
    def test_gha_query_workflow_run_by_id_not_found(self):
        """Test querying a workflow run by its ID where the ID is not found."""
        with self.assertRaises(Exception):
            gha_query_workflow_run_by_id("ROCm/TheRock", "00000000000")

    @unittest.skipUnless(
        os.getenv("GITHUB_TOKEN"),
        "GITHUB_TOKEN not set, skipping test that requires GitHub API access",
    )
    def test_gha_query_workflow_runs_for_commit_found(self):
        """Test querying workflow runs for a commit that has runs."""
        # https://github.com/ROCm/TheRock/commit/77f0cb2112d1d0aaae0de6088a6e4337f2488233
        runs = gha_query_workflow_runs_for_commit(
            "ROCm/TheRock", "ci.yml", "77f0cb2112d1d0aaae0de6088a6e4337f2488233"
        )
        self.assertIsInstance(runs, list)
        self.assertGreater(len(runs), 0)

        # Verify fields we depend on in RunOutputRoot and find_artifacts_for_commit
        run = runs[0]
        self.assertIn("id", run)
        self.assertIn("head_repository", run)
        self.assertIn("full_name", run["head_repository"])
        self.assertIn("updated_at", run)
        self.assertIn("status", run)
        self.assertIn("html_url", run)

    @unittest.skipUnless(
        os.getenv("GITHUB_TOKEN"),
        "GITHUB_TOKEN not set, skipping test that requires GitHub API access",
    )
    def test_gha_query_workflow_runs_for_commit_not_found(self):
        """Test querying workflow runs for a commit with no runs returns empty list."""
        runs = gha_query_workflow_runs_for_commit(
            "ROCm/TheRock", "ci.yml", "0000000000000000000000000000000000000000"
        )
        self.assertIsInstance(runs, list)
        self.assertEqual(len(runs), 0)

    @unittest.skipUnless(
        os.getenv("GITHUB_TOKEN"),
        "GITHUB_TOKEN not set, skipping test that requires GitHub API access",
    )
    def test_gha_query_last_successful_workflow_run(self):
        """Test querying for the last successful workflow run on a branch."""
        # Test successful run found on main branch
        result = gha_query_last_successful_workflow_run(
            "ROCm/TheRock", "ci_nightly.yml", "main"
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["head_branch"], "main")
        self.assertEqual(result["conclusion"], "success")
        self.assertIn("id", result)

        # Test no matching branch - should return None
        result = gha_query_last_successful_workflow_run(
            "ROCm/TheRock", "ci_nightly.yml", "nonexistent-branch-12345"
        )
        self.assertIsNone(result)

        # Test non-existent workflow - should raise an exception
        with self.assertRaises(Exception):
            gha_query_last_successful_workflow_run(
                "ROCm/TheRock", "nonexistent_workflow_12345.yml", "main"
            )


if __name__ == "__main__":
    unittest.main()
