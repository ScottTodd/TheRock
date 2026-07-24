# Testing overview

**TheRock is the integration point for all build, test, packaging, and release
infrastructure for ROCm Core.** The code here is used by developers building
ROCm from source, CI systems validating pull request contributions
in repositories like [rocm-systems](https://github.com/ROCm/rocm-systems) and
[rocm-libraries](https://github.com/ROCm/rocm-libraries), and release workflows
publishing nightly and stable releases in
[rockrel](https://github.com/ROCm/rockrel) which are trusted by users and
downstream projects.

**TheRock aims to keep ROCm "ready to release" at any time.** Achieving this at
scale requires robust automated tests that detect issues as close as possible
to their source. Early detection limits the impact of regressions and makes
them easier to diagnose and fix, while continuous validation provides the
confidence needed to release frequently.

**Testing must scale across a broad support surface.** ROCm includes
40+ subprojects, supports 25+ GPU targets across multiple hardware generations,
runs on multiple operating systems, is distributed via multiple packaging
formats, and is used by many downstream frameworks. Testing every combination
for every change is not practical, so TheRock layers automated tests according
to their cost and the confidence they provide. Presubmit testing prioritizes
fast, high-signal test suites and configurations with enough capacity to run for
every change. Longer test suites and hardware with limited runner capacity are
exercised through nightly, scheduled, and on-demand testing.

**Testing should be accessible to all contributors.** Wherever possible,
code and automation should be structured so that important behavior can be
tested quickly on commonly available development machines. Local testing usually
provides the fastest feedback, while continuous integration (CI) workflows
provide consistent environments for validating changes across representative
project-wide configurations and component boundaries.

**ROCm Core is built and released as a single product.** Individual subprojects
can validate their own behavior in isolation, but TheRock assembles and tests
those projects together as often as practical throughout development, providing
confidence in cross-component behavior and product-wide properties that
component-level testing cannot evaluate.

<!-- TODO: make this content flow better, "good testing" is too vague -->

This page describes how these testing layers work together, how TheRock code
can make good testing the easy path, and what good testing looks like for
common types of contributions.

## Testing principles

### Make tests accessible during development

### Use layered validation

- Use static analysis for mechanical checks

### Scale coverage to available resources

### Add reliable tests to required CI

______________________________________________________________________

## Testing changes to TheRock

### Test categories in TheRock

Tests for the code in TheRock itself are split into a few broad categories:

- pre-commit and static checks
  - These are fast checks for formatting, linting, repository policies, and more
  - Example tests:
    - `actionlint` for GitHub Actions workflow files
    - `black` formatting for Python scripts
    - `check-merge-conflicts` for all files
- unit tests
  - These are fast tests for script behavior, runnable on generic hardware
  - Example tests:
    - [`build_tools/tests/build_topology_test.py`](/build_tools/tests/build_topology_test.py)
    - [`build_tools/tests/fileset_tool_test.py`](/build_tools/tests/fileset_tool_test.py)
    - [`build_tools/github_actions/tests/workflow_dispatch_inputs_test.py`](/build_tools/github_actions/tests/workflow_dispatch_inputs_test.py)
- integration tests
  - These provide validation for build outputs and packages and may run on real hardware
  - Example tests:
    - [`tests/test_artifact_structure.py`](/tests/test_artifact_structure.py)
    - [`tests/test_rocm_sanity.py`](/tests/test_rocm_sanity.py)
    - [`build_tools/packaging/linux/native_linux_package_install_test.py`](/build_tools/packaging/linux/native_linux_package_install_test.py)
    - [`build_tools/packaging/python/templates/rocm/src/rocm_sdk/tests/core_test.py`](/build_tools/packaging/python/templates/rocm/src/rocm_sdk/tests/core_test.py)

Tests in each category are runnable as part of local development and are also
run as part of our CI workflows:

| Test type         | Target test runtime | CI workflows                                                                                                                                                                                                                                                                                                                                      |
| ----------------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| pre-commit        | 10 seconds          | <ul><li>[`.pre-commit-config.yaml`](/.pre-commit-config.yaml)</li><li>[`.github/workflows/pre-commit.yml`](/.github/workflows/pre-commit.yml)</li></ul>                                                                                                                                                                                           |
| unit tests        | 5 minutes           | <ul><li>[`.github/workflows/unit_tests.yml`](/.github/workflows/unit_tests.yml)</li></ul>                                                                                                                                                                                                                                                         |
| integration tests | 30 minutes          | <ul><li>[`.github/workflows/test_artifacts_structure.yml`](/.github/workflows/test_artifacts_structure.yml)</li><li>[`.github/workflows/test_native_linux_packages_install.yml`](/.github/workflows/test_native_linux_packages_install.yml)</li><li>[`.github/workflows/test_rocm_wheels.yml`](/.github/workflows/test_rocm_wheels.yml)</li></ul> |

### CMake and super-project build logic

As the centralized build system for ROCm Core, TheRock includes a CMake
super-project using code in:

- CMake project files like [`CMakeLists.txt`](/CMakeLists.txt) and
  [`cmake/therock_amdgpu_targets.cmake`](/cmake/therock_amdgpu_targets.cmake)
- Topology metadata in [`BUILD_TOPOLOGY.toml`](/BUILD_TOPOLOGY.toml)
- Sub-project declarations like [`math-libs/CMakeLists.txt`](/math-libs/CMakeLists.txt)
- Sub-project artifact descriptors like [`math-libs/BLAS/artifact-blas.toml`](/math-libs/BLAS/artifact-blas.toml)
- Scripts used by the build system like [`build_tools/fileset_tool.py`](/build_tools/fileset_tool.py)

The build system supports a broad matrix of configurations:

| Matrix dimension          | Available configurations                                                                        | Typical CI coverage                             |
| ------------------------- | ----------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| Operating system          | Linux (multiple distros), WSL, Windows                                                          | Linux (manylinux), WSL, Windows                 |
| Build variant             | Release, Debug, Address Sanitizer (ASan), etc.                                                  | Release, ASan                                   |
| AMDGPU build/test targets | `gfx942`, `gfx950`, `gfx1100`, `gfx1200`, etc.                                                  | 1-3 targets (based on test runner availability) |
| Enabled subprojects       | `THEROCK_ENABLE_ALL`, `THEROCK_ENABLE_PROFILER`, etc.                                           | All enabled, subsets as an optimization         |
| Enabled feature flags     | See [`FLAGS.cmake`](/FLAGS.cmake) and [`docs/development/flags.md`](/docs/development/flags.md) | Default values                                  |
| Other CMake options       | `THEROCK_BUILD_TESTING`, `THEROCK_BUNDLE_SYSDEPS`, etc.                                         | Default values                                  |

The CI systems in [TheRock](https://github.com/ROCm/TheRock) and component
repositories like [rocm-systems](https://github.com/ROCm/rocm-systems)
continuously build a few slices through this support matrix.

> [!IMPORTANT]
> Certain types of changes often warrant additional validation, such as:
>
> - Adding new subprojects
> - Adjusting support for specific AMDGPU targets
> - Updates to the compiler (llvm-project)
>
> Pull requests that modify key git submodules in TheRock automatically run
> extra CI jobs. These extra CI jobs can be enabled for other PRs through
> the mechanisms documented in
> [ci_behavior_manipulation.md](/docs/development/ci_behavior_manipulation.md).

### GitHub Actions workflows

<!-- DRAFT -->

Types of workflows:

- Lightweight checks: codeql.yml, gitleaks.yml, pre-commit.yml, unit_tests.yml, therock-pr-bot.yml
- CI/CD workflows: multi_arch_ci.yml, multi_arch_release.yml, etc.
- Other automation: bump_submodules.yml, copy_release.yml, publish_build_manylinux_x86_64.yml

Per docs/development/style_guides/github_actions_style_guide.md...

- "Prefer Python scripts over inline Bash"
- "Separate build and test stages" and modular workflows allow for testing
  without needing to build fully from scratch during testing (see docs/development/github_actions_debugging.md also)

emphasize that

- CI needs to stay stable or all development is blocked
- nightly releases need to stay stable so we can release at any point
- iteration cycles on changes to workflows can be exceedingly long if working
  directly in workflow files, put logic in scripts that are runnable locally

<!-- DRAFT -->

### Python scripts and tools

### Packaging and release infrastructure

<!-- TODO: "infrastrcture" is overloaded here -->

<!-- TODO: merge with "Validating assembled ROCm" section below?

     could focus this on release workflows?
-->

<!-- DRAFT -->

Types of packages:

- artifacts (the raw build system outputs)
- tarballs/archives (folder distributions that are not associated with any particular package manager / ecosystem)
- native linux packages (deb/rpm)
- native windows packages (msi)
- python packages

Test for:

- unit test: package construction (no crashes, outputs are not malformed, files are filtered as expected)
- integration test: package install/usage behavior
  - installable
  - can load and call APIs - matching what user-facing instructions say to do
  - install on multiple supported distros (e.g. build on manylinux -> test on Ubuntu and RHEL)
- integration test: interaction between multiple packages
  - ROCm packages should be self-sufficient and not conflict with system packages
  - packages should be compatible/usable with other packages in the same ecosystem (e.g. PyTorch using ROCm python packages)

<!-- DRAFT -->

### Maintaining reliable CI infrastructure

<!-- TODO: "infrastrcture" is overloaded here -->

### Framework integration tooling

______________________________________________________________________

## Testing changes to ROCm subprojects with TheRock

<!-- TODO: mention therock_cmake_subproject_build_test -->

<!-- TODO: mention build_tools/github_actions/test_executable_scripts/README.md -->

### Build subprojects through TheRock

### Use standardized component test interfaces

- build_tools/github_actions/test_executable_scripts/test_runner.py

### Make test environments explicit and reproducible

<!-- TODO: reword section header, merge with prior section? -->

- tests should aim to be runnable from installed artifacts using standard test runners, e.g. `pytest` or `ctest`
  - avoid what build_tools/github_actions/test_executable_scripts/test_hiptests.py does with copy_dlls_exe_path
  - avoid that build_tools/github_actions/test_executable_scripts/test_origami.py does with `LD_LIBRARY_PATH`
- developers _working on the projects_ and users/CI systems that _install test artifacts_ should have the same experience

### "TheRock CI" in component repositories

<!-- DRAFT -->

- First CI line of defense against regressions

<!-- DRAFT -->

### Test submodule updates

#### Testing changes to rocm-libraries and rocm-systems

#### Testing changes to llvm-project

______________________________________________________________________

## Validating assembled ROCm

### Validate artifact contents and dependencies

### Install and test distributed packages

### Run component tests against assembled ROCm

### Test on supported GPU hardware

### Validate downstream frameworks

### Validate development and release pipelines
