import io
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, Any, List

CONTRAST_PALETTE = [
    "#007BFF",  # Royal Blue (Primary Theme)
    "#DC2626",  # Crimson Red
    "#059669",  # Emerald Green
    "#D97706",  # Amber / Warm Gold
    "#7C3AED",  # Royal Purple
    "#0891B2",  # Cyan / Teal
    "#EA580C",  # Burnt Orange
    "#475569",  # Slate Dark
    "#DB2777",  # Magenta / Pink
    "#2563EB",  # Deep Blue
]

def render_reaction_coordinate(reaction, thermo_summary: Dict[str, Any], u_pot: float = 0.0, ph: float = 0.0, step_mode: str = "4-step", y_lim: tuple[float, float] | None = None) -> bytes:
    """Renders single-catalyst reaction coordinate profile for any registered reaction (HER, OER, ORR)."""
    if reaction.name == "OER":
        labels, levels, _ = reaction.get_reaction_coordinate_states(thermo_summary, u_pot, ph, step_mode=step_mode)
        mode_tag = f" ({step_mode.upper()})"
    else:
        labels, levels, _ = reaction.get_reaction_coordinate_states(thermo_summary, u_pot, ph)
        mode_tag = ""
    num_states = len(labels)
    
    # Identical figure dimensions for 6-step and 4-step so vertical eV/pixel scale matches 1:1
    fig, ax = plt.subplots(figsize=(8.5, 5.0), dpi=300)
    x_mid = np.arange(num_states) + 0.5
    width = 0.36
    bar_thickness = 2.4

    for i in range(num_states):
        c = "#007BFF" if i > 0 and levels[i] > levels[i - 1] else "#1e293b"
        ax.hlines(levels[i], x_mid[i] - width / 2, x_mid[i] + width / 2, colors=c, linewidth=bar_thickness)
        ax.text(
            x_mid[i], levels[i] + 0.03, f"{levels[i]:+.2f} eV",
            ha="center", va="bottom", fontsize=8.5 if num_states >= 7 else 9,
            fontweight="bold", color=c
        )
        if i < num_states - 1:
            ax.plot([x_mid[i] + width / 2, x_mid[i + 1] - width / 2], [levels[i], levels[i + 1]], "k--", alpha=0.5, linewidth=1.1)

    ax.set_xticks(x_mid)
    ax.set_xticklabels(labels, fontsize=8.5 if num_states >= 7 else 10, fontweight="bold")
    ax.set_ylabel(r"Free Energy $\Delta G$ (eV)", fontsize=11, fontweight="bold")
    ax.set_title(
        f"{reaction.name}{mode_tag} Free Energy Landscape — {thermo_summary.get('surface', 'Surface')}\n"
        f"(U = {u_pot:.2f} V vs. RHE, pH = {ph:.1f})",
        fontsize=12, fontweight="bold", pad=14
    )
    ax.axhline(0, color="gray", linestyle=":", alpha=0.4)
    ax.set_xlim(0, num_states)
    if y_lim is not None:
        ax.set_ylim(y_lim)
    ax.grid(axis="y", linestyle="--", alpha=0.3)

    # Lock exact inner plot box coordinates instead of variable tight_layout()
    fig.subplots_adjust(left=0.11, right=0.97, top=0.85, bottom=0.14)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=300)
    plt.close(fig)
    return buf.getvalue()

def render_comparative_reaction_coordinate(reaction, surfaces_data: List[Dict[str, Any]], u_pot: float = 0.0, ph: float = 0.0) -> bytes:
    """Overlays multiple catalyst profiles with high-contrast colors on a single reaction coordinate."""
    fig, ax = plt.subplots(figsize=(8.5, 5.2), dpi=300)
    
    first_labels, _, _ = reaction.get_reaction_coordinate_states(surfaces_data[0], u_pot, ph)
    num_states = len(first_labels)
    x_mid = np.arange(num_states) + 0.5
    width = 0.36

    colors = [CONTRAST_PALETTE[i % len(CONTRAST_PALETTE)] for i in range(len(surfaces_data))]

    for idx, (s, c) in enumerate(zip(surfaces_data, colors)):
        _, levels, _ = reaction.get_reaction_coordinate_states(s, u_pot, ph)
        for j in range(num_states):
            lbl = f"{s['surface']} (U_L={s['u_limiting']:+.2f} V)" if j == 0 else None
            ax.hlines(levels[j], x_mid[j] - width/2, x_mid[j] + width/2, colors=c, linewidth=2.2, label=lbl)
            if j < num_states - 1:
                ax.plot([x_mid[j] + width/2, x_mid[j+1] - width/2], [levels[j], levels[j+1]], '--', color=c, alpha=0.6, linewidth=1.0)

    ax.legend(loc="upper right" if reaction.name == "HER" else "upper left", frameon=True, fontsize=8.5)
    ax.set_xticks(x_mid)
    ax.set_xticklabels(first_labels, fontsize=10, fontweight='bold')
    ax.set_ylabel(r"Free Energy $\Delta G$ (eV)", fontsize=11, fontweight='bold')
    ax.set_title(f"{reaction.name} Multi-Catalyst Free Energy Profiles\n(U = {u_pot:.2f} V vs. RHE, pH = {ph:.1f})", fontsize=12, fontweight='bold', pad=14)
    ax.axhline(0, color='gray', linestyle=':', alpha=0.4)
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=300)
    plt.close(fig)
    return buf.getvalue()

