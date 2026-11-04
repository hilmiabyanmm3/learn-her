import io
import re
import openpyxl
import matplotlib.pyplot as plt
import numpy as np
from utils.common import extract_zip_to_dict, build_zip_from_dict, find_excel_file, RY_TO_EV

def render_gibbs_reaction_profile(
    surface_name: str, delta_g_shifted: float, u_pot: float = 0.0, ph: float = 0.0
) -> bytes:
    """
    Renders Graph 1: Gibbs Free Energy Profile (Reaction Coordinate).
    x-axis: Reaction Coordinate (H+ + e-, H*, 1/2 H2)
    y-axis: Free Energy Delta G (eV)
    """
    fig, ax = plt.subplots(figsize=(7.2, 4.8), dpi=300)
    steps = [r"$\mathrm{H}^+ + \mathrm{e}^-$", r"$\mathrm{H}^*$", r"$\frac{1}{2}\mathrm{H}_2$"]
    x_mid = [0.5, 1.5, 2.5]
    width = 0.36
    bar_thickness = 2.4

    # Baseline references at 0.0 eV
    ax.hlines(0.0, x_mid[0] - width/2, x_mid[0] + width/2, colors="#1e293b", linewidth=bar_thickness)
    ax.hlines(0.0, x_mid[2] - width/2, x_mid[2] + width/2, colors="#1e293b", linewidth=bar_thickness)

    ax.text(x_mid[0], 0.025, "0.00 eV", ha='center', va='bottom', fontsize=10, fontweight='bold', color="#1e293b")
    ax.text(x_mid[2], 0.025, "0.00 eV", ha='center', va='bottom', fontsize=10, fontweight='bold', color="#1e293b")

    h_x_start = x_mid[1] - width/2
    h_x_end = x_mid[1] + width/2

    color = "#1e3a8a" if abs(delta_g_shifted) <= 0.1 else ("#ef4444" if delta_g_shifted > 0 else "#2563eb")
    ax.hlines(delta_g_shifted, h_x_start, h_x_end, colors=color, linewidth=bar_thickness)
    ax.text(x_mid[1], delta_g_shifted + 0.025, f"{delta_g_shifted:+.2f} eV", ha='center', va='bottom', fontsize=10, fontweight='bold', color=color)

    ax.plot([x_mid[0] + width/2, h_x_start], [0.0, delta_g_shifted], 'k--', alpha=0.5, linewidth=1.2)
    ax.plot([h_x_end, x_mid[2] - width/2], [delta_g_shifted, 0.0], 'k--', alpha=0.5, linewidth=1.2)

    ax.set_xticks(x_mid)
    ax.set_xticklabels(steps, fontsize=12, fontweight='bold')
    ax.set_ylabel(r"Free Energy $\Delta G$ (eV)", fontsize=11, fontweight='bold')
    ax.set_title(f"HER Free Energy Profile — {surface_name}\n(U = {u_pot:.2f} V vs. RHE, pH = {ph:.1f})", fontsize=12, fontweight='bold', pad=14)
    ax.axhline(0, color='gray', linestyle=':', alpha=0.5)
    ax.set_xlim(0, 3.0)
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=300)
    plt.close(fig)
    return buf.getvalue()

def render_ul_graph(surface_name: str, delta_e: float, delta_g: float) -> bytes:
    """
    Renders Graph 2: The Limiting Potential (U_L) Graph.
    x-axis: *H Adsorption Energy Delta E_H* (eV)
    y-axis: Limiting Potential U_L (V vs. RHE)
    """
    fig, ax = plt.subplots(figsize=(7.2, 4.8), dpi=300)

    # Thermochemical correction Delta ZPE - T Delta S
    corr = delta_g - delta_e if (delta_g is not None and delta_e is not None) else 0.24
    de_peak = -corr

    # Theoretical Sabatier Volcano lines vs. *H adsorption energy:
    de_neg = np.linspace(-1.0, de_peak, 100)
    de_pos = np.linspace(de_peak, 0.6, 100)

    ul_neg = de_neg + corr      # Heyrovsky branch: slope = +1
    ul_pos = -(de_pos + corr)   # Volmer branch: slope = -1

    ax.plot(de_neg, ul_neg, color="#dc2626", linewidth=2.5,
            label=rf"Heyrovsky / Tafel Limiting ($\Delta E_{{\mathrm{{H}}^*}} < {de_peak:.2f}$ eV)")
    ax.plot(de_pos, ul_pos, color="#2563eb", linewidth=2.5,
            label=rf"Volmer Limiting ($\Delta E_{{\mathrm{{H}}^*}} > {de_peak:.2f}$ eV)")

    # Volcano Peak (Ideal catalyst at U_L = 0 V)
    ax.scatter([de_peak], [0.0], color="#16a34a", s=130, zorder=5, marker="*",
               label=f"Ideal Volcano Apex ({de_peak:.2f} eV, 0.0 V)")

    # Current catalyst point (x = Delta E_H*, y = U_L)
    ul_val = -abs(delta_g)
    ax.scatter([delta_e], [ul_val], color="#7c3aed", s=140, zorder=6, edgecolors="black", linewidths=1.5,
               label=f"{surface_name} ($\Delta E = {delta_e:+.2f}$ eV, $U_L = {ul_val:+.2f}$ V)")

    # Dashed drop lines to axes
    ax.plot([delta_e, delta_e], [-1.0, ul_val], "k:", alpha=0.45)
    ax.plot([-1.2, delta_e], [ul_val, ul_val], "k:", alpha=0.45)

    ax.set_xlabel(r"*H Adsorption Energy $\Delta E_{\mathrm{H}^*}$ (eV)", fontsize=11, fontweight="bold")
    ax.set_ylabel(r"Limiting Potential $U_L$ (V vs. RHE)", fontsize=11, fontweight="bold")
    ax.set_title(f"Limiting Potential ($U_L$) Graph — {surface_name}", fontsize=12, fontweight="bold", pad=14)
    ax.set_xlim(-1.0, 0.6)
    ax.set_ylim(-0.85, 0.1)
    ax.axhline(0, color="gray", linestyle="--", alpha=0.4)
    ax.axvline(de_peak, color="gray", linestyle=":", alpha=0.4)
    ax.grid(True, linestyle="--", alpha=0.3)
    ax.legend(loc="lower center", frameon=True, fontsize=8.5)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=300)
    plt.close(fig)
    return buf.getvalue()

