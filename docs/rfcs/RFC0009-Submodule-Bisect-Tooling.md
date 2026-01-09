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
│  - Repository (rocm-libraries / rocm-systems)               │
│  - Commit range (good_commit..bad_commit)                   │
│  - Test script to run                                       │
│  - GPU family (e.g., gfx942, gfx110X-dgpu)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ bisect_submodule.py orchestrator                            │
│  1. Query GitHub API for workflow runs in commit range      │
│  2. Build commit→run_id mapping                             │
│  3. Initialize git bisect                                   │
│  4. For each bisect step:                                   │
│     a. Checkout commit                                      │
│     b. Find corresponding workflow run_id                   │
│     c. Download artifacts (via fetch_artifacts.py)          │
│     d. Setup test environment                               │
│     e. Run user test script                                 │
│     f. Report result to git bisect                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Output: Identified commit that introduced regression        │
└─────────────────────────────────────────────────────────────┘
```

## Detailed Design

### 1. High-Level Components

The system is composed of four main components that work together to enable artifact-based bisection:

#### Bisect Orchestrator (`bisect_submodule.py`)

Main entry point that drives the bisection process. Coordinates between git bisect, the workflow mapper, artifact fetcher, and test executor.

**Responsibilities:**

- Parse CLI arguments and validate inputs
- Initialize bisect workspace
- Execute bisect loop (checkout → fetch artifacts → setup env → run test → report)
- Handle errors and cleanup

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

#### Workflow Mapper (`workflow_mapper.py`)

Maps git commits to GitHub workflow runs. Provides an abstract interface for querying commit→run_id mappings.

**Key Challenges:**

- Not every commit has a workflow run (CI disabled, rate-limited, failed to start)
- Need efficient GitHub API querying with pagination
- Must handle missing mappings gracefully

**Core Interface:**

```python
class WorkflowMapper:
    """Maps commits to workflow runs using pluggable storage."""

    def get_run_id(self, commit_sha: str) -> str | None:
        """Get workflow run_id for a commit, or None if no run exists."""

    def load_commit_range(self, good_commit: str, bad_commit: str) -> None:
        """Load workflow runs for commits in the given range."""

    def get_run_metadata(self, run_id: str) -> dict[str, Any]:
        """Get metadata about a workflow run (url, conclusion, timestamp, etc)."""
```

**Storage Abstraction:**

The mapper uses a pluggable storage backend for caching mappings:

```python
class RunMappingStore(Protocol):
    """Storage interface for commit→run_id mappings."""

    def get(self, repo: str, commit_sha: str) -> WorkflowRun | None:
        """Retrieve mapping for a commit."""

    def set(self, repo: str, commit_sha: str, run: WorkflowRun) -> None:
        """Store mapping for a commit."""

    def get_all(self, repo: str) -> dict[str, WorkflowRun]:
        """Get all cached mappings for a repository."""
```

This abstraction allows us to start simple (in-memory) and evolve to persistent storage (SQLite, remote DB) without changing the orchestrator.

#### Artifact Manager (`artifact_manager.py`)

Downloads and caches artifacts, integrating with existing `fetch_artifacts.py`.

**Responsibilities:**

- Download artifacts for a given run_id
- Extract archives to cache directory
- Manage cache lifecycle (check existence, cleanup)
- Reuse existing `fetch_artifacts.py` infrastructure

**Interface:**

```python
class ArtifactManager:
    def get_artifact_dir(self, run_id: str, artifact_group: str) -> Path:
        """Get artifact directory, downloading if necessary."""

    def is_cached(self, run_id: str) -> bool:
        """Check if artifacts are already cached."""

    def cleanup_old_artifacts(self, keep_latest_n: int = 10) -> None:
        """Remove old cached artifacts to save disk space."""
```

#### Test Environment Setup (`setup_test_env.py`)

Prepares an isolated environment for running tests against downloaded artifacts.

**Responsibilities:**

- Set up environment variables (PATH, LD_LIBRARY_PATH, ROCM_PATH, etc.)
- Locate artifact binaries and libraries
- Create Python venv if needed (for wheel testing)

**Interface:**

```python
def setup_test_environment(artifact_dir: Path, amdgpu_family: str) -> dict[str, str]:
    """Returns environment variables to use for test execution."""
```

### 2. Component Interaction

```
┌──────────────────────────────────────────────────────────────────┐
│ bisect_submodule.py (Orchestrator)                               │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Bisect Loop                                                │  │
│  │                                                            │  │
│  │  1. git checkout <commit>                                 │  │
│  │  2. mapper.get_run_id(commit) → run_id or None            │  │
│  │  3. artifact_mgr.get_artifact_dir(run_id) → Path          │  │
│  │  4. setup_test_env(artifact_dir) → env_vars               │  │
│  │  5. subprocess.run(test_script, env=env_vars) → exit_code │  │
│  │  6. git bisect good/bad/skip based on exit_code           │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                    │                    │
        ┌───────────┘                    └───────────┐
        ▼                                            ▼
