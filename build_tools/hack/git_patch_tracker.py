#!/usr/bin/env python3
"""
Git Patch File History Tracker

This script traverses git history and counts .patch files in subdirectories
at each commit, outputting the data to a CSV file for analysis.
"""

import argparse
import subprocess
import csv
import os
import sys
from collections import defaultdict
from pathlib import Path


def run_git_command(command: list[str], repo_path: Path):
    """Runs a git command and return the output."""
    try:
        result = subprocess.run(
            command, cwd=repo_path, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {' '.join(command)}")
        print(f"Error: {e.stderr}")
        return None


def get_commit_history(repo_path: Path, start_commit="HEAD"):
    """Gets a list of commits from start_commit walking back through history."""
    command = ["git", "rev-list", "--first-parent", start_commit]
    output = run_git_command(command, repo_path)

    if output is None:
        return []

    return output.split("\n") if output else []


def get_commit_date(commit_hash: str, repo_path: Path):
    """Gets the commit date as 'YYYY-MM-DD HH:MM:SS' in the local timemzone."""
    command = [
        "git",
        "show",
        "--format=%ad",
        "--date=iso-local",
        "--no-patch",
        commit_hash,
    ]
    output = run_git_command(command, repo_path)

    if output is None:
        return None

    return output[:20]


def count_patch_files_at_commit(commit_hash, repo_path, target_dir):
    """Counts .patch files in subdirectories at a specific commit."""
    # Get list of all files at this commit under target_dir
    command = ["git", "ls-tree", "-r", "--name-only", commit_hash, target_dir]
    output = run_git_command(command, repo_path)

    if output is None:
        return {}

    files = output.split("\n") if output else []

    # Count .patch files by subdirectory
    patch_counts = defaultdict(int)

    for file_path in files:
        if file_path.endswith(".patch"):
            # Get the subdirectory relative to target_dir
            rel_path = os.path.relpath(file_path, target_dir)
            subdir = os.path.dirname(rel_path)

            # If file is directly in target_dir, use "." as subdirectory
            if subdir == "":
                subdir = "."

            patch_counts[subdir] += 1

    return dict(patch_counts)


def main():
    parser = argparse.ArgumentParser(
        description="Count .patch files in git history by subdirectory"
    )
    parser.add_argument(
        "root_dir",
        type=Path,
        help="Root directory path to analyze (relative to repo root)",
    )
    parser.add_argument(
        "--start-commit", default="HEAD", help="Starting commit (default: HEAD)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default="patch_history.csv",
        help="Output CSV file (default: patch_history.csv)",
    )
    parser.add_argument(
        "--repo-path",
        type=Path,
        default=".",
        help="Path to git repository (default: current directory)",
    )

    args = parser.parse_args()

    # Verify we're in a git repository
    if not (args.repo_path / ".git").exists():
        print(f"Error: {args.repo_path} does not appear to be a git repository")
        sys.exit(1)

    print(f"Analyzing patch files in '{args.root_dir}' from commit {args.start_commit}")
    print(f"Repository path: {args.repo_path}")

    # Get commit history
    commits = get_commit_history(args.repo_path, args.start_commit)

    if not commits:
        print("No commits found!")
        sys.exit(1)

    print(f"Found {len(commits)} commits to analyze")

    # Collect all unique subdirectories across all commits
    all_subdirs = set()
    commit_data = []

    print("Analyzing commits...")
    for i, commit_hash in enumerate(commits):
        if i % 50 == 0:  # Progress indicator
            print(f"  Progress: {i}/{len(commits)} commits")

        # Get commit date
        date_str = get_commit_date(commit_hash, args.repo_path)
        if date_str is None:
            continue

        # Count patch files
        patch_counts = count_patch_files_at_commit(
            commit_hash, args.repo_path, args.root_dir
        )

        # Track all subdirectories
        all_subdirs.update(patch_counts.keys())

        commit_data.append(
            {
                "commit": commit_hash,
                "date": date_str,
                "counts": patch_counts,
            }
        )

    # Flip to show older commits first and recent commits last
    commit_data.reverse()

    print(f"Analysis complete! Found {len(all_subdirs)} subdirectories")

    # Sort subdirectories for consistent column order
    sorted_subdirs = sorted(all_subdirs)

    # Write CSV
    print(f"Writing results to {args.output}")
    with open(args.output, "w", newline="", encoding="utf-8") as csvfile:
        # Create headers
        fieldnames = ["commit_hash", "date"] + sorted_subdirs
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()

        for commit_info in commit_data:
            row = {
                "commit_hash": commit_info["commit"],
                "date": commit_info["date"],
            }

            # Add counts for each subdirectory (0 if not present)
            for subdir in sorted_subdirs:
                row[subdir] = commit_info["counts"].get(subdir, 0)

            writer.writerow(row)

    print(f"Results written to {args.output}")
    print(f"Columns: commit info + {len(sorted_subdirs)} subdirectories")
    print("Subdirectories found:", ", ".join(sorted_subdirs))


if __name__ == "__main__":
    main()
