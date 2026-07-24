# Testing overview working appendix

> [!NOTE]
> This local working file preserves material from the initial outline while
> `testing_overview.md` is reorganized. It is not intended for submission.

## Recent structure and content notes

These notes capture ideas discussed while reorganizing the main document. They
are working material, not proposed final wording.

### Proposed top-level progression

1. **Testing principles:** Practices that apply across TheRock, ROCm
   subprojects, and the assembled product.
1. **Testing changes to TheRock:** Python tools, CMake and build logic, GitHub
   Actions workflows, packaging, release infrastructure, and framework
   integration tooling.
1. **Testing ROCm subproject changes with TheRock:** Building subprojects
   through the super-project and running their tests through standardized,
   locally reproducible interfaces.
1. **Validating assembled ROCm:** Artifacts, installed packages, component
   tests, supported GPU hardware, downstream frameworks, and release
   pipelines.
1. **Maintaining reliable testing infrastructure:** Safely changing and
   operating the runners and services that produce test results.

The first four sections progress from common practices, to code maintained in
TheRock, to integrated subprojects, and finally to the product delivered to
users. The infrastructure section covers the availability, reliability, and
observability needed to trust all of those results.

### Reusable testing strategy profile

The subsections under "Testing changes to TheRock" could follow a standard
profile. Other ROCm subprojects could reuse the same structure in their own
testing strategy documents.

| Attribute         | Details to document                                                  |
| ----------------- | -------------------------------------------------------------------- |
| Code under test   | Files, directories, workflows, or produced artifacts                 |
| Test location     | Where the checks and tests are implemented                           |
| Purpose           | The behavior or property in which the tests provide confidence       |
| Environment       | Required OS, build, package installation, GPU, or external service   |
| Local entry point | How the same coverage is run during development                      |
| CI coverage       | Workflows and configurations that run the test                       |
| Frequency         | Presubmit, postsubmit, nightly, scheduled, on demand, or release     |
| Blocking status   | Informational or required                                            |
| Cost and capacity | Typical runtime, sharding, and scarce runner requirements            |
| Limitations       | Important behavior or configurations that the tests do not establish |

Keep environment, frequency, and cost separate. A test may be fast but require
scarce GPU hardware, or it may run on a CPU machine but take several hours.
Either property can determine whether coverage runs presubmit, nightly, or on
demand.

After the profile, each area can explain:

- how the code should be structured for testability;
- which behavior can be tested quickly on commonly available development
  machines;
- which boundaries require a real build, workflow, package, service, or GPU;
  and
- one or two concrete examples from TheRock.

The profile should describe current coverage and known limits, not only the
intended design.

### Separate test layers from execution stages

Do not conflate what a test validates with where or how often it runs. Static
checks, unit tests, build tests, package tests, and system tests are testing
layers. Local development, presubmit, on-demand, nightly, and prerelease are
execution stages. Unit and integration tests may run locally, in CI, or both.

A testing-layer table could document:

| Layer                       | Primary confidence provided                      | Typical requirements             |
| --------------------------- | ------------------------------------------------ | -------------------------------- |
| Static checks               | Source and configuration meet mechanical rules   | CPU only                         |
| Unit tests                  | Isolated logic behaves as expected               | Usually CPU only                 |
| Build and integration tests | Components work across real boundaries           | Build environment, sometimes GPU |
| Package and system tests    | Installed ROCm behaves as users expect           | Clean installation and often GPU |
| Release tests               | Publishing and orchestration work across systems | Live services and credentials    |

An execution-stage table could separately document:

| Stage             | Coverage policy                                          | Time and capacity considerations              |
| ----------------- | -------------------------------------------------------- | --------------------------------------------- |
| Local development | Relevant coverage selected during development            | Seconds to hours; available local environment |
| Presubmit         | Fast, high-signal required coverage                      | Bounded feedback time and sufficient capacity |
| On demand         | Change-specific configurations                           | Scarce hardware or unusual variants           |
| Nightly/scheduled | Broader configurations and longer test suites            | Longer budgets and all available hardware     |
| Prerelease        | Highest-confidence validation of release-relevant inputs | Potentially several hours                     |

The detailed execution stages can reference the existing `quick`, `standard`,
`comprehensive`, and `full` test-filter categories and their time budgets.

Coverage can also expand based on change risk. Submodule updates, compiler
updates, and changes with a wide build-system impact are candidates for deeper
or broader validation. Changes affecting a particular GPU target or build
variant should be able to request the corresponding opt-in coverage.

### Testing ROCm subprojects through TheRock

TheRock provides integration coverage for subprojects without replacing their
native unit and component testing. Useful principles include:

- build subprojects through the super-project to validate dependency, install,
  and packaging relationships;
- use standardized CTest categories, GPU labels, and installed test artifacts;
- keep component-specific CI adapters minimal;
- use the same test entry points locally and in CI when their environment
  requirements are available;
