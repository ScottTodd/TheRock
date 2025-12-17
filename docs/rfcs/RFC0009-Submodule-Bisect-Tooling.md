# RFC0009: ROCm Submodule Bisect Tooling

- **Author:** Claude (AI Assistant)
- **Created:** 2025-12-17
- **Modified:** 2025-12-17
- **Status:** Draft
- **Discussion:** https://github.com/ROCm/TheRock/issues/2608

## Overview

When a test regression occurs in ROCm super-repos (`rocm-libraries` or `rocm-systems`), developers need to identify which commit introduced the failure. Traditional `git bisect` would require rebuilding TheRock at each commit, which is prohibitively expensive (hours per commit).

This RFC proposes bisect tooling that leverages pre-built CI artifacts from super-repo workflows to enable fast regression identification without rebuilding.

## Motivation

The super-repos already run TheRock CI workflows (`.github/workflows/therock-ci-*.yml`) that:

- Build TheRock for every commit on the develop branch
- Upload artifacts to S3 buckets (segmented by repository, trust level, and run-id)
- Run component tests

These artifacts represent a valuable resource for bisection: they allow testing historical commits without the multi-hour rebuild cost. By downloading and testing against these pre-built artifacts, developers can bisect through commit ranges in minutes instead of days.

## Goals

- Create bisect tooling that leverages pre-built artifacts to find regressions without rebuilding
- Reduce bisection time from hours per commit to minutes per commit
- Reuse existing infrastructure (`fetch_artifacts.py`, GitHub API utilities, artifact storage)
- Provide a simple CLI interface that integrates with standard `git bisect` workflows

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ User provides:                                              │
│  - Repository (rocm-libraries / rocm-systems)              │
│  - Commit range (good_commit..bad_commit)                  │
│  - Test script to run                                      │
│  - GPU family (e.g., gfx942, gfx110X-dgpu)                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ bisect_submodule.py orchestrator                           │
│  1. Query GitHub API for workflow runs in commit range     │
│  2. Build commit→run_id mapping                            │
│  3. Initialize git bisect                                  │
│  4. For each bisect step:                                  │
│     a. Checkout commit                                     │
│     b. Find corresponding workflow run_id                  │
│     c. Download artifacts (via fetch_artifacts.py)        │
│     d. Setup test environment                              │
│     e. Run user test script                                │
│     f. Report result to git bisect                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Output: Identified commit that introduced regression       │
└─────────────────────────────────────────────────────────────┘
```

## Detailed Design

### 1. Core Components

#### `build_tools/bisect/bisect_submodule.py`

Main entry point that orchestrates the bisection process.

**Key Functions:**

- `query_workflow_runs(repo, commit_range)` → List of (commit_sha, run_id, workflow_url) tuples
- `setup_bisect_workspace(cache_dir)` → Create isolated workspace for artifacts/venvs
- `run_bisect(repo, good_commit, bad_commit, test_script, **options)` → Execute bisection
- `fetch_and_setup_artifacts(run_id, artifact_group, cache_dir)` → Download and prepare artifacts
- `execute_test(test_script, artifact_dir, env_vars)` → Run user test and capture result

**CLI Interface:**

```bash
python build_tools/bisect/bisect_submodule.py \
  --repo rocm-libraries \
  --good abc123 \
  --bad def456 \
  --test ./my_test_script.sh \
  --amdgpu-family gfx942 \
  [--cache-dir ~/.therock/bisect] \
  [--artifact-group gfx94X-all] \
  [--workflow therock-ci-linux.yml]
