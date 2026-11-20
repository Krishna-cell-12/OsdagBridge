# =============================================================================
# OsdagBridge report - charts
#
# Draws the report charts with matplotlib and returns ready-to-insert LaTeX
# figure code. Appearance comes from styles.CHART / styles.COLORS.
#
#   ur_chart_tex(rows_tex)           Section 5.5  utilization ratios per member group
#   quantity_charts_tex(input_dict)  Chapter 7    steel tonnage + concrete vs reinforcement
#
# generate_report() calls set_output_dir() with its temporary image folder, so
# nothing is left next to the PDF. Every function returns "" (and logs) when
# matplotlib is missing or there is nothing to plot - the report still builds.
# =============================================================================
import logging
import os
import re

from . import styles

logger = logging.getLogger(__name__)
_OUT_DIR = None

_ROW_SPLIT = re.compile(r"\\\\(?:\*)?(?:\[[^\]]*\])?")
_CELL_SPLIT = re.compile(r"(?<!\\)&")
_FLOAT = re.compile(r"[-+]?\d+(?:\.\d+)?")


def set_output_dir(path):
    """Folder (inside the report's temp dir) where chart PNGs are written."""
    global _OUT_DIR
    _OUT_DIR = path
    os.makedirs(path, exist_ok=True)


def _get_plt():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt
    except Exception as exc:  # pragma: no cover
        logger.warning("charts skipped: matplotlib not available (%s)", exc)
        return None


def _num(v):
    m = _FLOAT.search(str(v).replace(",", "")) if v is not None else None
    return float(m.group(0)) if m else None


def _save(fig, name):
    if not _OUT_DIR:
        logger.warning("charts skipped: output directory not set")
        return None
    path = os.path.join(_OUT_DIR, name)
    fig.savefig(path, dpi=styles.CHART["dpi"], bbox_inches="tight")
    return path.replace("\\", "/")


def _figure_tex(path, caption, label):
    return "\n".join([
        r"\begin{figure}[H]",
        r"\centering",
        r"\includegraphics[width=0.92\textwidth]{%s}" % path,
        r"\caption{%s}" % caption,
        r"\label{%s}" % label,
        r"\end{figure}",
    ])


def _style_axes(ax):
    c = styles.CHART
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=c["grid_alpha"])
    ax.set_axisbelow(True)


# --------------------------------------------------------------------------
# Section 5.5 - utilization ratio chart
# --------------------------------------------------------------------------
_GROUPS = (
    ("Steel Plate Girders", ("girder",)),
    ("Concrete Deck Slab", ("deck", "(slab)", "slab")),
    ("Cross Bracing", ("cross bracing",)),
    ("End Diaphragms", ("end diaphragm",)),
)


def parse_ur_groups(rows_tex):
    """Maximum UR per member group from the rows of the overall summary table (LaTeX text)."""
    best = {}
    for row in _ROW_SPLIT.split(rows_tex or ""):
        row = re.sub(r"\\hline|\\cline\{[^}]*\}", " ", row)
        cells = _CELL_SPLIT.split(row)
        if len(cells) < 5:
            continue
        label = re.sub(r"\s+", " ", cells[0]).strip().lower()
        ur = _num(re.sub(r"\\textcolor\{[^}]*\}", "", cells[-1]))
        if ur is None:
            continue
        for name, keys in _GROUPS:
            if any(k in label for k in keys):
                best[name] = max(best.get(name, 0.0), ur)
                break
    return {name: best[name] for name, _ in _GROUPS if name in best}


def ur_chart_tex(rows_tex):
    groups = parse_ur_groups(rows_tex)
    if not groups:
        logger.warning("UR chart skipped: no utilization ratios found")
        return ""
    plt = _get_plt()
    if plt is None:
        return ""
    c = styles.CHART
    names, vals = list(groups), list(groups.values())
    colors = [c["bar_pass"] if v <= 1.0 else c["bar_fail"] for v in vals]
    plt.rcParams.update({"font.size": c["font_size"]})
    fig, ax = plt.subplots(figsize=c["figsize"])
    bars = ax.bar(names, vals, color=colors, width=0.55, zorder=3)
    ax.axhline(1.0, color=c["threshold_color"], linestyle="--", linewidth=1.4, zorder=4,
               label="UR = 1.0 (limit)")
    top = max(1.15, max(vals) * 1.18)
    ax.set_ylim(0, top)
    ax.set_ylabel("Utilization ratio (demand / capacity)")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + top * 0.015, f"{v:.2f}", ha="center", va="bottom",
                fontweight="bold")
    _style_axes(ax)
    ax.legend(loc="upper right", frameon=False)
    fig.tight_layout()
    path = _save(fig, "chart_ur_summary.png")
    plt.close(fig)
    if not path:
        return ""
    return "\n\\vspace{1em}\n" + _figure_tex(
        path,
        r"Governing utilization ratio of each member group (bars above the dashed line fail)",
        "fig:ur-summary")


