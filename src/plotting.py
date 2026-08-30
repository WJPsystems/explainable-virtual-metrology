"""
Shared plotting utilities used across notebooks 01-05 for the Visual
Evidence figures required by the Final Report.

Established once here, not per-notebook, so that: (1) the same model always
gets the same color across every chart a reader sees, letting them build a
visual vocabulary once instead of re-reading a legend every figure; and (2)
every figure is saved the same way (same DPI, same folder, same naming
convention), so 00_run_all's "download all figures" step can reliably find
everything without notebook-specific special-casing.

Optimized for the Word/PDF report specifically (portrait-friendly sizes,
readable at print resolution) -- NOT tuned for slide/16:9 presentation use.
A presentation-specific restyling pass is planned separately later; do not
assume these defaults are appropriate for a PPT export without revisiting
figsize/font sizes for that context.
"""

from pathlib import Path

import matplotlib.pyplot as plt

FIGURES_DIR = Path(__file__).resolve().parents[1] / "data" / "artifacts" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# Fixed color mapping -- reused identically across every chart that compares
# these models. MLP is only ever plotted alongside TabNet in RQ4, but is
# defined here too so RQ4's charts pull from the same single source of
# truth as every other notebook, rather than a locally-redefined color.
MODEL_COLORS = {
    "RandomForest": "#1f77b4",       # blue
    "XGBoost": "#ff7f0e",            # orange
    "LogisticRegression": "#2ca02c", # green
    "TabNet": "#d62728",             # red
    "MLP": "#9467bd",                # purple
}

# Consistent display labels (spaces, not concatenated words) for axis/legend
# text, independent of the dict keys above (which match the keys already
# used throughout the codebase's results dictionaries).
MODEL_LABELS = {
    "RandomForest": "Random Forest",
    "XGBoost": "XGBoost",
    "LogisticRegression": "Logistic Regression",
    "TabNet": "TabNet",
    "MLP": "MLP (control)",
}

FONT_SIZE = 11
FIGSIZE_STANDARD = (7, 5)
FIGSIZE_WIDE = (9, 5)
DPI = 200


def style_axes(ax, title=None, xlabel=None, ylabel=None):
    """Apply consistent, minimal styling: no top/right spines, light grid."""
    if title:
        ax.set_title(title, fontsize=FONT_SIZE + 1, fontweight="bold")
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=FONT_SIZE)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=FONT_SIZE)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.25, linewidth=0.6)
    ax.tick_params(labelsize=FONT_SIZE - 1)
    return ax


def save_figure(fig, name):
    """
    Save a figure to the shared figures artifact folder as a PNG, and
    return the saved path. `name` should be a short, descriptive,
    snake_case identifier without an extension (e.g. 'rq1_roc_curves').
    """
    path = FIGURES_DIR / f"{name}.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved figure: {path}")
    return path