```

#### `build_tools/bisect/setup_test_env.py`

Creates an isolated environment for testing artifacts.

**Responsibilities:**

- Extract downloaded artifact archives to temporary directory
- Set up environment variables (PATH, LD_LIBRARY_PATH, ROCM_PATH, etc.)
- Optionally create Python venv with downloaded wheels
- Prepend artifact bin/ directories to PATH

**Interface:**

```python
def setup_test_environment(artifact_dir: Path, amdgpu_family: str) -> dict[str, str]:
    """Returns environment variables to use for test execution."""
    env = os.environ.copy()
    env["ROCM_PATH"] = str(artifact_dir / "rocm")
    env["PATH"] = f"{artifact_dir}/rocm/bin:{env['PATH']}"
    env["LD_LIBRARY_PATH"] = f"{artifact_dir}/rocm/lib:{env.get('LD_LIBRARY_PATH', '')}"
    env["THEROCK_BIN_DIR"] = str(artifact_dir / "rocm/bin")
    env["AMDGPU_FAMILIES"] = amdgpu_family
    return env
```

#### `build_tools/bisect/workflow_mapper.py`

Maps git commits to GitHub workflow runs.

**Key Challenges:**

- Not every commit has a workflow run (e.g., CI might be disabled, rate-limited, or failed to start)
- Need to handle commits that should be skipped in bisection
- Need to query GitHub API efficiently (pagination, caching)

**Interface:**

```python
class WorkflowMapper:
    def __init__(self, repo: str, workflow_file: str, cache_dir: Path):
        self.commit_to_run: dict[str, WorkflowRun] = {}

    def load_workflow_runs(self, commit_range: tuple[str, str]) -> None:
        """Query GitHub API for workflow runs in commit range."""

    def get_run_id(self, commit_sha: str) -> str | None:
        """Get workflow run_id for a commit, or None if no run exists."""

    def find_nearest_run(self, commit_sha: str, direction: str) -> str | None:
        """Find nearest commit with a run (for skipping commits)."""
```

**GitHub API Usage:**

```python
# Query workflow runs for a specific workflow file
url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_file}/runs"
params = {
    "branch": "develop",
    "created": f"{start_date}..{end_date}",
    "per_page": 100,
}
```

### 2. Caching Strategy

Similar to IREE's approach, use `~/.therock/bisect/` for caching:

```
~/.therock/bisect/
├── cache.db                    # SQLite DB mapping commits to run_ids
├── rocm-libraries/
│   └── <commit_sha>/
│       ├── artifacts/          # Downloaded .tar.xz files
│       ├── rocm/              # Extracted artifact tree
│       └── metadata.json      # Run info, download timestamp
└── rocm-systems/
    └── <commit_sha>/
        ├── artifacts/
        ├── rocm/
        └── metadata.json
```

**Benefits:**

- Avoid re-downloading artifacts for the same commit
- Persist across multiple bisect runs
- Can be cleaned up manually if disk space is needed

**Cache DB Schema:**

```sql
CREATE TABLE workflow_runs (
    repo TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    run_id INTEGER NOT NULL,
    workflow_url TEXT,
    created_at TEXT,
    conclusion TEXT,  -- success, failure, cancelled, skipped
    PRIMARY KEY (repo, commit_sha)
);

CREATE INDEX idx_commit ON workflow_runs(repo, commit_sha);
```

### 3. Integration with Git Bisect

The tool wraps `git bisect` similar to `git bisect run`:

```bash
# User workflow
cd rocm-libraries/
git bisect start
git bisect bad def456  # Known bad commit
git bisect good abc123 # Known good commit

# Run bisect with artifact downloading
git bisect run python ../TheRock/build_tools/bisect/bisect_submodule.py \
  --bisect-mode \
  --repo rocm-libraries \
  --test ../my_test_script.sh \
  --amdgpu-family gfx942
