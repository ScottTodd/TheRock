"""Utilities for working with GitHub Actions from Python.

See also https://pypi.org/project/github-action-utils/.
"""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Mapping
from urllib.request import urlopen, Request


def _log(*args, **kwargs):
    print(*args, **kwargs)
    sys.stdout.flush()


def gha_warn_if_not_running_on_ci():
    # https://docs.github.com/en/actions/reference/variables-reference
    if not os.getenv("CI"):
        _log("Warning: 'CI' env var not set, not running under GitHub Actions?")


def gha_add_to_path(new_path: str | Path):
    """Adds an entry to the system PATH for future GitHub Actions workflow run steps.

    This appends to the file located at the $GITHUB_PATH environment variable.

    See
      * https://docs.github.com/en/actions/reference/workflow-commands-for-github-actions#example-of-adding-a-system-path
    """
    _log(f"Adding to path by appending to $GITHUB_PATH:\n  '{new_path}'")

    path_file = os.getenv("GITHUB_PATH")
    if not path_file:
        _log("  Warning: GITHUB_PATH env var not set, can't add to path")
        return

    with open(path_file, "a") as f:
        f.write(str(new_path))


def gha_set_env(vars: Mapping[str, str | Path]):
    """Sets environment variables for future GitHub Actions workflow run steps.

    This appends to the file located at the $GITHUB_ENV environment variable.

    See
      * https://docs.github.com/en/actions/reference/workflow-commands-for-github-actions#environment-files
    """
    _log(f"Setting environment variable by appending to $GITHUB_ENV:\n  {vars}")

    env_file = os.getenv("GITHUB_ENV")
    if not env_file:
        _log("  Warning: GITHUB_ENV env var not set, can't set environment variable")
        return

    with open(env_file, "a") as f:
        f.writelines(f"{k}={str(v)}" + "\n" for k, v in vars.items())


def gha_set_output(vars: Mapping[str, str | Path]):
    """Sets values in a step's output parameters.

    This appends to the file located at the $GITHUB_OUTPUT environment variable.

    See
      * https://docs.github.com/en/actions/reference/workflow-commands-for-github-actions#setting-an-output-parameter
      * https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/passing-information-between-jobs
    """
    _log(f"Setting github output:\n{json.dumps(vars, indent=2)}")

    step_output_file = os.getenv("GITHUB_OUTPUT")
    if not step_output_file:
        _log("  Warning: GITHUB_OUTPUT env var not set, can't set github outputs")
        return

    with open(step_output_file, "a") as f:
        for k, v in vars.items():
            print(f"OUTPUT {k}={str(v)}")
            f.write(f"{k}={str(v)}\n")


def gha_append_step_summary(summary: str):
    """Appends a string to the GitHub Actions job summary.

    This appends to the file located at the $GITHUB_STEP_SUMMARY environment variable.

    See
      * https://docs.github.com/en/actions/reference/workflow-commands-for-github-actions#adding-a-job-summary
      * https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#adding-a-job-summary
    """
    _log(f"Writing job summary:\n{summary}")

    step_summary_file = os.getenv("GITHUB_STEP_SUMMARY")
    if not step_summary_file:
        _log("  Warning: GITHUB_STEP_SUMMARY env var not set, can't write job summary")
        return

    with open(step_summary_file, "a") as f:
        # Use double newlines to split sections in markdown.
        f.write(summary + "\n\n")


