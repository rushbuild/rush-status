#!/usr/bin/env python3
"""Render the rush status charts.

Build-time charts are LINEAR and use small multiples: one panel per
scenario, each with its own axis. A single linear axis cannot hold a
0.05 s no-op and a 611 s cold build, and a single log axis flattens a
250x difference into a couple of centimetres - which hides the result
instead of showing it. One panel per scenario keeps every bar readable
at true proportion.

A log chart is kept as a secondary view for readers who want the whole
range at once. The TensorFlow chart reports scoped acceptance gates.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

RUSH = "#1F5FA9"       # deep blue
BAZEL = "#C8781A"      # amber - blue/amber stays separable under CVD
BAZEL_WARM = "#E0A75E"  # lighter amber for Bazel's best case
INK = "#1A1A1A"
MUTED = "#6B6B6B"
GRID = "#DDDDDD"

# (scenario, rush, bazel_no_cache, bazel_warm_cache)  None = not measured
FULL = [
    ("Cold build\nfrom nothing",              362.0, 611.0, None),
    ("Rebuild after\ndeleting all outputs",    32.0, None,  63.0),
    ("Change one file\n(novel edit)",          26.0, 30.1,  None),
    ("Repeat an edit\nseen before",             0.15, None, 13.0),
    ("Build again,\nnothing changed",           0.05, 12.6, 13.2),
]
STDLIB = [
    ("Cold build\nfrom nothing",               39.0, 245.0, 42.0),
    ("Change one file",                        23.0, 24.0,  24.0),
    ("Build again,\nnothing changed",           0.35, 3.4,   3.5),
]
TENSORFLOW_CERTIFICATES = [
    ("TF 2.15 CPU\ntf_cc_test", 463, 463),
    ("Repaired corpus\nre-sweep", 98, 98),
    ("Differential\ncorrectness checks", 8, 8),
    ("Compatibility\nmicro-conformance", 16, 16),
    ("Python extension\nbuild + import", 2, 2),
]


def fmt_secs(v):
    if v < 1:
        return f"{v:.2f} s"
    if v < 10:
        return f"{v:.1f} s"
    return f"{v:.0f} s"


def small_multiples(rows, title, subtitle, path):
    fig, axes = plt.subplots(1, len(rows), figsize=(3.4 * len(rows), 4.3))
    if len(rows) == 1:
        axes = [axes]

    for ax, (name, rush, bz, bz_warm) in zip(axes, rows):
        bars, colors, labels = [], [], []
        bars.append(rush); colors.append(RUSH); labels.append("rush")
        if bz is not None:
            bars.append(bz); colors.append(BAZEL); labels.append("Bazel")
        if bz_warm is not None:
            bars.append(bz_warm); colors.append(BAZEL_WARM)
            labels.append("Bazel\n(warm cache)")

        y = list(range(len(bars)))[::-1]
        # A bar can be so much shorter than its neighbours that it renders as
        # nothing (0.05 s beside 13 s). Draw the true value, then give any
        # sub-pixel bar a visible stub so it reads as "measured and tiny"
        # rather than "missing". The number beside it carries the real value.
        floor = max(bars) * 0.012
        drawn = [max(b, floor) for b in bars]
        ax.barh(y, drawn, color=colors, height=0.62)
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=10, color=INK)
        ax.set_xlim(0, max(bars) * 1.42)
        for yi, v in zip(y, bars):
            ax.text(max(v, floor) + max(bars) * 0.04, yi, fmt_secs(v), va="center",
                    fontsize=11, color=INK, fontweight="bold")

        # How much faster is rush than Bazel's BEST showing here?
        best = min(b for b in (bz, bz_warm) if b is not None)
        ratio = best / rush
        verdict = (f"rush {ratio:.0f}x faster" if ratio >= 2
                   else f"rush {ratio:.1f}x faster" if ratio > 1.05
                   else f"Bazel {1/ratio:.1f}x faster" if ratio < 0.95
                   else "about even")
        vcolor = RUSH if ratio > 1.05 else (BAZEL if ratio < 0.95 else MUTED)
        ax.set_title(name, fontsize=11.5, color=INK, pad=16, fontweight="bold")
        ax.text(0.5, 1.005, verdict, transform=ax.transAxes, ha="center",
                fontsize=10.5, color=vcolor, fontweight="bold")

        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
        ax.tick_params(axis="x", labelsize=9, colors=MUTED)
        ax.set_xlabel("seconds", fontsize=9, color=MUTED)
        ax.grid(axis="x", color=GRID, linewidth=0.7)
        ax.set_axisbelow(True)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color(GRID)

    fig.suptitle(title, fontsize=15, fontweight="bold", color=INK, y=1.02)
    fig.text(0.5, 0.945, subtitle, ha="center", fontsize=10.5, color=MUTED)
    fig.text(0.5, 0.015, "Shorter bars are better. Each panel has its own "
             "scale so every bar stays readable.",
             ha="center", fontsize=9.5, color=MUTED)
    fig.tight_layout(rect=[0, 0.04, 1, 0.91])
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print("wrote", path)


def log_overview(rows, title, path):
    fig, ax = plt.subplots(figsize=(8.4, 3.6))
    names = [r[0].replace("\n", " ") for r in rows]
    y = list(range(len(rows)))[::-1]
    h = 0.36
    ax.barh([v + h / 2 for v in y], [r[1] for r in rows], height=h,
            color=RUSH, label="rush")
    # Plot Bazel's BEST measured run in each scenario - the comparison that
    # is hardest on rush, and the same basis the per-scenario panels use.
    best = [min(v for v in (r[2], r[3]) if v is not None) for r in rows]
    ax.barh([v - h / 2 for v in y], best, height=h,
            color=BAZEL, label="Bazel (its best measured run)")
    ax.set_xscale("log")
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=10, color=INK)
    ax.set_xlabel("seconds (log scale)", fontsize=9.5, color=MUTED)
    ax.tick_params(labelsize=9, colors=MUTED)
    ax.grid(axis="x", color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.legend(fontsize=9.5, frameon=False, loc="lower right")
    ax.set_title(title, fontsize=12.5, fontweight="bold", color=INK)
    fig.text(0.5, -0.04, "Secondary view: a log scale fits every scenario on "
             "one axis, but it visually shrinks large wins.",
             ha="center", fontsize=9, color=MUTED)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print("wrote", path)


def certification_dashboard(rows, title, subtitle, path):
    """Render pass/total certificates without implying whole-tree coverage."""
    fig, ax = plt.subplots(figsize=(8.4, 4.5))
    labels = [r[0] for r in rows]
    passed = [r[1] for r in rows]
    totals = [r[2] for r in rows]
    rates = [p / t * 100 for p, t in zip(passed, totals)]
    y = list(range(len(rows)))[::-1]

    ax.barh(y, [100] * len(rows), color="#E9EEF4", height=0.58)
    ax.barh(y, rates, color=RUSH, height=0.58)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10.5, color=INK)
    ax.set_xlim(0, 112)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}%"))
    ax.tick_params(axis="x", labelsize=9, colors=MUTED)
    ax.grid(axis="x", color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    for yi, p, t, rate in zip(y, passed, totals, rates):
        ax.text(101.5, yi, f"{p}/{t}", va="center", fontsize=11,
                color=INK, fontweight="bold")
        ax.text(97.5, yi, f"{rate:.0f}%", va="center", ha="right",
                fontsize=10, color="white", fontweight="bold")

    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    fig.suptitle(title, fontsize=15, fontweight="bold", color=INK, y=1.02)
    fig.text(0.5, 0.925, subtitle, ha="center", fontsize=10.5, color=MUTED)
    fig.text(0.5, 0.005,
             "Run each named gate; read N/N as N passing cases out of N "
             "evaluated cases in that scope.",
             ha="center", fontsize=9.5, color=MUTED)
    fig.tight_layout(rect=[0, 0.05, 1, 0.88])
    with matplotlib.rc_context({"svg.hashsalt": "rush-status-certification-v1"}):
        fig.savefig(path, bbox_inches="tight", metadata={"Date": None})
    plt.close(fig)
    if path.endswith(".svg"):
        # Matplotlib emits spaces before newlines in SVG path data. Normalize
        # them so regeneration is byte-stable and passes git diff --check.
        with open(path, encoding="utf-8") as source:
            normalized = "\n".join(
                line.rstrip() for line in source.read().splitlines()
            ) + "\n"
        with open(path, "w", encoding="utf-8", newline="\n") as target:
            target.write(normalized)
    print("wrote", path)


def tensorflow_noop_chart(path):
    """Render the one currently published apples-to-apples TF timing."""
    labels = ["rush daemon", "Bazel --watchfs", "Bazel default"]
    values = [9.3, 54.5, 64.2]
    colors = [RUSH, BAZEL_WARM, BAZEL]
    y = list(range(len(labels)))[::-1]

    fig, ax = plt.subplots(figsize=(8.2, 3.6))
    ax.barh(y, values, color=colors, height=0.62)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=11, color=INK)
    ax.set_xlim(0, 78)
    ax.set_xlabel("build command latency (milliseconds, lower is better)",
                  fontsize=9.5, color=MUTED)
    ax.tick_params(axis="x", labelsize=9, colors=MUTED)
    ax.grid(axis="x", color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)

    for yi, value in zip(y, values):
        ax.text(value + 1.5, yi, f"{value:.1f} ms", va="center",
                fontsize=11, color=INK, fontweight="bold")

    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    fig.suptitle("TensorFlow scoped warm no-op — 18,522 dependencies",
                 fontsize=15, fontweight="bold", color=INK, y=1.02)
    fig.text(0.5, 0.91,
             "Median of 30 repeated builds of //tensorflow/core:framework.",
             ha="center", fontsize=10.5, color=MUTED)
    fig.text(0.5, 0.005,
             "No input changed; this is not a cold-build, incremental-compile, "
             "full-tree, or test-runtime result.",
             ha="center", fontsize=9.5, color=MUTED)
    fig.tight_layout(rect=[0, 0.08, 1, 0.86])
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print("wrote", path)


if __name__ == "__main__":
    import os
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "graphs")
    small_multiples(
        FULL, "Modular whole repo - 4,175 targets, 96 cores",
        "Time to finish the same build with the same inputs.",
        os.path.join(d, "bench-full.svg"))
    small_multiples(
        STDLIB, "Modular stdlib slice - 945 targets, 96 cores",
        "Time to finish the same build with the same inputs.",
        os.path.join(d, "bench-stdlib.svg"))
    log_overview(FULL, "Whole repo, every scenario on one log axis",
                 os.path.join(d, "bench-full-log.svg"))
    tensorflow_noop_chart(os.path.join(d, "bench-tensorflow-noop.svg"))
    certification_dashboard(
        TENSORFLOW_CERTIFICATES,
        "TensorFlow acceptance gates",
        "Run each named gate and count cases that satisfy its pass rule.",
        os.path.join(d, "tensorflow-certification.svg"))