```

**Exit Codes from Test Script:**

- `0` - Test passed (commit is good)
- `1-124, 126-127` - Test failed (commit is bad)
- `125` - Test cannot run (skip this commit - no artifact available)
- `128+` - Special git bisect codes

**Handling Missing Artifacts:**

```python
def bisect_step(commit_sha: str, test_script: Path, **options) -> int:
    """Single bisect step - download artifacts and run test."""

    # Find workflow run for this commit
    run_id = mapper.get_run_id(commit_sha)

    if run_id is None:
        # No workflow run for this commit, skip it
        print(f"No workflow run found for {commit_sha[:8]}, marking as skip")
        return 125  # Tell git bisect to skip

    # Download artifacts (cached if already downloaded)
    artifact_dir = fetch_and_setup_artifacts(run_id, options.artifact_group, cache_dir)

    # Setup environment
    env = setup_test_environment(artifact_dir, options.amdgpu_family)

    # Run user test
    result = subprocess.run([test_script], env=env)
    return result.returncode
```

### 4. Artifact Download Integration

Reuse existing `fetch_artifacts.py` infrastructure:

```python
from build_tools.fetch_artifacts import main as fetch_artifacts_main


def fetch_and_setup_artifacts(
    run_id: str,
    artifact_group: str,
    cache_dir: Path,
    repo: str,
) -> Path:
    """Download artifacts for a run_id and extract to cache."""

    commit_cache_dir = cache_dir / repo / f"run_{run_id}"
    artifact_dir = commit_cache_dir / "artifacts"

    # Check if already cached
    if (commit_cache_dir / "metadata.json").exists():
        print(f"Using cached artifacts for run {run_id}")
        return commit_cache_dir / "rocm"

    # Download using fetch_artifacts.py
    commit_cache_dir.mkdir(parents=True, exist_ok=True)

    fetch_artifacts_main(
        [
            "--run-id",
            run_id,
            "--artifact-group",
            artifact_group,
            "--output-dir",
            str(artifact_dir),
            "--github-repository",
            f"ROCm/{repo}",
        ]
    )

    # Extract to rocm/ directory
    extract_artifacts(artifact_dir, commit_cache_dir / "rocm")

    # Save metadata
    save_metadata(commit_cache_dir, run_id)

    return commit_cache_dir / "rocm"
```

### 5. User Test Script Requirements

User test scripts must:

1. Use environment variables set by `setup_test_env.py`
1. Return appropriate exit codes (0 = good, 1+ = bad, 125 = skip)
1. Be executable and self-contained

**Example test script:**

```bash
#!/bin/bash
set -e

# Environment variables are already set:
# - ROCM_PATH
# - THEROCK_BIN_DIR
# - AMDGPU_FAMILIES

# Run the actual test
python build_tools/github_actions/test_executable_scripts/test_miopen.py

# Or run a custom test
# cd my_app && ./run_tests.sh
```

**Example Python test script:**

```python
#!/usr/bin/env python3
import os
import subprocess
import sys

# THEROCK_BIN_DIR is already in PATH
result = subprocess.run(["rocminfo"], capture_output=True, text=True)

if "gfx942" not in result.stdout:
    print("ERROR: Expected GPU not found")
    sys.exit(1)  # Bad

