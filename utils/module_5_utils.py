import io
import os
import re
import matplotlib.pyplot as plt
import numpy as np
import openpyxl
from utils.common import extract_zip_to_dict, build_zip_from_dict, RY_TO_EV

HER_BLUE_PALETTE = [
    "#007BFF",  # Reference Electric Blue (Primary)
    "#0284c7",  # Sky Blue
    "#0d9488",  # Deep Teal
    "#2563eb",  # Royal Blue
    "#6366f1",  # Indigo
    "#0891b2",  # Cyan
    "#1e40af",  # Deep Navy
    "#4338ca",  # Midnight Blue
]

def extract_thermochem_robust(wb: openpyxl.Workbook) -> tuple[float, float]:
    """
    Extracts both *H adsorption energy Delta E_H* (from sheet 3-ads-energy)
    and Gibbs free energy Delta G_H* (from sheet 5-gibbs).
    """
    delta_e = None
    delta_g = None

    if "3-ads-energy" in wb.sheetnames:
        val_e = wb["3-ads-energy"].cell(row=2, column=2).value
        if isinstance(val_e, (int, float)):
            delta_e = float(val_e)

    if "5-gibbs" in wb.sheetnames:
        val_g = wb["5-gibbs"].cell(row=2, column=3).value
        if isinstance(val_g, (int, float)):
            delta_g = float(val_g)

    if delta_e is not None and delta_g is not None:
        return delta_e, delta_g

    try:
        ws1 = wb["1-adsorbate"]
        ws2 = wb["2-isolated-mol"]
        ws4 = wb["4-vibrasi"]

        e_surf_ry = ws1.cell(row=2, column=2).value
        e_ads_ry = ws1.cell(row=2, column=4).value
        e_surf_ev = float(e_surf_ry) * RY_TO_EV
        e_ads_ev = float(e_ads_ry) * RY_TO_EV

        e_h2 = float(ws2.cell(row=2, column=2).value or -31.7452)
        zpe_h2 = float(ws2.cell(row=2, column=3).value or 0.2720)
        ts_h2 = float(ws2.cell(row=2, column=4).value or 0.4040)

        calc_de = e_ads_ev - e_surf_ev - 0.5 * e_h2

        zpe_h = sum(
            float(ws4.cell(row=r, column=3).value or 0.0)
            for r in range(2, ws4.max_row + 1)
            if ws4.cell(row=r, column=3).value is not None
        )

        delta_zpe = zpe_h - 0.5 * zpe_h2
        calc_dg = calc_de + delta_zpe + 0.5 * ts_h2

        if delta_e is None:
            delta_e = calc_de
        if delta_g is None:
            delta_g = calc_dg
        return float(delta_e), float(delta_g)
    except Exception:
        return (delta_e if delta_e is not None else 0.0, delta_g if delta_g is not None else 0.0)

def parse_all_gibbs_from_zip(files: dict[str, bytes]) -> list[dict]:
    """Locates all valid .xlsx files in the uploaded zip and robustly evaluates Delta E_H*, Delta G_H*, and U_L."""
    results = []
    for path, data in files.items():
        if path.endswith('.xlsx') and not os.path.basename(path).startswith('~$'):
            try:
                wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
                if "5-gibbs" in wb.sheetnames or "3-ads-energy" in wb.sheetnames:
                    surf = wb["1-adsorbate"].cell(row=2, column=1).value if "1-adsorbate" in wb.sheetnames else None
                    if not surf and "5-gibbs" in wb.sheetnames:
                        surf = wb["5-gibbs"].cell(row=2, column=1).value
                    if not surf:
                        surf = os.path.splitext(os.path.basename(path))[0]

                    de, dg = extract_thermochem_robust(wb)
                    results.append({
                        "surface": str(surf),
                        "delta_e": round(de, 4),
                        "delta_g": round(dg, 4),
                        "u_l": round(-abs(dg), 4),
                        "overpotential": round(abs(dg), 4),
                        "path": path
                    })
            except Exception:
                continue
    return results