# --------------------------------------------------------------------------
# Chapter 7 - quantity charts
# --------------------------------------------------------------------------
def _member_weight(input_dict, prefix):
    """Total weight (MT) of one member family. Uses weight-per-member x quantity (4 decimals)
    rather than the rounded 'total' column, so very light members are not rounded to zero."""
    single = _num(input_dict.get(prefix + "_wt_single"))
    qty = _num(input_dict.get(prefix + "_qty"))
    if single is not None and qty is not None:
        return single * qty
    return _num(input_dict.get(prefix + "_wt_total"))


def _sum_members(input_dict, prefixes):
    vals = [_member_weight(input_dict, p) for p in prefixes]
    vals = [v for v in vals if v is not None]
    return sum(vals) if vals else None


def _label(v):
    return f"{v:.2f}" if v >= 0.1 else f"{v:.3f}"


def quantity_charts_tex(input_dict):
    plt = _get_plt()
    if plt is None:
        return ""
    c = styles.CHART
    plt.rcParams.update({"font.size": c["font_size"]})
    out = []

    # --- steel tonnage -------------------------------------------------------
    girders = _num(input_dict.get("steel_girders_wt_total"))
    bracing = _sum_members(input_dict, ("bracing_top", "bracing_bot", "bracing_diag"))
    diaph = _sum_members(input_dict, ("end_diaphragm_top", "end_diaphragm_bot", "end_diaphragm_diag"))
    items = [("Plate girders", girders), ("Cross bracing", bracing), ("End diaphragms", diaph)]
    shown = [(n, v) for n, v in items if v is not None]
    if shown:
        fig, ax = plt.subplots(figsize=(c["figsize"][0], 0.9 + 0.6 * len(shown)))
        names, vals = [n for n, _ in shown][::-1], [v for _, v in shown][::-1]
        bars = ax.barh(names, vals, color=c["bar_neutral"], height=0.5, zorder=3)
        xmax = max(vals) * 1.18
        ax.set_xlim(0, xmax)
        for b, v in zip(bars, vals):
            ax.text(v + xmax * 0.01, b.get_y() + b.get_height() / 2, f"{_label(v)} MT", va="center")
        ax.set_xlabel("Structural steel weight (MT)")
        ax.grid(axis="x", alpha=c["grid_alpha"])
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        fig.tight_layout()
        path = _save(fig, "chart_steel_quantities.png")
        plt.close(fig)
        if path:
            out.append(_figure_tex(path, r"Structural steel quantities by member group (MT)", "fig:steel-quantities"))
        if diaph is None:
            out.append(r"\noindent\textit{Note: end diaphragm quantities are not part of this version's "
                       r"bill of materials and are therefore not shown.}")

    # --- concrete volume vs reinforcement weight ----------------------------------
    conc = _num(input_dict.get("concrete_deck_vol_total"))
    rebar = _num(input_dict.get("rebar_deck_wt_total"))
    if conc is not None and rebar is not None:
        fig, (a1, a2) = plt.subplots(1, 2, figsize=(c["figsize"][0], 2.8))
        b1 = a1.bar(["Deck concrete"], [conc], color=c["bar_neutral"], width=0.45, zorder=3)
        b2 = a2.bar(["Reinforcement"], [rebar], color=c["bar_pass"], width=0.45, zorder=3)
        a1.set_ylabel("Volume (m$^3$)")
        a2.set_ylabel("Weight (MT)")
        for ax, bar, val, unit in ((a1, b1[0], conc, "m$^3$"), (a2, b2[0], rebar, "MT")):
            ax.set_ylim(0, val * 1.2)
            ax.text(bar.get_x() + bar.get_width() / 2, val * 1.02, f"{_label(val)} {unit}", ha="center", va="bottom",
                    fontweight="bold")
            _style_axes(ax)
        fig.tight_layout()
        path = _save(fig, "chart_concrete_rebar.png")
        plt.close(fig)
        if path:
            out.append(_figure_tex(path, r"Deck concrete volume and reinforcement weight "
                                         r"(shown on separate axes because the units differ)",
                                   "fig:concrete-rebar"))
    if not out:
        return ""
    return ("\n\\vspace{1em}\n\\needspace{16\\baselineskip}\n\\noindent\\textbf{Quantity charts}\n\n"
            + "\n\n".join(out) + "\n")
