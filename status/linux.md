# Linux build status

Rush is developing a native replay path for unmodified Linux Kbuild trees.
Linux's Makefiles, Kconfig logic, generated dependency metadata, and source
files remain unchanged. The current comparison uses
[Lorenzo Stoakes's v1 build-speedup series](https://lore.kernel.org/all/20260908-build-speedup-v1-0-5dc1ac01672d@kernel.org/)
as the baseline for both GNU Make and Rush, not vanilla Linux.

## Current verdict

**Promising scouting win, not yet a certified win.**

Three alternating Host A pairs produced a 40.24 s Rush median and a 50.92 s
Make median. That is a 1.265x speedup, or 20.97% lower wall time, with exact
output parity in every pair. Three pairs are not enough for the final claim:
the acceptance gate requires at least ten balanced alternating pairs and a
95% confidence-interval lower bound above 1.0.

This result compares a populated-cache Rush native replay into a clean output
root with a clean GNU Make build. It does **not** show that uncached Rush
compilation is faster. An empty-cache Rush diagnostic took 12:02.92 and is
currently far slower than Make.

## Scouting result

| Arm | Wall times | Median |
| --- | --- | --- |
| Rush populated-cache native replay | 35.98 s, 41.19 s, 40.24 s | **40.24 s** |
| Lorenzo-v1 GNU Make | 50.92 s, 53.04 s, 50.15 s | **50.92 s** |

Scope and constraints:

- Single 96-core x86-64 system, reported publicly as Host A.
- Scouting parallelism was fixed at 32 jobs for both arms.
- Linux commit `35568770debb5fab088d5d6c2b6a535ad6e8cb4d` and tree
  `116df9506075825b4f676ff33443a8f3acbc6e3e`.
- Identical configuration seed, fixed build timestamp, build user, build host,
  locale, and timezone.
- Rush and Make each produced 12,397 persistent entries and 11,561 regular
  files per run.
- File bytes, path types, modes, and symbolic-link targets had zero
  differences.

These timings are scouting evidence only. They are not yet the project's
official Linux performance certificate.

## How native replay works

The current pipeline separates one-time graph preparation from repeated
builds:

1. **Capture.** Run one clean GNU Make build under the Rush observer. Record
   process creation, command lines, environment, file accesses, generated
   files, directory effects, runtime inputs, and the Kbuild dependency flow.
2. **Derive.** Convert the observation stream into a deterministic external
   action graph. Classify cache eligibility and retain mandatory actions for
   environment-sensitive behavior such as procfs and runtime-directory
   checkpoints.
3. **Assemble.** Validate the graph and output tree, bind them to source,
   configuration, environment, and Rush binary identities, then emit a
   snapshot, key, and CAS-backed artifacts.
4. **Replay.** Validate those identities, restore cacheable outputs through
   Rush's normal action manager and CAS, execute mandatory actions under the
   modeled environment, and commit the output tree only after all gates pass.

The capture, derivation, and assembly costs are setup costs; they are not
hidden inside the 35.98-41.19 s replay measurements. A previous complete
fixture required 1:12:20 to capture, 6:48.55 to derive, and 1:08:15 to
assemble. That cost is acceptable for experimentation and repeated replay,
but it is much too high for the eventual user-facing frontend. Reducing or
eliminating this exporter path remains core work.

The target architecture is a supported Kbuild dialect and persistent native
graph, while GNU Make remains the correctness oracle and bootstrap path.

## Latest capture and descriptor work

GNU Make leaves jobserver metadata in ordinary recipe environments even when
the advertised descriptors are closed before `exec`. Replay intentionally
closes descriptors 3 and above, so accepting arbitrary captured descriptor
numbers can change nested Kconfig shell behavior.

Rush now applies two fail-closed gates:

- `05e55b712f7c` rejects jobserver-bearing mandatory actions that cannot be
  represented by standard-only replay.
- `8bbe6d14eb36` admits exactly one canonical closed
  `--jobserver-auth=3,4` token in `MAKEFLAGS` or `MFLAGS`, while rejecting
  shifted pairs, legacy `--jobserver-fds`, malformed values, duplicates, and
  path-bearing values.

Each change passed its focused Rush test. The second policy has not yet passed
the complete Linux replay certificate, so it is a guarded implementation
result rather than a finished compatibility claim.

A fresh Host A capture then completed successfully:

- 1:11:41 capture wall time;
- 30,222,094 observation records;
- 35,740 processes;
- 8,535,323,182 stream bytes;
- 6:28.78 graph derivation;
- approximately 1.6 GiB derived graph.

The fresh output's `.config` and `include/config/auto.conf` hashes matched the
previous capture. This means the descriptor diagnosis is not fully closed:
the final run must still prove the effective Kconfig action environment and
exact replay behavior.

The shared Host A service reclaimed the volatile workspace after derivation
and before preflight and assembly completed. This was an infrastructure
lifetime failure, not a Linux build or Rush capture failure. The large
one-time stages therefore remain **NOT RUN to completion** for this candidate,
and no new replay timing or parity claim is made from it.

## What is proven

- Rush can capture and derive the full unchanged Lorenzo-v1 Linux build.
- A prior assembled fixture can replay the build with 12,397-entry and
  11,561-file exact parity.
- Three populated-cache scouting pairs favor Rush by 1.265x at the median.
- Invalid descriptor metadata now fails before replay mutates the output root.
- Current ordinary and managed observer microfixtures preserve GNU Make's
  canonical `3,4` jobserver metadata and standard recipe descriptors.
- The latest full capture and graph derivation completed before volatile
  workspace reclamation.

## What is not proven

- The scouting speedup is not statistically certified.
- The canonical descriptor policy has not completed assembly, replay, and
  Linux output parity on a fresh fixture.
- Empty-cache Rush does not beat Make.
- Capture and assembly overhead is not production-ready.
- Results are single-host evidence, not cross-host certification.
- No claim is made against vanilla Linux; Lorenzo's series is the required
  baseline and goalpost.

## Acceptance gate -- do these

1. Freeze one Rush commit, Lorenzo-v1 Linux commit, configuration seed, and
   deterministic environment on Host A.
2. Capture, derive, preflight, and assemble on durable storage. Require every
   stage to complete and preserve its checksums before replay.
3. Verify the captured Kconfig action's effective `MAKEFLAGS`, `MFLAGS`, and
   descriptor topology. Require canonical closed `3,4` semantics or fail the
   snapshot before output mutation.
4. Replay into a clean output root. Require 12,397 persistent entries, 11,561
   regular files, and zero byte, type, mode, or symlink-target differences
   from the matching Lorenzo-v1 Make output.
5. Run at least ten balanced alternating Rush/Make pairs at
   `-j $(nproc)`. Report every sample, medians, dispersion, and paired
   speedup ratios.
6. Compute a 95% confidence interval over paired log-speedup ratios. Require
   its lower bound to exceed 1.0; otherwise report no performance win.
7. Run empty-cache, changed-input, changed-environment, corrupted-cache, and
   interrupted-commit cases. Require either correct rebuilding or a
   fail-closed refusal with no partially committed output.
8. Keep capture/derive/assembly costs separate from replay latency and keep
   clean, incremental, warm no-op, populated-cache restore, and empty-cache
   results in separate tables.

Until all eight steps pass on one frozen candidate, the honest status remains:
Rush has beaten Lorenzo-v1 Make in a small exact-parity scouting race, but has
not yet earned the final Linux build-speed record claim.
