#!/usr/bin/env python3

"""Configures a CI workflow run given info about changed files, labels, etc."""

import fnmatch
import json
import os
import subprocess
import sys
from typing import Iterable, List, Mapping, Optional


# Paths matching any of these patterns are considered to have no influence over
# build or test workflows so any related jobs can be skipped if all paths
# modified by a commit/PR match a pattern in this list.
SKIPPABLE_PATH_PATTERNS = [
    "docs/*",
    "*.gitignore",
    "*.md",
    "*LICENSE",
]


def is_path_skippable(path: str) -> bool:
    """Determines if a given relative path to a file matches any skippable patterns."""
    return any(fnmatch.fnmatch(path, pattern) for pattern in SKIPPABLE_PATH_PATTERNS)


def modifies_non_skippable_paths(paths: Optional[Iterable[str]]) -> bool:
    """Returns true if not all modified paths are in the skippable set."""
    if paths is None:
        return True
    return any(not is_path_skippable(p) for p in paths)


def get_modified_paths(base_ref: str) -> Optional[Iterable[str]]:
    """Returns the paths of modified files relative to the base reference."""
    try:
        return subprocess.run(
            ["git", "diff", "--name-only", base_ref],
            stdout=subprocess.PIPE,
            check=True,
            text=True,
            timeout=60,
        ).stdout.splitlines()
    except TimeoutError as e:
        print(
            "Computing modified files timed out. Not using PR diff to determine"
            " jobs to run.",
            file=sys.stderr,
        )
        return None


def get_pr_labels() -> List[str]:
    """Gets a list of labels applied to a pull request."""
    labels = json.loads(os.environ.get("PR_LABELS", "[]"))
    return labels


def set_github_output(d: Mapping[str, str]):
    """Sets GITHUB_OUTPUT values.
    See https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/passing-information-between-jobs
    """
    print(f"Setting outputs: {d}")
    step_output_file = os.environ["GITHUB_OUTPUT"]
    with open(step_output_file, "a") as f:
        f.writelines(f"{k}={v}" + "\n" for k, v in d.items())


def write_job_summary(summary: str):
    """Appends a string to the GitHub Actions job summary.
    See https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#adding-a-job-summary
    """
    step_summary_file = os.environ["GITHUB_STEP_SUMMARY"]
    with open(step_summary_file, "a") as f:
        # Use double newlines to split sections in markdown.
        f.write(summary + "\n\n")


def main():
    is_pr = os.environ["GITHUB_EVENT_NAME"] == "pull_request"
    labels = get_pr_labels() if is_pr else []
    print("labels:", labels)
    base_ref = os.environ["BASE_REF"]

    try:
        modified_paths = get_modified_paths(base_ref)
        print("modified_paths:", modified_paths)

        run_ci = modifies_non_skippable_paths(modified_paths)
        print("run_ci:", run_ci)
    except ValueError as e:
        print(e)
        sys.exit(1)

    write_job_summary(
        f"""##Summary
      labels: {labels}
    """
    )

    output = {
        "run_ci": json.dumps(run_ci),
    }
    set_github_output(output)


if __name__ == "__main__":
    main()