sys.exit(0)  # Good
```

### 6. Workflow Query Strategy

**Challenges:**

- GitHub API rate limits (5000 requests/hour authenticated)
- Large commit ranges may have hundreds of commits
- Not all commits have workflow runs

**Solution:**

1. **Bulk query workflow runs** for the entire date range:

   ```python
   # Get commit date range
   start_date = (
       subprocess.check_output(["git", "log", "-1", "--format=%cI", good_commit])
       .decode()
       .strip()
   )
   end_date = (
       subprocess.check_output(["git", "log", "-1", "--format=%cI", bad_commit])
       .decode()
       .strip()
   )

   # Query all workflow runs in this date range
   runs = query_workflow_runs(repo, workflow_file, start_date, end_date)
   ```

1. **Build commit→run mapping** by querying commit for each run:

   ```python
   for run in runs:
       # Each run has a head_sha field
       commit_to_run[run["head_sha"]] = run["id"]
   ```

1. **Cache results** in SQLite DB to avoid re-querying:

   ```python
   # On subsequent runs, only query runs newer than cached data
   last_cached_date = db.get_latest_cached_date(repo)
   runs = query_workflow_runs(repo, workflow_file, last_cached_date, "now")
   ```

### 7. Error Handling

**Common Scenarios:**

| Scenario                   | Handling                                |
| -------------------------- | --------------------------------------- |
| No workflow run for commit | Return exit code 125 (skip)             |
| Artifact download fails    | Retry 3 times, then return 125 (skip)   |
| Artifact extraction fails  | Log error, return 125 (skip)            |
| Test script not executable | Fail fast with clear error message      |
| GitHub API rate limit      | Wait and retry with exponential backoff |
| Invalid commit range       | Validate commits exist before starting  |
| Cache corruption           | Delete cache entry and re-download      |

### 8. Future Enhancements

**Phase 2:**

- Support for Windows artifacts
- Parallel downloading of artifacts (pre-fetch likely candidates)
- Web UI for visualizing bisect progress
- Integration with test result database
- Automatic test script generation for common scenarios

**Phase 3:**

- Bisect across TheRock commits (not just super-repo commits)
- Support for multiple artifact groups simultaneously
- Delta debugging (minimize failing test case)
- Regression report generation

## Implementation Plan

### Milestone 1: Core Infrastructure (Week 1-2)

- [ ] `workflow_mapper.py` - GitHub API integration and caching
- [ ] `setup_test_env.py` - Environment setup
- [ ] Cache directory structure and SQLite schema
- [ ] Unit tests for core components

### Milestone 2: Bisect Orchestration (Week 3-4)

- [ ] `bisect_submodule.py` - Main entry point
- [ ] Git bisect integration
- [ ] Artifact download and extraction
- [ ] End-to-end testing with real super-repo commits

### Milestone 3: Documentation & Polish (Week 5)

- [ ] User documentation and examples
- [ ] Error message improvements
- [ ] Performance optimizations
- [ ] Integration with existing TheRock docs

### Milestone 4: CI Integration (Week 6)

- [ ] Add bisect tool to TheRock CI for regression detection
- [ ] Example workflows for common bisect scenarios
- [ ] Monitoring and alerting

## Open Questions

1. **Should we support bisecting across TheRock versions?**

   - Super-repo CI pins TheRock to a specific commit
   - If the regression is in TheRock itself, need different approach
   - **Recommendation**: Start with super-repo only, add TheRock bisect in Phase 2

1. **How to handle multi-arch testing?**

   - Some regressions only appear on specific GPU families
   - **Recommendation**: Require user to specify `--amdgpu-family`, download only those artifacts

1. **Should we support bisecting external builds (PyTorch)?**

   - External builds are more complex
   - **Recommendation**: Out of scope for initial implementation

1. **Integration with existing test harness?**

   - Could auto-generate test scripts from `test_executable_scripts/`
   - **Recommendation**: Start with user-provided scripts, add auto-generation in Phase 2

1. **Handling of nightly vs. PR artifacts?**

   - Different S3 buckets for different release types
   - **Recommendation**: Default to CI artifacts, allow override via `--bucket` flag

## Success Metrics

- **Time savings**: Reduce bisection time from hours to minutes
- **Adoption**: 5+ developers use tool in first month
- **Reliability**: 95%+ of commits in super-repos have usable artifacts
- **Cache hit rate**: 80%+ of artifacts served from cache on repeated bisects

## References

- [IREE bisect tools](https://github.com/iree-org/iree/tree/main/build_tools/pkgci/bisect) - Inspiration for design
- [fetch_artifacts.py](build_tools/fetch_artifacts.py) - Existing artifact download infrastructure
- [BUILD_TOPOLOGY.toml](BUILD_TOPOLOGY.toml) - Artifact structure definition
- [GitHub Actions Workflow Runs API](https://docs.github.com/en/rest/actions/workflow-runs)