┌──────────────────────┐                  ┌─────────────────────┐
│ WorkflowMapper       │                  │ ArtifactManager     │
│                      │                  │                     │
│ ┌─────────────────┐  │                  │ ┌─────────────────┐ │
│ │ RunMappingStore │  │                  │ │ fetch_artifacts │ │
│ │  (pluggable)    │  │                  │ │     .py         │ │
│ └─────────────────┘  │                  │ └─────────────────┘ │
│         │            │                  │         │           │
│         ▼            │                  │         ▼           │
│ ┌─────────────────┐  │                  │ ┌─────────────────┐ │
│ │ GitHub API      │  │                  │ │ Cache Directory │ │
│ └─────────────────┘  │                  │ └─────────────────┘ │
└──────────────────────┘                  └─────────────────────┘
```

### 3. Implementation Details

#### Initial Storage: In-Memory RunMappingStore

Start with a simple in-memory dictionary for the `RunMappingStore`:

```python
@dataclass
class WorkflowRun:
    run_id: str
    commit_sha: str
    workflow_url: str
    created_at: str
    conclusion: str  # success, failure, cancelled, skipped


class InMemoryRunStore:
    """Simple in-memory storage for commit→run_id mappings."""

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], WorkflowRun] = {}

    def get(self, repo: str, commit_sha: str) -> WorkflowRun | None:
        return self._store.get((repo, commit_sha))

    def set(self, repo: str, commit_sha: str, run: WorkflowRun) -> None:
        self._store[(repo, commit_sha)] = run

    def get_all(self, repo: str) -> dict[str, WorkflowRun]:
        return {commit: run for (r, commit), run in self._store.items() if r == repo}
```

**Benefits:**

- Simple to implement and test
- No external dependencies (no SQLite)
- Easy to reason about
- Fast lookups
- Perfect for prototyping and single bisect sessions

**Limitations:**

- No persistence across runs
- Not suitable for sharing across processes
- All data must fit in memory

**Future Migration Path:**

When persistence becomes valuable, implement `SQLiteRunStore` or `RemoteRunStore` with the same protocol interface. The orchestrator and WorkflowMapper don't need to change - just swap the storage backend.

#### Cache Directory Structure

```
~/.therock/bisect/
├── rocm-libraries/
│   └── <commit_sha>/
│       ├── artifacts/         # Downloaded .tar.xz files
│       ├── rocm/              # Extracted artifact tree
│       └── metadata.json      # Run info, download timestamp
└── rocm-systems/
    └── <commit_sha>/
        ├── artifacts/
        ├── rocm/
        └── metadata.json