def render_comparative_gibbs_graph(surfaces_data: list[dict], u_pot: float = 0.0, ph: float = 0.0) -> bytes:
    """
    Renders Graph 1: Comparative Gibbs Free Energy Profile.
    x-axis: Reaction Coordinate (H+ + e-, H*, 1/2 H2)
    y-axis: Free Energy Delta G (eV)
    """
    fig, ax = plt.subplots(figsize=(8.0, 5.0), dpi=300)
    steps = [r"$\mathrm{H}^+ + \mathrm{e}^-$", r"$\mathrm{H}^*$", r"$\frac{1}{2}\mathrm{H}_2$"]
    x_mid = [0.5, 1.5, 2.5]
    width = 0.36
    bar_thickness = 2.4

    # Reference levels at 0.0 eV
    ax.hlines(0.0, x_mid[0] - width/2, x_mid[0] + width/2, colors="#1e293b", linewidth=bar_thickness)
    ax.hlines(0.0, x_mid[2] - width/2, x_mid[2] + width/2, colors="#1e293b", linewidth=bar_thickness)

    ax.text(x_mid[0], 0.025, "0.00 eV", ha='center', va='bottom', fontsize=10, fontweight='bold', color="#1e293b")
    ax.text(x_mid[2], 0.025, "0.00 eV", ha='center', va='bottom', fontsize=10, fontweight='bold', color="#1e293b")

    h_x_start = x_mid[1] - width/2
    h_x_end = x_mid[1] + width/2

    colors = [HER_BLUE_PALETTE[i % len(HER_BLUE_PALETTE)] for i in range(len(surfaces_data))]

    for idx, (s, c) in enumerate(zip(surfaces_data, colors)):
        dg = s["delta_g_shifted"]
        ax.hlines(dg, h_x_start, h_x_end, colors=c, linewidth=2.2, label=f"{s['surface']} (ΔG = {dg:+.2f} eV)")
        ax.text(h_x_end + 0.03, dg, f"{dg:+.2f} eV", ha='left', va='center', fontsize=8.5, fontweight='bold', color=c)
        ax.plot([x_mid[0] + width/2, h_x_start], [0.0, dg], '--', color=c, alpha=0.6, linewidth=1.0)
        ax.plot([h_x_end, x_mid[2] - width/2], [dg, 0.0], '--', color=c, alpha=0.6, linewidth=1.0)

    ax.legend(loc='upper right', frameon=True, fontsize=8.5, framealpha=0.9)
    ax.set_xticks(x_mid)
    ax.set_xticklabels(steps, fontsize=11, fontweight='bold')
    ax.set_ylabel(r"Free Energy $\Delta G$ (eV)", fontsize=11, fontweight='bold')
    ax.set_title(f"HER Multi-Catalyst Gibbs Free Energy Profiles\n(U = {u_pot:.2f} V vs. RHE, pH = {ph:.1f})", fontsize=12, fontweight='bold', pad=14)
    ax.axhline(0, color='gray', linestyle=':', alpha=0.5)
    ax.set_xlim(0, 3.1)
    ax.grid(axis='y', linestyle='--', alpha=0.3)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=300)
    plt.close(fig)
    return buf.getvalue()

