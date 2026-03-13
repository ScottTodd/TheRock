# Component Path Discovery

This document describes how ROCm components should locate each other at build
time and at runtime. It is the authoritative reference for path resolution
patterns in TheRock and its sub-projects.

## Core Principles

1. **No hardcoded absolute paths.** References to `/opt/rocm`, `/usr/local`,
   or any other fixed filesystem location are banned. They break relocatable
   installs, containerized builds, and developer workflows where ROCm lives in
   a non-standard location.

1. **Self-contained packages.** Tools and libraries that are built and installed
   together in the same distribution tree must be able to find each other using
   only information embedded at install time — specifically, paths relative to
   their own installed location. No ambient state required.

1. **No environment-variable assumptions for intra-package discovery.**
   Environment variables like `ROCM_PATH`, `HIP_PATH`, and `ROCM_HOME` must
   never be required for components within the same install tree to find each
   other. These variables are a user-facing convenience for pointing external
   tools at a ROCm installation, not an internal wiring mechanism.

1. **Side-by-side installs must work.** Users may have multiple ROCm
   installations coexisting — e.g., different versions in separate Python
   venvs, or multiple tarball extractions on the same machine. Any reliance
   on global state (environment variables, global config files, hardcoded
   paths) breaks this. Each install tree must be fully self-describing so
   that the "active" one is determined solely by which tree's tools or
   libraries are being invoked.

1. **User-facing discovery uses tool commands, not env vars.** External
   consumers (build scripts, CI pipelines, Python packages) should discover
   paths via tool commands like `hipconfig --path`, `hipconfig --rocmpath`, or
   `rocm-sdk path --root`. These tools compute the answer from their own
   installed location, so they work regardless of where the tree is rooted.

## Build-Time Patterns (TheRock Super-Project)

During a TheRock build, sub-projects are isolated from each other and from the
host system. The super-project controls how dependencies are resolved.

### How sub-projects find dependencies

