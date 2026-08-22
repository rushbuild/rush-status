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
| Cold build | **362 s** | 611 s | — |
| Repeat-cold (outputs wiped, caches warm) | **32 s** (14.6 s warm page cache) | — | 63 s |
| Warm no-op | **0.05 s** | 12.6 s | 13.2 s |
| Incremental (1 file touched) | **14.6 s** | 29 s | 13 s |

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
- **Incremental: rush now has content-based early cutoff.** Output
  stamps carry each artifact's value (a versioned BLAKE3 fingerprint over
  content, kind and observable filesystem properties — with thin-archive
  members folded in) instead of the producer's identity. A comment-only
  edit re-runs one compiler, sees `std.mojoc` come back byte-identical,
  and prunes the entire downstream graph: 334 s before, **14.6 s** now —
  past Bazel's 29 s no-cache result and matching its 13 s cached result.
- **Repeat-cold: rush now has a real CAS.** Action results record full
  output records (fingerprints, content digests, modes, symlinks, tree
  structure) and output bytes live in a content-addressed store; deleting
  the entire output tree and rebuilding restores from cache in **32 s**
  (14.6 s with a warm page cache) versus Bazel's 63 s. Every restored
  blob is digest-verified during the copy — corrupt or truncated cache
  content becomes a miss, never a wrong build. Storing into the CAS costs
  nothing measurable on cold builds (362 s vs the 368 s pre-CAS baseline).

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