def render_comparative_ul_graph(surfaces_data: list[dict]) -> bytes:
    """
    Renders Graph 2: The Limiting Potential (U_L) Graph for all compared catalysts.
    x-axis: *H Adsorption Energy Delta E_H* (eV)
    y-axis: Limiting Potential U_L (V vs. RHE)
    """
    fig, ax = plt.subplots(figsize=(8.2, 5.0), dpi=300)

    corr = 0.24
    if surfaces_data:
        corrs = [s["delta_g"] - s["delta_e"] for s in surfaces_data if s.get("delta_e") is not None]
        if corrs:
            corr = float(np.mean(corrs))

    de_peak = -corr

    de_min = min([s["delta_e"] for s in surfaces_data] + [-0.9]) - 0.15
    de_max = max([s["delta_e"] for s in surfaces_data] + [0.5]) + 0.15

    de_neg = np.linspace(de_min, de_peak, 100)
    de_pos = np.linspace(de_peak, de_max, 100)

    # Cohesive theme: Slate-Gray for Heyrovsky branch, Electric Blue for Volmer branch
    ax.plot(de_neg, de_neg + corr, color="#475569", linewidth=2.2,
            label=rf"Heyrovsky / Tafel Limiting ($\Delta E < {de_peak:.2f}$ eV)")
    ax.plot(de_pos, -(de_pos + corr), color="#007BFF", linewidth=2.2,
            label=rf"Volmer Limiting ($\Delta E > {de_peak:.2f}$ eV)")

    # Volcano apex (0 V)
    ax.scatter([de_peak], [0.0], color="#16a34a", s=130, marker="*", zorder=4,
               label=f"Ideal Volcano Apex ({de_peak:.2f} eV, 0.0 V)")

    colors = [HER_BLUE_PALETTE[i % len(HER_BLUE_PALETTE)] for i in range(len(surfaces_data))]

    for idx, (s, c) in enumerate(zip(surfaces_data, colors)):
        de = s["delta_e"]
        ul = s["u_l"]
        ax.scatter([de], [ul], color=c, s=120, zorder=6, edgecolors="#1e293b", linewidths=1.2,
                   label=f"{s['surface']} ($\Delta E={de:+.2f}$ eV, $U_L={ul:+.2f}$ V)")
        ax.text(de, ul + 0.035, s["surface"], ha="center", va="bottom", fontsize=8.5, fontweight="bold", color=c)
        ax.plot([de, de], [-1.5, ul], ":", color=c, alpha=0.4)

    ax.set_xlabel(r"*H Adsorption Energy $\Delta E_{\mathrm{H}^*}$ (eV)", fontsize=11, fontweight="bold")
    ax.set_ylabel(r"Limiting Potential $U_L$ (V vs. RHE)", fontsize=11, fontweight="bold")
    ax.set_title("Comparative Limiting Potential ($U_L$) Graph", fontsize=12, fontweight="bold", pad=14)
    ax.set_xlim(de_min, de_max)
    ax.set_ylim(-1.0, 0.1)
    ax.axhline(0, color="gray", linestyle="--", alpha=0.4)
    ax.axvline(de_peak, color="gray", linestyle=":", alpha=0.4)
    ax.grid(True, linestyle="--", alpha=0.3)
    ax.legend(loc="lower center", frameon=True, fontsize=8.5)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=300)
    plt.close(fig)
    return buf.getvalue()

def generate_multi_surface_comparison(
    zip_bytes: bytes, u_pot: float = 0.0, ph: float = 0.0
) -> tuple[bytes | None, bytes | None, bytes | None, list[dict], str | None]:
    files = extract_zip_to_dict(zip_bytes)
    surfaces_data = parse_all_gibbs_from_zip(files)

    if not surfaces_data:
        return None, None, None, [], "No valid Excel spreadsheets with a populated `5-gibbs` sheet were found in the uploaded zip."

    if len(surfaces_data) < 2:
        return None, None, None, surfaces_data, "Please upload a zip archive containing at least two catalyst spreadsheets/folders to perform comparison."

    for s in surfaces_data:
        s["delta_g_shifted"] = round(s["delta_g"] - u_pot + 0.0592 * ph, 4)

    gibbs_img_bytes = render_comparative_gibbs_graph(surfaces_data, u_pot, ph)
    ul_img_bytes = render_comparative_ul_graph(surfaces_data)

    for s in surfaces_data:
        root_match = re.match(r"^([^/]+)/", s["path"])
        root = f"{root_match.group(1)}/" if root_match else ""
        files[f"{root}5-data-visual/her_free_energy_comparison.png"] = gibbs_img_bytes
        files[f"{root}5-data-visual/her_ul_volcano_comparison.png"] = ul_img_bytes

    return build_zip_from_dict(files), gibbs_img_bytes, ul_img_bytes, surfaces_data, None