1. **`find_package` via dependency provider.** The super-project installs a
   [CMake dependency provider](https://cmake.org/cmake/help/latest/command/cmake_language.html#dependency-providers)
   (see `cmake/therock_subproject_dep_provider.cmake`) that intercepts all
   `find_package()` calls. Packages declared via
   `therock_cmake_subproject_provide_package()` are resolved exclusively from
   the super-project's staging directories. Everything else falls through to
   system resolution.

1. **`CMAKE_PREFIX_PATH` injection.** Each sub-project's generated `_init.cmake`
   prepends the unified install directory to `CMAKE_PREFIX_PATH`. Combined with
   the dependency provider, this ensures sub-projects find sibling packages
   without knowing absolute paths.

1. **Toolchain file.** Each sub-project receives a generated `_toolchain.cmake`
   that configures compilers and platform settings. Sub-projects must not
   search for compilers outside this mechanism.

### Environment variable sandboxing

TheRock unsets dangerous environment variables when invoking sub-project builds
to prevent sandbox escapes:

```
cmake -E env --unset=ROCM_PATH --unset=ROCM_DIR --unset=HIP_PATH --unset=HIP_DIR -- cmake --build ...
```

This is a defense-in-depth measure. Sub-projects should not rely on these
variables in the first place, but unsetting them catches cases where upstream
code has not yet been fixed.

### Anti-patterns at build time

These anti-patterns have caused real build failures. See
[#670](https://github.com/ROCm/TheRock/issues/670) for detailed examples of
each on Windows, where an existing HIP SDK install at
`C:\Program Files\AMD\ROCm\6.2\` caused sandbox escapes during TheRock builds.

| Anti-pattern                                          | Why it's wrong                                                                               | Correct approach                                                   |
| ----------------------------------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| `set(FOO_DIR "/opt/rocm/...")`                        | Hardcoded path; breaks on any non-default install                                            | Use `find_package()` — the dependency provider resolves it         |
| `set(HIP_PATH $ENV{HIP_PATH})`                        | Reads env var from host; picks up wrong install and may introduce backslash paths on Windows | Use `find_package(hip)` or paths from super-project                |
| `find_program(FOO foo)` without hints                 | Searches `PATH`; may find the wrong version                                                  | Compute relative to `CMAKE_CURRENT_LIST_DIR` or use a known prefix |
| `execute_process(COMMAND hipconfig ...)` during build | Runs host tool, not the one being built                                                      | Pass the value as a CMake variable from the super-project          |
| Probing `C:\Program Files\AMD\ROCm` or similar        | Finds stale/partial system installs; fails with empty directories                            | Use only paths provided by the super-project                       |

## Install-Time Patterns (Generated CMake Config Files)

When a sub-project generates a `foo-config.cmake` (or `foo-config.cmake.in`
template), it must produce a config that works from any install prefix.

### Relative path computation

CMake config files should derive all paths from their own installed location.
The general idea:

```cmake
# foo-config.cmake.in
@PACKAGE_INIT@

# Compute the install prefix relative to this file's location.
# If this file is at <prefix>/lib/cmake/foo/foo-config.cmake, then:
get_filename_component(_IMPORT_PREFIX "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)

# Now use _IMPORT_PREFIX for everything:
set_and_check(foo_INCLUDE_DIR "${_IMPORT_PREFIX}/include")
set_and_check(foo_BIN_DIR "${_IMPORT_PREFIX}/bin")
```

CMake's
[`configure_package_config_file()`](https://cmake.org/cmake/help/latest/module/CMakePackageConfigHelpers.html)
generates this kind of relative-path logic automatically. Prefer using that
helper over hand-rolling templates when writing new configs.

> **TODO:** Validate this pattern against a real sub-project in the tree. We
> need to identify a sub-project that already does this correctly and use it
> as the reference example — or fix one up as a model. See the
> [compliance audit](#compliance-audit) section below.

### Executable paths in config files

If a config file needs to reference a sibling executable (e.g., `hip-config.cmake`
referencing `hipconfig`), the path must be computed relative to the config
file's location, **not** baked in from a build-time variable that may have been
an absolute path:

```cmake
# GOOD: relative to this config file's install location
get_filename_component(_PREFIX "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)
set(hip_HIPCONFIG_EXECUTABLE "${_PREFIX}/bin/hipconfig")

# BAD: baked-in absolute path from build time
set(hip_HIPCONFIG_EXECUTABLE "/opt/rocm/bin/hipconfig")

# BAD: searching PATH — may find the wrong installation
find_program(hip_HIPCONFIG_EXECUTABLE hipconfig)
```

### RPATH for shared libraries

Libraries must find their runtime dependencies via relative RPATH, not by
relying on `LD_LIBRARY_PATH` or hardcoded absolute RPATH entries.

TheRock configures this via `INTERFACE_INSTALL_RPATH_DIRS` in sub-project
declarations (see `build_system.md`). The resulting RPATH entries are relative
to the library's own location (e.g., `$ORIGIN/../lib` on Linux), making the
install tree fully relocatable.

## User-Facing Path Discovery

External consumers of ROCm (downstream projects, Python packages, CI scripts)
need to locate the ROCm install tree. The supported mechanisms are:

### Tool commands (preferred)

| Command                | Returns             | Notes                          |
| ---------------------- | ------------------- | ------------------------------ |
| `hipconfig --path`     | HIP install prefix  | Computes from own location     |
| `hipconfig --rocmpath` | ROCm install prefix | Computes from own location     |
| `hipconfig --platform` | `amd` or `nvidia`   | Platform detection             |
| `rocm-sdk path --root` | SDK root            | For Python `rocm-sdk` packages |

These commands derive paths from their own installed location, so they work
correctly for any install prefix without environment variables.

### Running tools from PATH (for scripts and end users)

After installing ROCm and adding its `bin/` directory to `PATH`, users can
invoke tools like `hipcc`, `amdclang`, or `hipconfig` directly. Each tool is
responsible for figuring out the rest of the install tree from its own location
— the user does not need to set any additional environment variables.

This is the expected workflow for end users and CI scripts that compile HIP
programs:

```bash
# User adds ROCm to PATH once:
export PATH=/path/to/rocm/bin:$PATH

# Then just uses the tools — they find everything else on their own:
hipcc my_kernel.cpp -o my_kernel
amdclang++ -x hip my_kernel.cpp -o my_kernel
```

The key invariant is that tools must resolve sibling tools and libraries
relative to their own location (typically `../lib`, `../include`, etc.), never
by reading `ROCM_PATH` or similar environment variables. This ensures that
whichever install tree's `bin/` directory appears first on `PATH` is the one
that gets used consistently — critical for side-by-side installs.

### `find_package` (for CMake consumers)

Downstream CMake projects should use:

```cmake
find_package(hip REQUIRED CONFIG)
target_link_libraries(myapp hip::host)  # or hip::device
```

The consumer points CMake at the install tree via `-DCMAKE_PREFIX_PATH=<prefix>`
or by adding the prefix to `CMAKE_PREFIX_PATH` in their CMake configuration.
No environment variables are needed.

### Environment variables (last resort)

`ROCM_PATH`, `HIP_PATH`, and `ROCM_HOME` exist for backward compatibility
with legacy build scripts that predate the modern discovery mechanisms. They
should be considered a user-facing convenience, not a dependency:

- ROCm components must **never require** these to be set in order to function.
- Components must **never read** these for intra-package discovery.
- Downstream projects should prefer `find_package` or tool commands over env
  vars.
- Legacy `FindHIP.cmake` checks these as a fallback search path, which is
  acceptable for backward compatibility but not the recommended path forward.

## Case Study: `HIP_PLATFORM` Detection

This section documents a real design issue to illustrate the principles above.

### Problem

The `hip-config.cmake.in` template in `rocm-systems` auto-detects
`HIP_PLATFORM` by running `hipconfig --platform`. However, the path to
`hipconfig` was configured via `HIPCC_BIN_DIR`, which defaulted to
`/opt/rocm/bin` — a hardcoded absolute path.

When TheRock builds HIP, it sets `HIPCC_BIN_DIR` to empty to prevent the
build from "escaping" the sandbox and finding host tools. This caused
`HIP_INSTALLS_HIPCC` to be set to `OFF`, which meant the generated
`hip-config.cmake` never set `hip_HIPCONFIG_EXECUTABLE`, breaking
`HIP_PLATFORM` auto-detection for all downstream consumers.

### Wrong fix: PATH fallback

Adding `find_program(hipconfig)` as a fallback (searching `PATH`) violates
principle 2 (self-contained packages). The behavior becomes dependent on what
else is installed on the system. A user with both a system ROCm and a
TheRock build could get the wrong `hipconfig`, producing incorrect results
silently.

### Better fix: relative path computation

The generated `hip-config.cmake` should compute the `hipconfig` path relative
to its own installed location:

```cmake
# Compute prefix from this file's location (lib/cmake/hip/hip-config.cmake)
get_filename_component(_HIP_PREFIX "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)
set(hip_HIPCONFIG_EXECUTABLE "${_HIP_PREFIX}/bin/hipconfig")
```

This requires no build-time detection of `HIPCC_BIN_DIR`, no environment
variables, and no PATH search. The config file knows where `hipconfig` is
because it knows where it was installed relative to itself.

On the super-project side, TheRock may still need to override
`HIP_INSTALLS_HIPCC` as a cache variable (see TheRock PR #1410) so that the
template's conditional block emits the executable path. The key point is that
the emitted path must be relative, not absolute.

## Checklist for Sub-Project Authors

When adding or modifying a sub-project's CMake config:

- [ ] No hardcoded absolute paths in generated config files
- [ ] All sibling tool/library paths computed relative to `CMAKE_CURRENT_LIST_DIR`
- [ ] No `find_program()` calls that search `PATH` for tools in the same package
- [ ] No reads of `ROCM_PATH`, `HIP_PATH`, or `ROCM_HOME` for internal wiring
- [ ] RPATH uses `$ORIGIN`-relative entries (Linux) or `@loader_path` (macOS)
- [ ] `find_package()` used for inter-project dependencies (resolved by
  super-project dependency provider at build time)
- [ ] Config file works when installed to an arbitrary prefix (test by
  installing to a temp directory and running `find_package` from there)

## Compliance Audit

This section tracks which sub-projects comply with these requirements and which
need to be fixed.

> **TODO:** Run a project-wide audit to classify each sub-project's CMake
> config generation and path discovery patterns. The goal is to identify:
>
> 1. **Compliant sub-projects** — already use relative path computation, no
>    hardcoded paths, no env var reads. Use these as the reference model for
>    fixing non-compliant projects.
> 1. **Non-compliant sub-projects** — use hardcoded `/opt/rocm` defaults,
>    read `HIP_PATH`/`ROCM_PATH` env vars, probe system directories, or
>    search PATH for sibling tools. These must be fixed.
> 1. **Severity** — which violations cause active build failures or
>    user-facing bugs in distributed packages vs. which are latent but still
>    non-compliant.

### Open violations

- `hip-config.cmake.in` (`rocm-systems/projects/clr/hipamd/`):
  `HIPCC_BIN_DIR` defaults to `/opt/rocm/bin`; PATH fallback added in
  rocm-systems PR #3150. Users of distributed packages hit broken
  `HIP_PLATFORM` detection unless they manually pass `-DHIP_PLATFORM=amd`.
  ([#1402](https://github.com/ROCm/TheRock/issues/1402))

### Fixed violations (for reference)

- hipSOLVER: read `$ENV{HIP_PATH}`, fell back to `/opt/rocm/hip`.
  On Windows, picked up stale system HIP SDK paths with backslashes,
  causing CMake parse errors and wrong include directories.
  ([#670](https://github.com/ROCm/TheRock/issues/670), closed — mitigated by
  env var unsetting in TheRock)
- Tensile / tensilelite: probed `C:\Program Files\AMD\ROCm` for toolchain
  validation. Failed with empty directories from partial uninstalls.
  ([#683](https://github.com/ROCm/TheRock/issues/683), closed)

## Alternatives Considered

### Environment variables as primary discovery

Rejected. Environment variables are ambient global state — they create implicit
coupling between components, make builds non-reproducible, and silently produce
wrong results when stale or misconfigured. They remain as a backward-compatible
fallback for user-facing tools, but components within the same install tree must
not rely on them.

### Hardcoded default paths with override variables

Rejected. Patterns like `set(FOO_DIR "/opt/rocm" CACHE PATH "...")` appear
convenient but create a maintenance burden: every consumer must remember to
override, and forgetting to override produces silent failures or picks up the
wrong installation. Relative path computation eliminates this class of bug
entirely.

### PATH-based tool discovery

Rejected for intra-package use. `find_program()` searching PATH is appropriate
for truly external tools (e.g., finding `python3` or `git`), but not for tools
that ship in the same distribution tree. PATH ordering is fragile, environment-
dependent, and can silently resolve to a different installation.