```

**Note:** No `cache.db` in the initial implementation - workflow mappings live in memory during the bisect session. This keeps the initial implementation simple while maintaining the option to add persistence later.

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

1. **Build commit→run mapping** and store in RunMappingStore:

   ```python
   store = InMemoryRunStore()
   for run in runs:
       # Each run has a head_sha field
       workflow_run = WorkflowRun(
           run_id=run["id"],
           commit_sha=run["head_sha"],
           workflow_url=run["html_url"],
           created_at=run["created_at"],
           conclusion=run["conclusion"],
       )
       store.set(repo, run["head_sha"], workflow_run)
   ```

1. **Future enhancement**: Persistent caching with SQLite or remote database

   For the initial implementation, we query the GitHub API once per bisect session. Future implementations can add persistent caching to avoid re-querying across sessions.

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

## Decisions & Trade-offs

### In-Memory vs Persistent Storage (Phase 1)

**Decision:** Use in-memory `InMemoryRunStore` for initial implementation

**Rationale:**

- Simplifies initial development (no SQLite dependency)
- Faster iteration during prototyping
- Still provides abstraction for future migration
- Single bisect session can query GitHub API once and cache in memory

**Alternatives considered:**

- SQLite from the start: More complexity, harder to test, overkill for prototype
- No abstraction: Would make future migration harder

### Cache Directory Structure

**Decision:** Use `~/.therock/bisect/<repo>/<commit_sha>/` structure

**Rationale:**

- Commit SHA is more intuitive for debugging
- Easier to manually inspect cached artifacts
- Aligns with git workflow (users think in commits, not run IDs)

**Alternatives considered:**

- Using `run_<run_id>`: Less intuitive, harder to correlate with git history

### Bisect Modes: Lightweight vs Heavy

**Challenge:** Super-repo CI workflows (e.g., rocm-systems) build only a subset of ROCm components. Pre-built artifacts may not include the component where the regression occurs (e.g., rocprim test failures when only HIP/runtime are pre-built).

**Decision:** Design for two bisect modes to handle partial artifact coverage

**Mode 1: Lightweight (Repackaging)**

- Download pre-built artifacts and use them directly
- Repackage ROCm with different component versions
- No compilation required
- Use case: Test downstream components against different library versions without rebuilding
- Example: Test rocprim (from one commit) against HIP runtime (from bisected commits)

**Mode 2: Heavy (Bootstrap + Rebuild)**

- Use `buildctl.py` to bootstrap build directory with available artifacts
- Build missing components from source
- Compilation required but faster than full rebuild
- Use case: Regressions in components not included in pre-built artifacts
- Example: Bisect rocprim changes where HIP API changes require rocprim rebuild

**Rationale:**

- Flexibility: Support both shallow (library-only) and deep (requires rebuild) regressions
- Scalability: Lightweight mode enables parallelization on low-powered machines
- Practicality: Acknowledges real-world artifact coverage gaps
- Incremental: Can implement lightweight first, add heavy mode later

**Implementation Impact:**

- `ArtifactManager`: Needs download-only mode (Phase 1) and bootstrap mode (Phase 2+)
- Test scripts: May declare mode requirement via metadata or convention
- Documentation: Must explain when each mode is appropriate

**Alternatives considered:**

- Full rebuild always: Too expensive, defeats the purpose of using artifacts
- Lightweight only: Would exclude important use cases with partial artifacts
- Require complete artifacts: Unrealistic given CI resource constraints

## Implementation Plan

### Phase 1: Prototype & Validation

Focus on getting a working prototype with minimal complexity to validate the approach.

**Goals:**

- Prove the concept works end-to-end
- Identify any architectural issues early
- Build confidence in the design

**Tasks:**

- [ ] `workflow_mapper.py` - GitHub API integration with `InMemoryRunStore`
- [ ] `artifact_manager.py` - Basic artifact download and caching
- [ ] `setup_test_env.py` - Environment setup
- [ ] `bisect_submodule.py` - Basic orchestrator (manual mode, not git-bisect integration yet)
- [ ] Cache directory structure
- [ ] Manual end-to-end test with a known regression

### Phase 2: Git Bisect Integration

Integrate with `git bisect run` for automated bisection.

**Tasks:**

- [ ] Update orchestrator for `git bisect run` compatibility
- [ ] Exit code handling (0/1/125)
- [ ] Error handling and retry logic
- [ ] End-to-end testing with real super-repo commits

### Phase 3: Polish & Documentation

Make the tool production-ready.

**Tasks:**

- [ ] User documentation and examples
- [ ] Error message improvements
- [ ] Performance optimizations
- [ ] Unit tests for core components
- [ ] Integration with existing TheRock docs

### Phase 4: Enhancements (Future)

Add features based on user feedback.

**Potential Tasks:**

- [ ] Persistent storage backend (SQLite or remote DB)
- [ ] Parallel artifact pre-fetching
- [ ] Support for Windows artifacts
- [ ] Centralized artifact database abstraction

## Future Work: CI-Orchestrated Bisection

The initial implementation focuses on local bisection where artifacts are downloaded and tested on a developer's machine. A complementary approach would leverage our existing CI infrastructure to perform bisection workflows entirely in the cloud.

### Concept

Rather than downloading artifacts locally, the bisect orchestrator would launch GitHub workflow runs that build/test each bisected commit. The orchestrator monitors these workflow runs and reports results back to the bisect algorithm.

### Benefits

**Infrastructure Reuse:**

- Logs viewable online in the same format as regular CI runs
- Optimizations to bootstrapping and project slicing propagate to all workflows
- Leverage existing build and test machine pools

**Parallelism:**

- Multiple commits tested simultaneously across available runners
- No local hardware constraints (GPU availability, OS requirements)
- Natural distribution of workload

**Consistency:**

- Tests run in same environment as CI
- No "works locally but fails in CI" divergence
- Artifact caching already optimized

### Challenges

**Orchestration Complexity:**

- Bisect orchestrator must launch workflows and listen for completion events
- The orchestrator itself could be a workflow (workflow launching workflows)
- Job status monitoring across many parallel runs
- Handling workflow failures, timeouts, runner unavailability

**Feedback Loop:**

- Longer iteration time compared to local testing
- Debugging harder without local access
- Cost implications of spinning up many CI runs

**Resource Contention:**

- Could starve regular PR/commit CI of runners
- Need quotas or dedicated runner pools
- Queue wait times impact bisection speed

### Integration Strategy

The CI-based approach complements rather than replaces local bisection:

1. **Local bisection** (Phase 1-3): Fast iteration, easy debugging, developer-driven
1. **CI-based bisection** (Future): Automated regression detection, no hardware constraints, production-scale testing

Both modes can share:

- Workflow mapper (commit→run_id mapping)
- Artifact discovery logic
- Test script conventions

The orchestrator becomes a strategy pattern:

- `LocalBisectStrategy`: Downloads artifacts, runs tests locally
- `CIBisectStrategy`: Launches workflows, monitors status, aggregates results

### Open Design Questions

1. How does the CI orchestrator communicate bisect state?

   - GitHub Actions outputs?
   - Artifacts containing bisect state?
   - External state service?

1. How to prevent resource exhaustion?

   - Dedicated runner labels for bisection?
   - Queue depth limits?
   - Cost budgets?

1. How to surface results to developers?

   - Workflow summary with bisect progress?
   - Integration with GitHub issue comments?
   - Separate bisect dashboard?

This approach is valuable for automated regression detection and production-scale testing but requires significant infrastructure work. It's positioned as future work after local bisection is proven.

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