def gha_get_request_headers():
    """Gets common request heaers for use with the GitHub REST API.

    See https://docs.github.com/en/rest.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # If GITHUB_TOKEN environment variable is available, include it in the API
    # request to avoid a lower rate limit
    gh_token = os.getenv("GITHUB_TOKEN", "")
    if gh_token:
        headers["Authorization"] = f"Bearer {gh_token}"
    else:
        _log(f"Warning: GITHUB_TOKEN not set, requests may be rate limited")

    return headers


def gha_send_request(url: str) -> object:
    """Sents a request to the given GitHub REST API URL and returns the response if successful."""
    headers = gha_get_request_headers()

    _log(f"Sending request to URL: {url}")

    request = Request(url, headers=headers)
    with urlopen(request) as response:
        if response.status == 403:
            raise Exception(
                f"Access denied (403 Forbidden). "
                f"Check if your token has the necessary permissions (e.g., `repo`, `workflow`)."
            )
        elif response.status != 200:
            raise Exception(
                f"Received unexpected status code: {response.status}. Please verify the URL or check GitHub API status {response.status}."
            )

        return json.loads(response.read().decode("utf-8"))


def gha_query_workflow_run_by_id(github_repository: str, workflow_run_id: str) -> dict:
    """Gets metadata for a workflow run by its run ID.

    Uses the GitHub REST API endpoint: /actions/runs/{run_id}

    Args:
        github_repository: Repository in "owner/repo" format (e.g., "ROCm/TheRock")
        workflow_run_id: The workflow run ID (e.g., "12345678901")

    Returns:
        Workflow run metadata dict from GitHub API.

    See: https://docs.github.com/en/rest/actions/workflow-runs#get-a-workflow-run
    """
    url = f"https://api.github.com/repos/{github_repository}/actions/runs/{workflow_run_id}"
    return gha_send_request(url)


def gha_query_workflow_runs_for_commit(
    github_repository: str,
    workflow_file_name: str,
    git_commit_sha: str,
) -> list[dict]:
    """Gets all workflow runs for a specific commit.

    Uses the GitHub REST API endpoint: /actions/workflows/{workflow}/runs?head_sha={sha}

    A commit may have multiple workflow runs if the workflow was retriggered.
    The list is ordered by most recent first.

    Note: The API returns up to 30 results by default (first page only).
    For a single commit this is typically sufficient.

    Args:
        github_repository: Repository in "owner/repo" format (e.g., "ROCm/TheRock")
        workflow_file_name: Workflow filename (e.g., "ci.yml")
        git_commit_sha: Full git commit SHA

    Returns:
        List of workflow run metadata dicts, ordered most recent first.
        Empty list if no runs exist for this commit.

    See: https://docs.github.com/en/rest/actions/workflow-runs#list-workflow-runs-for-a-workflow
    """
    url = (
        f"https://api.github.com/repos/{github_repository}"
        f"/actions/workflows/{workflow_file_name}/runs?head_sha={git_commit_sha}"
    )
    response = gha_send_request(url)
    return response.get("workflow_runs", [])


def gha_query_last_successful_workflow_run(
    github_repository: str = "ROCm/TheRock",
    workflow_name: str = "ci.yml",
    branch: str = "main",
) -> dict | None:
    """Find the last successful run of a specific workflow on the specified branch.

    Args:
        github_repository: Repository in format "owner/repo"
        workflow_name: Name of the workflow file (e.g., "ci_nightly.yml")
        branch: Branch to filter by (defaults to "main")

    Returns:
        The full workflow run object of the most recent successful run on the specified branch,
        or None if no successful runs are found.
    """
    # Use GitHub API query parameters to pre-filter for successful runs on the specified branch
    url = f"https://api.github.com/repos/{github_repository}/actions/workflows/{workflow_name}/runs?status=success&branch={branch}&per_page=100"
    response = gha_send_request(url)

    # Return the first (most recent) successful run
    if response and response.get("workflow_runs"):
        return response["workflow_runs"][0]
    return None


def str2bool(value: str | None) -> bool:
    """Convert environment variables to boolean values."""
    if not value:
        return False
    if not isinstance(value, str):
        raise ValueError(
            f"Expected a string value for boolean conversion, got {type(value)}"
        )
    value = value.strip().lower()
    if value in (
        "1",
        "true",
        "t",
        "yes",
        "y",
        "on",
        "enable",
        "enabled",
        "found",
    ):
        return True
    if value in (
        "0",
        "false",
        "f",
        "no",
        "n",
        "off",
        "disable",
        "disabled",
        "notfound",
        "none",
        "null",
        "nil",
        "undefined",
        "n/a",
    ):
        return False
    raise ValueError(f"Invalid string value for boolean conversion: {value}")


def get_visible_gpu_count(env=None, therock_bin_dir: str | None = None) -> int:
    rocminfo = Path(therock_bin_dir) / "rocminfo"
    rocminfo_cmd = str(rocminfo) if rocminfo.exists() else "rocminfo"

    result = subprocess.run(
        [rocminfo_cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        check=False,
    )

    pattern = re.compile(r"^\s*Name:\s+gfx[0-9a-z]+$", re.IGNORECASE)

    return sum(1 for line in result.stdout.splitlines() if pattern.match(line.strip()))