- make required environment setup explicit, deterministic, and shared; and
- avoid hidden assumptions about a particular CI runner or filesystem layout.

`build_tools/github_actions/test_executable_scripts/test_runner.py` represents
the desired standardized direction. Ad hoc setup such as
`copy_dlls_exe_path()` in `test_hiptests.py` is a useful counterexample: it
depends on implicit directory layout, mutates the test directory, and suppresses
copying failures. Some integration tests inherently need environment setup, but
that setup should not exist only inside CI or a component-specific adapter.

### Maintaining reliable testing infrastructure

TheRock depends on self-hosted runners, build containers, caches, dependency
mirrors, artifact and package storage, credentials, and other external
services. The testing overview should cover the practices needed to trust these
systems without becoming a provider-specific operations manual.

#### Validate infrastructure changes

Test changes against development or isolated environments when possible. This
includes changes to runner images and configuration, build containers, caches,
mirrors, storage, credentials, and external services.

#### Roll out changes progressively

Some infrastructure behavior cannot be established before deployment. Introduce
such changes to a limited runner pool, workflow population, or share of traffic;
compare their behavior with the existing configuration; expand only after
establishing confidence; and retain a rollback path.

#### Make system health observable

Automated results are only trustworthy when the systems producing them are
observable.

- Follow consistent logging practices in build and CI/CD infrastructure.
  Record relevant commands, configuration, environment details, stage
  boundaries, and failure context without exposing secrets.
- Preserve logs and related diagnostics long enough to investigate failures,
  and make them accessible to contributors who need to reproduce or triage
  them.
- Run health checks for build and test runners before expensive work. Validate
  prerequisites such as GPU and driver health so infrastructure failures can be
  distinguished from failures in the code under test.
