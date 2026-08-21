# Modular build status

Rush builds Modular's public repository (modular/modular) from unmodified
sources — whole-repo, not a curated slice — and runs its Mojo stdlib test
corpus. Validation runs against pinned nightly trees on two hosts: pin
`cc7155d854a0` on a 96-core x86-64 box (whole-repo sweep) and pin
`4e87649567` on an AMD W7900 host (stdlib corpus + GPU work).

## Whole-repo sweep

The census enumerates every label in the repo (~17.6k), Bazel builds the
configurable non-GPU subset with `--keep_going` (4,175 targets succeed on a
GPU-less host), and rush builds the same 4,175-label ledger:

- **Rush builds 4,113 of 4,175 (98.5%).**
- mojoc byte-parity holds for 29 of 37 comparable mojo_library artifacts;
  the 8 diffs are kernel packages consuming absolute bitcode-library paths
  (fix queued: exec-root-relative $(location) expansion).
- The 62 remaining failures: the unwired `py_*` rule stack (38 labels via
  `modular_py_binary`/`modular_py_test`), mojo module-resolution tails
  (`matmul_rs`, `_hal`), and singletons (one circular-dependency report,
  one generated-source target).

## What works

- **Bzlmod resolution.** Rush reads Bazel's module graph and repository
  mappings, fetches canonical repos (`@mojo`, `@rules_mojo`), and resolves
  apparent names per-repository. MODULE.bazel-only trees bypass every legacy
  WORKSPACE heuristic.
- **The Mojo rule stack.** `mojo_library`, `mojo_binary`, and `mojo_test`
  execute for real: precompile with the fetched mojoc, object compile with
  staged sources (Bazel-sandbox parity), link with the fetched clang, lld,
  sysroot, and the five Mojo runtime libraries.
- **Byte parity.** `//mojo/stdlib/std:std` produces a `std.mojoc`
  SHA-256-identical to Bazel's on every validated pin.
- **The stdlib test corpus.** All 335 non-GPU test targets batch-build in one
  invocation. 264 tests verify green at runtime: 217 plain `mojo_test`
  binaries, 38 FileCheck-verified, 9 expect-crash tests that trap and
  FileCheck-verify. The 23 remaining failures are test-environment gaps
  (hermetic Python, TEST_* env), not compile or link failures.
- **GPU compile and run.** `mojo_binary` honors accelerator targets;
  Modular's tiled_matmul builds and passes GPU validation on an H100 with
  byte-identical output to Bazel across ten alternating runs (median 1.010 s
  vs Bazel 1.020 s).
- **Speed.** Warm no-op over the 335-target corpus: 0.02 s (Bazel: 0.33 s).
  Single-file incremental rebuild + re-run: 2.0 s (Bazel: 4.7 s).

## What's left — do these

- **Wire the `py_*` rule stack.** The largest remaining cluster (38 labels)
  is `modular_py_binary`/`modular_py_test` chains; py rules exist but are
  unwired. This is the same gap as TensorFlow's Python slice.
- **Relativize $(location) expansion.** Mojo copt expansion currently emits
  absolute artifact paths; Bazel uses exec-root-relative. This is the root
  of the 8 mojoc byte-parity diffs in kernel packages.
- **Resolve the mojo module-resolution tails.** `builtin_kernels` can't
  locate `matmul_rs`, `_mojo_module` can't locate `_hal` — compare -I sets
  against Bazel aquery for these shapes.
- **Honor `target_compatible_with`.** Skip platform-incompatible targets
  (macOS-only stdlib tests) instead of failing their compiles.
- **Add an llvm-lit test runner.** 48 stdlib tests (including every
  compile-fail negative test) are lit-driven. Drive `llvm-lit` + FileCheck
  the way `bazel/internal/lit.bzl` does.
- **Provide the hermetic test environment.** Python-interop tests need the
  rules_python toolchains and `mojo_test_environment` env
  (`COMPUTED_IMPORT_PATH`, `COMPUTED_LIBS`); os/pathlib tests need Bazel's
  TEST_* contract. 23 already-building tests turn green with this.
- **Wire `mojo_test` into `rush test`.** `rush test` must classify Mojo test
  targets, execute them with harness semantics (FileCheck, expect_crash,
  expect_fail, runtime args), and report per-test results. Today binaries are
  executed by an external harness script.
- **Execute Starlark-action rules.** `modular_versioned_expand_template`
  (generated test sources) needs real `ctx.actions` execution.
- **Auto-detect GPU toolchains.** Rush needs `RUSH_MOJO_TARGET_ACCELERATOR`
  set by hand; detect GPUs like `mojo_host_platform.bzl` does (rocm-smi,
  amd-smi, nvidia-smi) and pick the accelerator automatically.
- **Discover the Mojo toolchain without env overrides.** Resolve the fetched
  `rules_mojo` toolchain from the module graph in every layout; `RUSH_MOJO`
  must remain an override, not a requirement.

## Upstream findings worth reporting to Modular

- max/kernels GPU tests fail on gfx1100 (RDNA3) under Bazel itself at the
  validated pin: `test_matmul` instantiates `matmul_kernel_tc` with
  `MMA_K=4` and trips `copy_from should move data of the same size, getting
  dst size 4 and src size 8` in `layout_tensor.mojo`.
- GPU detection in `rules_mojo` is PATH-dependent (`rctx.which("rocm-smi")`);
  a Bazel server started without `/opt/rocm/bin` in PATH silently declares a
  GPU-less host platform.

## Reproduce

```sh
# in a Modular checkout with a Bazel-materialized output base
export RUSH_MOJO=<output_base>/external/rules_mojo++mojo+mojo_toolchain_linux_x86_64/bin/mojo
rush build //mojo/stdlib/std:std
sha256sum rush-out/mojo/stdlib/std/std.mojoc bazel-bin/mojo/stdlib/std/std.mojoc
```
