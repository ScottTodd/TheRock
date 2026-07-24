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

Tests are split into a few

- pre-commit: these are fast checks for formatting, linting, repository policies, and more.
- unit tests: these are fast tests for script behavior, runnable on generic hardware.
- integration tests: these provide validation for build outputs and packages and run on real hardware.

| Test type         | Description                                                         | Time budget | Special requirements                                            | Validated by                                                                                                                                                                                                                                                                                                                                      |
| ----------------- | ------------------------------------------------------------------- | ----------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| pre-commit        | Fast checks for formatting, linting, repository policies, and more. | 10 seconds  | None (run on _every_ commit)                                    | <ul><li>[`.pre-commit-config.yaml`](/.pre-commit-config.yaml)</li><li>[`.github/workflows/pre-commit.yml`](/.github/workflows/pre-commit.yml)</li></ul>                                                                                                                                                                                           |
| Unit tests        | Fast tests for script behavior, runnable on generic hardware.       | 5 minutes   | File system and network access                                  | <ul><li>[`.github/workflows/unit_tests.yml`](/.github/workflows/unit_tests.yml)</li></ul>                                                                                                                                                                                                                                                         |
| Integration tests | Validation for build outputs and packages, running on real hardware | 30 minutes  | Build system outputs, specific operating systems, physical GPUs | <ul><li>[`.github/workflows/test_artifacts_structure.yml`](/.github/workflows/test_artifacts_structure.yml)</li><li>[`.github/workflows/test_native_linux_packages_install.yml`](/.github/workflows/test_native_linux_packages_install.yml)</li><li>[`.github/workflows/test_rocm_wheels.yml`](/.github/workflows/test_rocm_wheels.yml)</li></ul> |

### Scale coverage to available resources

### Add reliable tests to required CI

______________________________________________________________________

## Testing changes to TheRock

### CMake and super-project build logic

### GitHub Actions workflows

### Python scripts and tools

### Packaging and release infrastructure

<!-- TODO: "infrastrcture" is overloaded here -->

### Maintaining reliable CI infrastructure

### Framework integration tooling

______________________________________________________________________

## Testing changes to ROCm subprojects with TheRock

<!-- TODO: mention therock_cmake_subproject_build_test -->

<!-- TODO: mention build_tools/github_actions/test_executable_scripts/README.md -->

### Build subprojects through TheRock

### Use standardized component test interfaces

### Make test environments explicit and reproducible

### "TheRock CI" in component repositories

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