- Health checks must enforce their results rather than merely print
  diagnostics. PR
  [#6604](https://github.com/ROCm/TheRock/pull/6604) is a concrete example: a
  driver/GPU sanity check printed a HIP failure but did not propagate it, making
  a broken runner appear to be a component failure later in the job.
- Monitor workflow and nightly health, runner availability and queue time,
  build and test duration, failure and flake rates, cache and storage
  reliability, build performance, binary size, and downstream-reported
  results.

Quartz can provide a common data path for TheRock results, downstream
notifications and feedback, and dashboard analytics. Detailed architecture
belongs in `docs/rfcs/RFC0011-Quartz-CICD-Datahub.md`.

#### Keep test results trustworthy

Separate product failures from infrastructure failures, avoid silent retries
that hide instability, track flakes instead of normalizing them, and ensure
that missing or failed reports reach a terminal state.

The section should explicitly exclude detailed service configuration,
operational ownership, alert thresholds, incident response, and
provider-specific procedures. Those belong in dedicated operational
documentation.

## Testing strategy

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

### Favor fast, representative local tests

Fast tests shorten development cycles and make failures easier to reproduce and
debug. Where possible, build, test, packaging, and release logic should be
structured so that its important decisions can be tested on a CPU-only
developer machine without building ROCm, reserving a GPU runner, or accessing a
live service.

The fastest test is only useful when it represents the behavior that matters.
Unit tests should exercise observable behavior through appropriately scoped
interfaces and realistic data rather than reimplementing the code's logic in
the test. A focused regression test should be added for a bug fix whenever
practical. These tests can then run for every change, across both Linux and
Windows where appropriate.

### Add integration coverage where unit tests stop

Unit tests cannot establish every property that matters to TheRock. Mocks do
not prove that a GitHub Actions expression is valid, that a package contains the
right shared libraries, that those libraries load on a clean system, or that a
component works on real GPU hardware.

Integration tests should cover these real boundaries. For example, TheRock
builds components on CPU machines, assembles artifacts and packages, installs
them on separate test machines, and runs component or framework tests on
matching GPUs. This is slower and more expensive than a unit test, but it
provides confidence that isolated pieces work together in the form users
receive.

The two layers should reinforce each other: use fast tests for detailed
behavior and failure cases, then use a smaller number of end-to-end tests for
the assumptions that only real tools, packages, services, and hardware can
verify.

### Use the mechanism that matches the requirement

Different checks belong in different tools:

- Formatting and mechanically enforceable source conventions belong in
  pre-commit hooks. For example, a project-wide line-length rule should be a
  formatter or lint hook, not a Python unit test or PR Policy Bot rule.
- Deterministic behavior in Python scripts and functions belongs in unit tests.
- Cross-file or workflow contracts that a general-purpose linter does not
  understand can be enforced with repository-specific unit tests.
- Repository contribution policies belong in branch protection or the PR
  Policy Bot when they require pull request metadata or organization-level
  state.
- Runtime behavior of workflows, packages, and GPU software must ultimately be
  exercised in the corresponding real environment.

These mechanisms can be complementary. The `actionlint` pre-commit hook catches
many syntax and expression errors in GitHub Actions workflows, while
[`workflow_dispatch_inputs_test.py`](../../build_tools/github_actions/tests/workflow_dispatch_inputs_test.py)
checks a TheRock-specific caller/callee input contract that `actionlint` cannot
validate.

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

### Know what the available automation does not cover

TheRock cannot test the Cartesian product of every configuration for every
change. Relevant dimensions include:

- operating system and distribution;
- GPU family and exact GPU target;
- build variant, such as release or a sanitizer build;
- component test tier;
- source build, artifact, wheel, native package, or tarball layout;
- pull request, postsubmit, scheduled, or release trigger; and
- `ci`, `dev`, nightly, or prerelease storage and versioning behavior.

Developers should understand which of these dimensions are exercised by the
available local and CI tests. When an affected feature or configuration is not
enabled in CI, the author is responsible for validating it through an
appropriate local build or purpose-built workflow run.

## TODO: Static checks and Python unit tests

### Pre-commit checks

- Explain that all commits must pass the repository's pre-commit hooks and that
  these checks are the standard enforcement point for formatting, source
  hygiene, and workflow linting.
- Describe the repository's formatting, file validation, and `actionlint`
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
- Use real files in temporary directories and representative small fixtures for
  filesystem, archive, artifact, and package transformations. These operations
  are usually cheap, deterministic, and clearer than deeply mocked tests.
- Mock network services such as GitHub and S3 when testing local decisions,
  request construction, and error handling. Do not mock so much of the code
  under test that the test only verifies configured return values.
- Put expensive or environment-dependent subprocess calls behind a narrow
  boundary. Unit test the command and surrounding decisions, use the real tool
  when it is cheap and reliably available, and retain an integration test for
  assumptions that only the actual tool can verify.
- Prefer dependency injection or small boundary functions over patching many
  implementation details. Tests should remain valid through reasonable
  refactoring.
- For workflow helpers, test both the Python decision logic and invariants in
  the workflow YAML. Existing examples validate dispatch input contracts,
  matrix references, and the transitive set of reusable workflows.
- Connect this guidance to the
  [Python style guide's testing standards](style_guides/python_style_guide.md#testing-standards)
  and expand both pages consistently as the standards mature.

## TODO: Testing build system changes

### Source builds are the primary validation

- Build system changes are expected to be validated with a source build. Unit
  tests for CMake helpers or topology parsers can provide faster feedback, but
  they do not replace configuring and building the affected path.
- The important question is whether the selected configuration exercises the
  behavior being changed, not whether a particular example command was copied
  verbatim.
- A targeted build is sufficient when it preserves the relevant dependency and
  install relationships. Changes to shared configuration, dependency edges, or
  artifact composition may require a broader build.
- When a feature, platform, option, or build variant is not enabled in CI, the
  contributor is responsible for ensuring that configuration continues to
  build.
- Link to [Build System](build_system.md) and the
  [Development Guide](development_guide.md) for commands and build-target
  mechanics rather than duplicating them here.

### Compare local and CI configurations

- Explain how to inspect the effective CMake options, enabled features, target
  families, build variant, and platform used by CI.
- Encourage contributors to compare those values with their local build and
  identify affected configurations that neither environment covers.
- Note that a successful build validates configuration and compilation, while
  runtime behavior, installed layouts, and GPU execution require later testing
  layers.

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

## TODO: Testing ROCm components

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
- Use specific component behavior as examples throughout this section. For
  instance, hipBLASLt maps smoke, quick, pre-checkin, nightly, and HMM test
  categories into TheRock's cumulative tiers; its installed tests also require
  generated test data and a device library for the executing GPU.
- Cover sharding, timeouts, GPU resource constraints, expected failures, and
  documented exclusions as distinct mechanisms.

### Adding and debugging component tests

- Link to [Adding tests to TheRock](adding_tests.md) for test-matrix and adapter
  integration.
- Link to [Test Environment Reproduction](test_environment_reproduction.md)
  for downloading the exact artifacts from a CI run and recreating the test
  command locally.
- Link to [Test Debugging](test_debugging.md) for component-specific logging.

## TODO: Testing GitHub Actions workflows safely

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

## TODO: Testing artifacts, packages, and releases

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

## TODO: Higher-level and specialized validation

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

## TODO: Interpreting and maintaining test results

### Read what actually ran

- Inspect the configured family matrix, test tier, selected components, runner,
  skipped jobs, and expected failures in the workflow summary.
- Do not equate an overall green conclusion with execution of every matrix
  entry.
- Preserve run IDs and artifact URLs needed to reproduce failures.
- Avoid listing routine automatically enforced formatting or lint checks as if
  they were substantive manual validation. Record additional evidence when it
  helps a reviewer understand an exceptional case, such as reproducing a bug,
  validating a fix on specific hardware, relying on CI for an unavailable
  configuration, or exercising a release workflow manually.

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

## TODO: Known coverage gaps

This section will track important limitations that contributors should consider
when evaluating coverage. Initial topics to document include:

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