def render_comparative_volcano(reaction, surfaces_data: List[Dict[str, Any]]) -> bytes:
    """Renders a clean multi-catalyst Limiting Potential (U_L) scatter plot with:
      1. High-contrast colors per catalyst
      2. Diagonal/volcanic lines removed for pure scatter focus
      3. Both vertical and horizontal guide lines per point
      4. Dynamic non-limiting x/y range with default bounds
      5. Non-overlapping bottom-right legend
    """
    params = reaction.get_volcano_parameters(surfaces_data[0])
    fig, ax = plt.subplots(figsize=(8.2, 5.2), dpi=300)

    default_xlim = params.get("xlim", (0.8, 2.4))
    default_ylim = params.get("ylim", (1.2, 2.6))

    colors = [CONTRAST_PALETTE[i % len(CONTRAST_PALETTE)] for i in range(len(surfaces_data))]
    all_x = []
    all_y = []

    for s in surfaces_data:
        p_s = reaction.get_volcano_parameters(s)
        pt_x, pt_y = p_s["data_point"]
        all_x.append(pt_x)
        all_y.append(pt_y)

    if all_x:
        min_data_x, max_data_x = min(all_x), max(all_x)
        x_min = min(default_xlim[0], min_data_x - 0.20)
        x_max = max(default_xlim[1], max_data_x + 0.20)
    else:
        x_min, x_max = default_xlim

    if all_y:
        min_data_y, max_data_y = min(all_y), max(all_y)
        y_min = min(default_ylim[0], min_data_y - 0.15)
        y_max = max(default_ylim[1], max_data_y + 0.20)
    else:
        y_min, y_max = default_ylim

    x_range = x_max - x_min
    y_range = y_max - y_min
    lr_points = [
        (x, y) for x, y in zip(all_x, all_y)
        if (x > x_min + 0.45 * x_range) and (y < y_min + 0.40 * y_range)
    ]
    if lr_points:
        lowest_lr_y = min(y for x, y in lr_points)
        required_y_min = lowest_lr_y - 0.35 * y_range
        y_min = min(y_min, required_y_min)

    for idx, (s, c) in enumerate(zip(surfaces_data, colors)):
        p_s = reaction.get_volcano_parameters(s)
        pt_x, pt_y = p_s["data_point"]
        ax.scatter([pt_x], [pt_y], color=c, s=120, zorder=6, edgecolors="#0f172a", linewidths=1.2,
                   label=f"{s['surface']} ($U_L={pt_y:+.2f}$ V)")
        ax.text(pt_x, pt_y + 0.035, s["surface"], ha="center", va="bottom", fontsize=8.5, fontweight="bold", color=c)
        # Vertical and horizontal dotted guide lines to the axes
        ax.plot([pt_x, pt_x], [y_min - 10.0, pt_y], ":", color=c, alpha=0.45, linewidth=1.2)
        ax.plot([x_min - 10.0, pt_x], [pt_y, pt_y], ":", color=c, alpha=0.45, linewidth=1.2)

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_xlabel(params["x_label"], fontsize=11, fontweight="bold")
    ax.set_ylabel(params["y_label"], fontsize=11, fontweight="bold")
    ax.set_title(f"Comparative {reaction.name} Limiting Potential ($U_L$) Comparison", fontsize=12, fontweight="bold", pad=14)

    for y_ref, c_ref, s_ref in params.get("ref_lines", []):
        ax.axhline(y_ref, color=c_ref, linestyle=s_ref, alpha=0.4)
    ax.grid(True, linestyle="--", alpha=0.3)

    ax.legend(
        loc="lower right",
        frameon=True,
        framealpha=0.92,
        facecolor="#ffffff",
        edgecolor="#cbd5e1",
        fontsize=8.5
    )
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=300)
    plt.close(fig)
    return buf.getvalue()
