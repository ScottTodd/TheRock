# Testing overview

> [!NOTE]
> This page is currently an outline. It will be expanded iteratively with
> tested commands, examples, and links as part of
> [issue #6711](https://github.com/ROCm/TheRock/issues/6711).

This page is the entry point for understanding how changes to TheRock are
validated. It will describe the project's testing strategy, help contributors
choose an appropriate test plan, and explain what confidence can and cannot be
inferred from local and CI results.

TheRock is both a CMake super-project and the integration point for ROCm build,
test, packaging, and release pipelines. Testing therefore spans more than the
source code in this repository. It includes component-owned tests, assembled
artifacts, installable packages, downstream frameworks, and GitHub Actions
workflows also called from repositories such as
[`ROCm/rockrel`](https://github.com/ROCm/rockrel).

## Testing strategy

### Validate the risk introduced by the change

- Identify the behavior and interfaces affected by the change, including
  downstream consumers.
- Start with the smallest deterministic test that can catch a regression, then
  add integration coverage where components, platforms, or services meet.
- Add a focused regression test for bug fixes whenever practical.
- Prefer testing the same commands, artifacts, and packages that users and CI
  consume rather than a convenient substitute.
- Record important dimensions that were and were not tested instead of relying
  on an ambiguous statement such as "CI passed."

### Confidence comes from layers

The testing layers overlap intentionally. A higher layer does not make the
lower layers redundant, and no single layer proves the whole distribution is
correct.

| Layer                     | Examples                                                    | Primary confidence provided                                                                    |
| ------------------------- | ----------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Static checks             | formatting, YAML parsing, `actionlint`, security scans      | Files are well formed and follow repository policies                                           |
| Unit tests                | Python tests under `build_tools/**/tests/`                  | Build, CI, packaging, and release logic handles expected inputs and failures                   |
| Configure and build tests | CMake configure, targeted Ninja builds                      | The super-project graph and component build integration are valid for a selected configuration |
| Artifact tests            | structure validation, sanity tests, relocation checks       | Build outputs contain the expected files and declared runtime dependencies                     |
| Component tests           | hipBLASLt, rocBLAS, MIOpen, and other installed test suites | Component behavior works on selected operating systems and GPU hardware                        |
| Package tests             | Python wheels, native packages, tarballs                    | Distribution formats can be installed and used outside the build tree                          |
| System tests              | PyTorch, JAX, functional tests, benchmarks                  | Multiple ROCm components work together for representative user workloads                       |
| Release tests             | `dev`, nightly, and prerelease pipelines                    | Versioning, publishing, indexes, credentials, and release orchestration work end to end        |

### Keep ownership close to the code

- Component repositories own detailed unit, algorithm, correctness, and
  regression coverage for their code.
- TheRock owns the super-project build graph, artifact contracts, packaging,
  CI/CD helpers, and integration of component tests into assembled ROCm builds.
- A component change should normally be tested first in its native development
  loop and then through TheRock when build, packaging, dependency, or
  distribution behavior could be affected.
- TheRock's test adapters should select and invoke component tests, not
  duplicate component test logic.

### Treat coverage as a set of dimensions

A test plan may need to vary across:

- operating system and distribution;
- GPU family and exact GPU target;
- build variant, such as release or a sanitizer build;
- component test tier;
- source build, artifact, wheel, native package, or tarball layout;
- pull request, postsubmit, scheduled, or release trigger; and
- `ci`, `dev`, nightly, or prerelease storage and versioning behavior.

The goal is not to test the Cartesian product for every change. The goal is to
choose representative dimensions based on risk and explicitly identify gaps.

## Choosing a test plan

This table will become the quick-start path for contributors. Each row should
eventually link to exact commands and examples in the sections below.

| Change area                    | Expected starting point                                                   | Reasons to expand coverage                                                                                            |
| ------------------------------ | ------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Documentation or metadata      | Targeted pre-commit hooks                                                 | Generated docs, embedded commands, or workflow metadata also changed                                                  |
| Python build/CI/release script | Focused unit tests, then the full `build_tools` unit suite                | Subprocesses, network services, package files, or platform-specific behavior changed                                  |
| GitHub Actions workflow        | `actionlint`, workflow unit/contract tests, affected automatic trigger    | Expressions, permissions, self-hosted runners, reusable callers, publishing, or schedules changed                     |
| CMake or build topology        | Configure plus the smallest affected build and `dist` targets             | Dependency edges, artifacts, platform logic, feature flags, or submodules changed                                     |
| Component or submodule         | Native component tests plus TheRock component tests on relevant GPUs      | Installed layout, downstream dependencies, multiple GPU families, or both operating systems are affected              |
| Packaging                      | Unit tests plus build, install, and runtime checks of the affected format | Package indexes, dependency metadata, multiple Python versions, or multiple Linux distributions are affected          |
| Release pipeline               | End-to-end `dev` release using a narrow representative matrix             | Code is shared with nightly/prerelease, changes destinations or credentials, or affects downstream framework releases |

### Document the test result

- Include exact commands, relevant inputs, GPU and operating system details,
  and the observed result in the pull request.
- Link GitHub Actions runs when they are part of the evidence.
- State which important configurations were not tested and why.
- Distinguish a test that was skipped, expected to fail, or allowed to fail
  from one that passed.

## Static checks and Python unit tests

### Pre-commit checks

- Explain the repository's formatting, file validation, and `actionlint`
  checks, with focused and all-files commands.
- Clarify that static validation catches malformed workflow syntax but does not
  execute GitHub expressions, contact services, or exercise runner state.
- Link to [`CONTRIBUTING.md`](../../CONTRIBUTING.md#pre-commit-checks) and the
  language-specific [style guides](style_guides/README.md).

### Python unit test layout

- Document the pytest configuration in
  [`build_tools/pyproject.toml`](../../build_tools/pyproject.toml) and the main
  suites under:
  - `build_tools/tests/`;
  - `build_tools/github_actions/tests/`;
  - `build_tools/packaging/python/tests/`; and
  - `build_tools/third_party/s3_management/tests/`.
- Call out independently configured or non-default suites, such as
  `build_tools/scan_tools/`, native package tests, and end-to-end packaging
  tests, so contributors do not assume that a single pytest invocation finds
  every Python test in the repository.

### Running Python tests locally and in CI

- Give a focused pytest example using TheRock's virtual environment, followed
  by the full command run from `build_tools/`.
- Explain that [`.github/workflows/unit_tests.yml`](../../.github/workflows/unit_tests.yml)
  runs the default suites with Python 3.12 on Ubuntu and Windows and uploads a
  coverage report.
- Note that these tests are CPU-only and should be the fastest feedback path
  for scripts used by build, test, package, and release automation.

### What to test in infrastructure scripts

- Separate deterministic decision-making from subprocess, filesystem, GitHub,
  and S3 boundaries so the core logic can be tested directly.
- Cover invalid inputs, missing data, partial failures, retry behavior, and
  platform-specific paths in addition to the happy path.
- Use temporary directories and representative small fixtures for artifact and
  package transformations.
- Mock external boundaries in unit tests, but retain an integration test for
  assumptions only the real tool or service can verify.
- For workflow helpers, test both the Python decision logic and invariants in
  the workflow YAML. Existing examples validate dispatch input contracts,
  matrix references, and the transitive set of reusable workflows.

## Testing build system changes

### Local configure and build loop

- Start with a GPU family that is relevant to the change and, when possible,
  matches locally available hardware.
- Use feature flags to configure the smallest useful component set, while
  preserving the dependency edges being changed.
- Build the affected project phase or directory rather than rebuilding all of
  ROCm. Link to the target model in [Build System](build_system.md) and the
  [Development Guide](development_guide.md).
- Use a component's `+expunge` target when changes to configure-time inputs or
  generated build state require a clean component rebuild.
- Build `+dist` or the relevant artifact targets when the change affects
  install rules, runtime dependencies, RPATHs, or artifact composition.
- Run `ctest --test-dir <build-dir>` for TheRock's build-integrity tests when
  `BUILD_TESTING` is enabled.
- Run topology validation when changing `BUILD_TOPOLOGY.toml` or its parser.

### What Multi-Arch CI covers

- Describe the progressively broader target selection for pull requests,
  pushes, and scheduled/release workflows.
- Point to
  [`amdgpu_family_matrix.py`](../../build_tools/github_actions/amdgpu_family_matrix.py)
  as the source of truth rather than copying a quickly stale architecture list
  into this page.
- Explain how pull request labels such as `gfx...` and `ci:run-all-archs` opt in
  to broader coverage. Automated submodule bump pull requests use the all-arch
  label.
- Explain how test labels, test filters, and manual dispatch inputs narrow or
  deepen testing. Link to [CI Behavior Manipulation](ci_behavior_manipulation.md)
  and [Test Filtering](test_filtering.md).

### What a green build does not prove

- A family can be built without tests executing on matching hardware.
- Matrix entries may be build-only, nightly-only, submodule-bump-only,
  sanity-only, or have no available test runner.
- Pull request CI does not cover every GPU family, operating system version,
  package format, optional feature, or build variant.
- A local build usually exercises one host environment and one selected target
  set; it does not reproduce CI's containers, self-hosted runners, or artifact
  transfer boundaries.
- The workflow summary and selected build configuration should be inspected to
  determine what actually ran before making a coverage claim.

## Testing ROCm components

### Component tests in TheRock

- Describe the build -> artifact upload -> artifact install -> GPU test flow.
- Explain that a sanity test runs before the parallel component test matrix in
  [`test_artifacts.yml`](../../.github/workflows/test_artifacts.yml).
- Document how
  [`fetch_test_configurations.py`](../../build_tools/github_actions/fetch_test_configurations.py)
  selects the component, required artifacts, platforms, runner, timeout, and
  shard count.
- Emphasize that tests run against installed artifacts. This also tests artifact
  composition and dependency declarations, not just component behavior in its
  source build tree.

### Component test tiers and the CTest contract

- Summarize the cumulative `quick`, `standard`, `comprehensive`, and `full`
  tiers and their intended trigger/cost tradeoffs. Keep the canonical policy in
  [Test Filtering](test_filtering.md).
- Explain the shared ROCm Libraries `test_categories.yaml` model and category,
  operating system, and GPU exclusion labels.
- Explain how
  [`test_runner.py`](../../build_tools/github_actions/test_executable_scripts/test_runner.py)
  discovers installed CTest labels and selects the category appropriate for
  `TEST_TYPE` and `AMDGPU_FAMILIES`.
- Cover sharding, timeouts, GPU resource constraints, expected failures, and
  documented exclusions as distinct mechanisms.

### hipBLASLt as a concrete example

- Show the progression from a focused native hipBLASLt test to TheRock
  integration testing:
  1. build and run the relevant test in the component's recommended standalone
     development loop;
  1. build hipBLASLt and its test artifacts through TheRock; and
  1. run the installed component suite through `test_artifacts.yml` on a
     matching GPU.
- Ground the example in
  `rocm-libraries/projects/hipblaslt/clients/tests/test_categories.yaml`, the
  `hipblaslt-test` executable, generated test data, and the required device
  library for the executing GPU.
- Demonstrate how the hipBLASLt smoke, quick, pre-checkin, nightly, and HMM
  categories map into TheRock's cumulative tiers without duplicating the full
  component documentation here.
- Generalize the same ownership and integration pattern to rocBLAS, rocFFT,
  MIOpen, and other components.

### Adding and debugging component tests

- Link to [Adding tests to TheRock](adding_tests.md) for test-matrix and adapter
  integration.
- Link to [Test Environment Reproduction](test_environment_reproduction.md)
  for downloading the exact artifacts from a CI run and recreating the test
  command locally.
- Link to [Test Debugging](test_debugging.md) for component-specific logging.

## Testing GitHub Actions workflows safely

### Test workflow changes at three levels

1. Run static checks, including YAML validation and `actionlint`.
1. Unit test extracted Python logic and add structural tests for contracts that
   static analysis cannot check.
1. Exercise the affected trigger and runner path in GitHub Actions.

Complex workflow logic should live in testable Python scripts instead of inline
shell. See the
[GitHub Actions style guide](style_guides/github_actions_style_guide.md).

### Match the live test to the trigger being changed

- Pull request and push triggers exercise their workflows automatically, but
  path filters and conditional jobs can still skip most of a run.
- `workflow_dispatch` supports focused try jobs with explicit GPU families,
  component labels, test tiers, and reusable build stages.
- Workflows using self-hosted runners can only be manually dispatched from a
  branch in the shared repository, not from a fork.
- Reusable `workflow_call` changes require checking both the called workflow's
  input contract and important callers.
- Scheduled release orchestration lives in `ROCm/rockrel`; a pull request run
  in TheRock does not execute that trigger by itself.

### Test CI workflows narrowly before expanding

- Start with one representative platform, GPU family, component, or package
  type when the workflow supports those inputs.
- Reuse known-good build stages or artifacts when the change only affects a
  downstream test or packaging stage.
- Expand to additional platforms, targets, or the full workflow when the change
  affects shared setup, matrices, artifact schemas, or cross-platform shell
  behavior.
- Verify job summaries and produced artifacts in addition to checking the final
  workflow conclusion.

### Test release workflows through `dev`

- Developer-triggered release workflows must use the `dev` release type.
- `dev` releases exercise nearly the same build, package, test, publish, and
  index-generation paths as nightly releases, while using development versions,
  IAM roles, and S3 buckets.
- Test the complete affected path: do not stop after a package uploads if the
  change also affects index generation, installation, runtime tests, or
  downstream framework builds.
- Never manually select nightly or prerelease destinations merely to test a
  change. Those are user-visible channels and require coordination with an
  infrastructure maintainer.
- Use the procedures in
  [GitHub Actions Debugging](github_actions_debugging.md#testing-release-workflows)
  and the bucket map in [S3 Buckets](s3_buckets.md).

### Workflow review checklist

- Trigger coverage, path filters, conditions, and concurrency behavior.
- Safe input defaults and compatibility between `workflow_dispatch` and
  `workflow_call` inputs.
- Least-privilege permissions, fork behavior, secrets, and OIDC role selection.
- Linux and Windows shell, quoting, path, and environment differences.
- Matrix expansion, job dependencies, result aggregation, and cancellation.
- Artifact producer/consumer contracts, retention, and baseline-run reuse.
- Correct release type, version, bucket, prefix, and package index.
- Idempotency and recovery behavior for uploads, copies, and promotions.

## Testing artifacts, packages, and releases

### Artifact structure and runtime sanity

- Validate manifests, expected files, platform conventions, and forbidden
  dependencies with `test_artifacts_structure.yml` and
  `tests/test_artifact_structure.py`.
- Run sanity tests after installing artifacts on a clean GPU runner before
  interpreting component failures.
- Test `dist` and merged artifact layouts when dependency declarations or
  installation rules change.

### Python packages and tarballs

- Build packages from artifacts, create a local index, install into a clean
  environment, and run `rocm-sdk test` plus affected runtime checks.
- Cover package metadata, dependency extras, version consistency, device-family
  selection, and Python versions relevant to the change.
- Distinguish tests of package-building logic from tests of the resulting
  installable package.

### Native Linux packages

- Build and install the affected Debian or RPM repositories in clean
  distribution containers.
- Explain the CI coverage for Ubuntu, RHEL, and SLES and identify distributions
  or versions not exercised by a given run.
- Validate repository metadata, dependencies, upgrade/removal behavior where
  relevant, and a basic runtime path after installation.

### Publishing and promotion

- Unit test version and index transformations with small representative package
  fixtures.
- Use dry-run or non-release destinations before allowing any mutation of
  release buckets.
- For an end-to-end change, verify published URLs by installing from the
  generated `dev` index rather than inspecting S3 contents alone.

## Higher-level and specialized validation

### Framework integrations

- Explain what ROCm wheel tests, PyTorch tests, and JAX tests add beyond
  component tests.
- Separate smoke tests used in routine CI from larger framework suites used on
  release or scheduled runs.
- Include framework builds when changing package metadata, exported CMake
  configuration, ABI-sensitive dependencies, or release orchestration.

### Functional tests and benchmarks

- Describe the extended functional and benchmark framework under
  `tests/extended_tests/`.
- Explain why correctness tests and performance regression tests require
  different baselines, runner stability, and failure interpretation.
- Identify which extended tests are gating, non-gating, or limited to dedicated
  scheduled runners.

### Sanitizers, security, and unusual configurations

- Link sanitizer workflows and [Sanitizers](sanitizers.md), including their
  narrower platform and trigger coverage.
- Mention CodeQL, gitleaks, and dependency/security checks as complementary to
  behavioral tests.
- Call out Windows, WSL ROCDXG, multi-GPU, HMM, and other specialized paths when
  a change touches their conditions or artifacts.

## Interpreting and maintaining test results

### Read what actually ran

- Inspect the configured family matrix, test tier, selected components, runner,
  skipped jobs, and expected failures in the workflow summary.
- Do not equate an overall green conclusion with execution of every matrix
  entry.
- Preserve run IDs and artifact URLs needed to reproduce failures.

### Reproduce before weakening coverage

- Re-run the printed reproduction command against the artifacts from the
  failing run.
- Reduce failures to the smallest component test and capture relevant logging.
- Treat timeouts and flaky tests as defects to diagnose. Do not silently remove
  them from a tier or add broad retries.
- Scope exclusions to the affected operating system or GPU and document the
  condition and owner.

### Keep tests useful over time

- Keep fast tiers deterministic and within their documented time budgets.
- Move tests between tiers deliberately as their cost or value changes.
- Minimize regression cases while retaining the behavior that exposed the bug.
- Fail clearly when prerequisites or expected test artifacts are missing.
- Remove expected-failure and exclusion entries when the underlying issue is
  fixed.

## Known coverage gaps

This section will track important limitations that contributors should consider
when choosing a test plan. Initial topics to document include:

- GPU families that are build-only or lack active test runners;
- differences between pull request, postsubmit, and release matrices;
- package coverage across Python versions and Linux distributions;
- release paths that can only be fully exercised by callers in `ROCm/rockrel`;
- non-gating or limited performance and extended-test coverage; and
- differences between local source-tree tests and tests of installed artifacts.

## Related documentation

- [CI Overview](ci_overview.md)
- [CI Behavior Manipulation](ci_behavior_manipulation.md)
- [Adding tests to TheRock](adding_tests.md)
- [Test Filtering](test_filtering.md)
- [Test Environment Reproduction](test_environment_reproduction.md)
- [Test Debugging](test_debugging.md)
- [GitHub Actions Debugging](github_actions_debugging.md)
- [Build System](build_system.md)
- [Artifacts](artifacts.md)
- [S3 Buckets](s3_buckets.md)
- [Python Packaging](../packaging/python_packaging.md)
- [Native Packaging](../packaging/native_packaging.md)

External projects with useful testing documentation patterns:

- [LLVM Testing Infrastructure Guide](https://llvm.org/docs/TestingGuide.html)
- [PyTorch unit testing guide](https://github.com/pytorch/pytorch/blob/main/CONTRIBUTING.md#unit-testing)
