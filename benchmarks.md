# Build-time benchmarks — Modular tree

Host: 96-core x86-64 (dual-socket Sapphire-Rapids class, 2 TB DDR +
512 GiB CXL), Modular pin `cc7155d`, both engines building the identical
label set with all external repositories pre-fetched. Values are medians
of 3 runs (cold: single run). "Bazel (warm disk cache)" is Bazel with the
tree's configured `--disk_cache` already populated — the best case Bazel
ever sees; "no disk cache" is a true cold compile, matching what rush
does (rush's own disk cache is cleared for cold runs).

![Whole repo](graphs/bench-full.svg)

![Stdlib slice](graphs/bench-stdlib.svg)

| Scenario (whole repo, 4,175 targets) | rush | Bazel (no disk cache) | Bazel (warm disk cache) |
|---|---:|---:|---:|
| Cold build | **368 s** | 611 s | 63 s |
| Warm no-op | **0.05 s** | 12.6 s | 13.2 s |
| Incremental (1 file touched) | 334 s | 29 s | 13 s |

| Scenario (stdlib slice, 945 targets) | rush | Bazel (no disk cache) | Bazel (warm disk cache) |
|---|---:|---:|---:|
| Cold build | **39 s** | 245 s | 42 s |
| Warm no-op | **0.35 s** | 3.4 s | 3.5 s |
| Incremental (1 file touched) | 23 s | 24 s | 24 s |

Reading the table honestly:

- **Cold compiles: rush is 1.7× faster whole-repo and 6× faster on the
  stdlib slice** than a true-cold Bazel. Rush's parallel wavefront drives
  all 96 cores with no JVM, no aspect overhead, and no sandbox setup tax.
- **Warm no-op: rush is ~250× faster** (0.05 s vs ~13 s). The rushd
  daemon's inotify dirty-set answers "nothing changed" without scanning.
- **Incremental is rush's open weakness at repo scale.** Bazel's
  content-based early cutoff notices that a comment-only edit produces a
  byte-identical `std.mojoc` and prunes the entire downstream graph
  (29 s); rush's dependency stamps are provenance-keyed, so the same edit
  rebuilds the Mojo world (334 s). At stdlib scale the effect washes out
  (23 s vs 24 s). Fix queued: content-keyed producer stamps to get the
  same early-cutoff behavior.
- A warm Bazel disk cache beats everything for repeat-cold builds (63 s).
  Rush's current cache is an **action metadata cache**: it can skip
  actions whose outputs still exist, but it cannot reconstruct deleted
  outputs from cached bytes, so rush has no equivalent repeat-cold path
  yet. A content-addressed store with rematerialization is in
  development. The no-cache columns are the honest engine-vs-engine
  compile comparison.

## GPU runtime correctness (H100)

Runtime parity was validated on a rented H100 (PCIe): the GPU kernel
test corpus was cross-compiled for `sm_90a` on the build host by BOTH
engines, and the binaries executed on the GPU with the repo's own
FileCheck / expect-crash semantics.

- Corpus: 287 GPU kernel tests (of 763; the remainder are multi-hour,
  100 GB+ RSS compile outliers — two of them OOM-killed under Bazel
  itself on a 2.5 TB machine).
- **Zero runtime divergences: every comparable Bazel-green test (222 of
  222) also passes when built by rush.** 12 shared failures agree
  between engines (H100-PCIe environment specifics). Rush's binaries
  additionally pass 36 tests where Bazel's filecheck wrapper scripts
  cannot run outside `bazel test` runfiles.
- Mojo GPU programs built by rush are byte-parity-class artifacts: the
  earlier H100 receipt showed byte-identical run output over ten
  alternating Bazel/rush runs.
