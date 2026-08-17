# TensorFlow build status

Rush builds TensorFlow from unmodified upstream sources and runs its C++
test corpus. The standard is Bazel parity: if it builds with Bazel it must
build with Rush, and every snag is either a rush bug (fix in rush) or an
upstreamable TF commit — never a hack script.

## What works

- **TF 2.15 CPU, certified.** Rush builds TF 2.15 and passes 463/463 of the
  `bazel test --test_tag_filters=-gpu` tf_cc_test set (the 3 remaining
  targets are requires-gpu). This includes proto compilation, op-wrapper
  codegen (`tf_gen_op_wrappers_cc`), alwayslink semantics, and full
  cc_binary/cc_test link closures with `--start-group` back-reference
  resolution.
- **libtensorflow_cc.so.** The shared library links, is dlopen-loadable
  (RTLD_NOW), and drives real workloads.
- **GPU / ROCm.** Rush builds and runs GPU tf_cc_tests on ROCm (TF 2.17,
  gfx1100): dlopen-loadable .so, GPU-test macro expansion, compile/link
  parity including response files and the ROCm runtime. A TF-scale GPU
  cc_binary (4056 targets) builds and converges on-device.
- **Configuration fidelity.** `--define` flows into `config_setting` /
  `select()` exactly like Bazel, and the parse cache is keyed by the defines
  fingerprint.
- **Differential correctness harness.** The aquery-based incremental +
  hermeticity harness passes 8/8; action outputs are deterministic.
- **Parallel wavefront builds.** The build executor saturates all cores by
  default (`RUSH_BUILD_JOBS` tunes the cap); use mold/lld for large links
  (`RUSH_LINKER`).

## What's left — do these

- **Close the no-op gap at TF scale.** Warm no-op sits at 44–130 s vs
  Bazel's 0.22 s on TF-sized graphs: redundant fetch-warmup of already
  materialized repos plus full BUILD/.bzl re-parse. Land the rushd daemon +
  inotify dirty-set design (the invariant: a second identical command does
  zero load/analyze work). The daemon already delivers 0.02 s no-ops on
  335-target graphs; prove it at 18–21k targets.
- **Enforce the rejection rules.** The 15-case micro-conformance suite shows
  rush enforcing 9/15; it is too permissive on 6 rejection rules (visibility
  and malformed-input classes). Make rush reject what Bazel rejects.
- **Track header dependencies for incremental correctness.** Compile-action
  freshness must incorporate included headers (and `--define` changes —
  a stale-object case exists) rather than declared inputs alone.
- **Wire the Python rule stack.** `py_*` rules exist but are unwired
  (rule_type=unknown) and pybind is absent. `cc_shared_library` works;
  connect py_library/py_binary/py_test to the live path and add pybind
  extension builds so the Python wheel slice becomes buildable.
- **Genrule make-variable expansion.** Finish `$(location)`, `$(RULEDIR)`,
  and py_binary-as-tool execution for generator genrules
  (quantized_function_library is the canonical blocker).
- **Full Bzlmod at TF scale.** The Modular lane proves module-graph
  resolution on mid-size trees; extend it to TF's protobuf→gRPC dependency
  breadth.
- **Remote cache / remote execution.** The Remote Execution API v2 endpoints
  exist as flags; validate them against a real CAS/executor deployment.

## Reproduce

```sh
# in an unmodified TF 2.15 checkout
rush build //tensorflow/tools/pip_package:build_pip_package  # or any target
rush build --define tflite_with_xnnpack=false //tensorflow:libtensorflow_cc.so.2.15.0
```

Run the CPU test corpus with the self-contained harness (auto-staged by the
test runner); expected result: 463/463.