def calculate_gibbs_and_visualize(
    zip_bytes: bytes, u_pot: float = 0.0, ph: float = 0.0
) -> tuple[bytes | None, dict | None, bytes | None, bytes | None, str | None]:
    """
    Computes Delta G_H* and Limiting Potential U_L, updates sheet 5-gibbs,
    and produces two SEPARATE graphs:
      1. gibbs_img_bytes: Gibbs Free Energy Profile (Reaction Coordinate).
      2. ul_img_bytes: Limiting Potential (U_L) Graph (y: U_L, x: *H Adsorption Energy Delta E_H*).
    Saves both as separate PNG files in `5-data-visual/`:
      - `5-data-visual/her_free_energy_diagram.png`
      - `5-data-visual/her_limiting_potential_diagram.png`
    """
    files = extract_zip_to_dict(zip_bytes)
    excel_info = find_excel_file(files)
    if not excel_info:
        return None, None, None, None, "No Excel spreadsheet found in the uploaded zip."

    excel_path, excel_bytes = excel_info
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes), data_only=False)

    if "5-gibbs" not in wb.sheetnames:
        return None, None, None, None, "Sheet `5-gibbs` not found in workbook."

    ws1 = wb["1-adsorbate"]
    ws2 = wb["2-isolated-mol"]
    ws3 = wb["3-ads-energy"]
    ws4 = wb["4-vibrasi"]
    ws5 = wb["5-gibbs"]

    surface_name = ws1.cell(row=2, column=1).value or "Surface"

    # Ground state electronic energies
    e_surf_ry = ws1.cell(row=2, column=2).value
    e_surf_ev = float(e_surf_ry) * RY_TO_EV if isinstance(e_surf_ry, (int, float)) else None

    e_ads_ry = ws1.cell(row=2, column=4).value
    e_ads_ev = float(e_ads_ry) * RY_TO_EV if isinstance(e_ads_ry, (int, float)) else None

    e_h2 = float(ws2.cell(row=2, column=2).value or -31.7452)
    zpe_h2 = float(ws2.cell(row=2, column=3).value or 0.2720)
    ts_h2 = float(ws2.cell(row=2, column=4).value or 0.4040)

    if e_ads_ev is not None and e_surf_ev is not None:
        delta_e = e_ads_ev - e_surf_ev - 0.5 * e_h2
    else:
        raw_b2 = ws3.cell(row=2, column=2).value
        delta_e = float(raw_b2) if isinstance(raw_b2, (int, float)) else 0.0

    zpe_h = sum(
        float(ws4.cell(row=r, column=3).value or 0.0)
        for r in range(2, ws4.max_row + 1)
        if ws4.cell(row=r, column=3).value is not None
    )

    delta_zpe = zpe_h - 0.5 * zpe_h2
    t_delta_s = -0.5 * ts_h2
    delta_g_base = delta_e + delta_zpe + 0.5 * ts_h2

    # Calculate Limiting Potential U_L (V) and Overpotential eta (V)
    u_limiting = -abs(delta_g_base)
    overpotential = abs(delta_g_base)

    # Write to sheet 5-gibbs: C2 = Delta G_H*, D2 = U_L
    ws5.cell(row=1, column=4, value="u_l")
    ws5.cell(row=2, column=1, value=surface_name)
    ws5.cell(row=2, column=2, value="H")
    ws5.cell(row=2, column=3, value=round(delta_g_base, 4))
    ws5.cell(row=2, column=4, value=round(u_limiting, 4))

    out_buf = io.BytesIO()
    wb.save(out_buf)
    files[excel_path] = out_buf.getvalue()

    # 1. Render Graph 1: Gibbs Free Energy Profile (Reaction Coordinate)
    delta_g_shifted = round(delta_g_base - u_pot + 0.0592 * ph, 4)
    gibbs_img_bytes = render_gibbs_reaction_profile(surface_name, delta_g_shifted, u_pot, ph)

    # 2. Render Graph 2: The Limiting Potential (U_L) Graph (x: *H Adsorption Energy delta_e, y: U_L)
    ul_img_bytes = render_ul_graph(surface_name, delta_e, delta_g_base)

    # Save both as separate image files in 5-data-visual/
    root_match = re.match(r"^([^/]+)/", excel_path)
    root = f"{root_match.group(1)}/" if root_match else ""
    files[f"{root}5-data-visual/her_free_energy_diagram.png"] = gibbs_img_bytes
    files[f"{root}5-data-visual/her_limiting_potential_diagram.png"] = ul_img_bytes

    summary = {
        "surface": surface_name,
        "delta_e": delta_e,
        "delta_zpe": delta_zpe,
        "t_delta_s": t_delta_s,
        "delta_g": delta_g_base,
        "delta_g_shifted": delta_g_shifted,
        "u_limiting": u_limiting,
        "overpotential": overpotential
    }

    return build_zip_from_dict(files), summary, gibbs_img_bytes, ul_img_bytes, None
