import os
import sys
import streamlit as st
import pandas as pd
import openpyxl
import io
import re

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from components.ui_components import (
    module_header, 
    sub_section_header, 
    highlight_box, 
    inject_global_css, 
    style_sidebar, 
    render_sidebar_progress
)
from config import get_reaction
from core.excel_manager import (
    extract_zip_to_dict, 
    build_zip_from_dict, 
    find_excel_file, 
    detect_reaction_type, 
    extract_thermochem_robust
)
from core.plotting import render_reaction_coordinate

st.set_page_config(
    page_title="Module 4: Delta Gibbs & Potential | Catalysis", 
    page_icon="https://img.icons8.com/?size=100&id=vtLGHdmfoSt8&format=png&color=000000", 
    layout="wide"
)
inject_global_css()
style_sidebar()
render_sidebar_progress(80)

if "mod4_run_history" not in st.session_state:
    st.session_state["mod4_run_history"] = []

module_header(
    "04", 
    "Delta Gibbs & Potential", 
    "Evaluate standard reaction free energies, compute Limiting Potential (U_L), and render reaction coordinate diagrams"
)

highlight_box(
    "<b>Objective:</b> Evaluates the reaction Gibbs free energy landscape and determines the "
    "<b>Limiting Potential ($U_L$)</b> and <b>Overpotential (&eta;)</b>. "
    "For OER, renders <b>both the 6-Step and 4-Step reaction coordinate diagrams</b> side-by-side on every run. "
    "Pressing the evaluate button multiple times at different potentials accumulates an <b>n &times; 2 visual grid</b> for direct potential-dependent comparison.",
    box_type="info"
)

st.latex(r"\text{HER: } \Delta G_{\text{Volmer}}(U) = \Delta G_{\mathrm{H}^*} + eU, \quad \Delta G_{\text{Heyrovsky}}(U) = -\Delta G_{\mathrm{H}^*} + eU \quad \Bigg| \quad \text{OER: } U_L = \frac{\max(\Delta G_i)}{e}")

zip_file = st.file_uploader("Upload Project ZIP (with populated tracking sheet)", type=["zip"])

col1, col2 = st.columns(2)
with col1:
    u_val = st.number_input("Electrode Potential U (V vs RHE)", value=0.0, step=0.05)
with col2:
    ph_val = st.number_input("Solution pH", value=0.0, min_value=0.0, max_value=14.0, step=0.5)

btn_col1, btn_col2 = st.columns([3, 1])
with btn_col1:
    run_clicked = st.button("Evaluate Gibbs Free Energy & Generate Diagram →", type="primary", use_container_width=True)
with btn_col2:
    if st.session_state["mod4_run_history"]:
        if st.button("🗑️ Clear Graph History", use_container_width=True):
            st.session_state["mod4_run_history"] = []
            st.rerun()

if zip_file and run_clicked:
    with st.spinner("Calculating reaction thermochemistry and rendering diagrams..."):
        files = extract_zip_to_dict(zip_file.getvalue())
        excel_info = find_excel_file(files)
        if not excel_info:
            st.error("No Excel tracking workbook found in uploaded archive.")
        else:
            excel_path, excel_bytes = excel_info
            wb = openpyxl.load_workbook(io.BytesIO(excel_bytes), data_only=False)
            rxn_name = detect_reaction_type(files, wb)
            reaction = get_reaction(rxn_name)

            raw_data = extract_thermochem_robust(wb, reaction.name)
            thermo = reaction.calculate_thermodynamics(raw_data, u_val, ph_val)

            # Update workbook sheet 5
            surface_name = thermo["surface"]
            if reaction.name == "HER":
                if "5-gibbs" in wb.sheetnames:
                    ws5 = wb["5-gibbs"]
                    ws5.cell(row=1, column=1, value="surface")
                    ws5.cell(row=1, column=2, value="adsorbate")
                    ws5.cell(row=1, column=3, value="e_g_1")
                    ws5.cell(row=1, column=4, value="e_g_2")
                    ws5.cell(row=1, column=5, value="u_l")
                    ws5.cell(row=2, column=1, value=surface_name)
                    ws5.cell(row=2, column=2, value="H")
                    ws5.cell(row=2, column=3, value=thermo["dg_volmer"])
                    ws5.cell(row=2, column=4, value="=-'5-gibbs'!C2")
                    ws5.cell(row=2, column=5, value="=-ABS('5-gibbs'!C2)")
            elif reaction.name == "OER":
                if "5-gibbs-steps" in wb.sheetnames:
                    ws5 = wb["5-gibbs-steps"]
                    ws5.cell(row=2, column=1, value=surface_name)
                    ws5.cell(row=2, column=2, value=thermo["dg1"])
                    ws5.cell(row=2, column=3, value=thermo["dg2"])
                    ws5.cell(row=2, column=4, value=thermo["dg3"])
                    ws5.cell(row=2, column=5, value=thermo["dg4"])
                    ws5.cell(row=2, column=6, value=thermo["dg5"])
                    ws5.cell(row=2, column=7, value=thermo["dg6"])
                    ws5.cell(row=2, column=8, value=thermo["g_max"])
                    ws5.cell(row=2, column=9, value=thermo["overpotential"])
                    ws5.cell(row=2, column=10, value=thermo["u_limiting"])

            out_buf = io.BytesIO()
            wb.save(out_buf)
            files[excel_path] = out_buf.getvalue()

            root_match = re.match(r"^([^/]+)/", excel_path)
            root = f"{root_match.group(1)}/" if root_match else ""
            run_idx = len(st.session_state["mod4_run_history"]) + 1
            u_tag = f"U{u_val:+.2f}V_pH{ph_val:.1f}".replace("+", "pos").replace("-", "neg")

            if reaction.name == "OER":
                _, levels_6, _ = reaction.get_reaction_coordinate_states(thermo, u_val, ph_val, step_mode="6-step")
                _, levels_4, _ = reaction.get_reaction_coordinate_states(thermo, u_val, ph_val, step_mode="4-step")
                all_levels = levels_6 + levels_4
                y_min_val, y_max_val = min(all_levels), max(all_levels)
                y_span = max(y_max_val - y_min_val, 0.5)
                shared_ylim = (y_min_val - 0.12 * y_span, y_max_val + 0.16 * y_span)

                img_left = render_reaction_coordinate(reaction, thermo, u_val, ph_val, step_mode="6-step", y_lim=shared_ylim)
                img_right = render_reaction_coordinate(reaction, thermo, u_val, ph_val, step_mode="4-step", y_lim=shared_ylim)
                cap_left = f"Run #{run_idx} — 6-Step OER Profile ({surface_name}, U = {u_val:.2f} V, pH = {ph_val:.1f})"
                cap_right = f"Run #{run_idx} — 4-Step OER Profile ({surface_name}, U = {u_val:.2f} V, pH = {ph_val:.1f})"
                files[f"{root}5-data-visual/oer_free_energy_6step_run{run_idx}_{u_tag}.png"] = img_left
                files[f"{root}5-data-visual/oer_free_energy_4step_run{run_idx}_{u_tag}.png"] = img_right
                files[f"{root}5-data-visual/oer_free_energy_diagram.png"] = img_right
            else:
                thermo_zero = reaction.calculate_thermodynamics(raw_data, 0.0, ph_val)
                img_left = render_reaction_coordinate(reaction, thermo_zero, 0.0, ph_val)
                img_right = render_reaction_coordinate(reaction, thermo, u_val, ph_val)
                cap_left = f"Run #{run_idx} — HER Baseline (U = 0.00 V, pH = {ph_val:.1f})"
                cap_right = f"Run #{run_idx} — HER Applied Potential (U = {u_val:.2f} V, pH = {ph_val:.1f})"
                files[f"{root}5-data-visual/her_free_energy_run{run_idx}_{u_tag}.png"] = img_right
                files[f"{root}5-data-visual/her_free_energy_diagram.png"] = img_right

            # Carry forward all previously generated PNGs into the latest ZIP
            for prev in st.session_state["mod4_run_history"]:
                for k_img, v_img in prev.get("saved_files", {}).items():
                    if k_img not in files:
                        files[k_img] = v_img

            saved_current = {k: v for k, v in files.items() if k.startswith(f"{root}5-data-visual/") and k.endswith(".png")}
            out_zip = build_zip_from_dict(files)

            st.session_state["mod4_run_history"].append({
                "run_idx": run_idx,
                "surface": surface_name,
                "reaction": reaction.name,
                "u_val": u_val,
                "ph_val": ph_val,
                "thermo": thermo,
                "img_left": img_left,
                "img_right": img_right,
                "cap_left": cap_left,
                "cap_right": cap_right,
                "saved_files": saved_current,
                "out_zip": out_zip,
            })

# Display accumulated n x 2 graph grid and latest thermochemical tables
if st.session_state["mod4_run_history"]:
    history = st.session_state["mod4_run_history"]
    latest = history[-1]
    surface_name = latest["surface"]
    rxn_type = latest["reaction"]
    thermo = latest["thermo"]
    u_latest = latest["u_val"]
    ph_latest = latest["ph_val"]

    st.success(f"**{surface_name}** ({rxn_type}) Thermodynamics evaluated! Showing **{len(history)} &times; 2** diagram grid across {len(history)} run(s).")

    # --- 1. n x 2 Graph Grid Display (Top Focus) ---
    sub_section_header(f"1. {rxn_type} Reaction Coordinate Diagrams ({len(history)} × 2 Grid)", "fa-solid fa-chart-line")

    for entry in history:
        st.markdown(f"**Run #{entry['run_idx']} — {entry['surface']} ($U = {entry['u_val']:+.2f}$ V vs. RHE, $\text{{pH}} = {entry['ph_val']:.1f}$)**")
        g_col1, g_col2 = st.columns(2)
        with g_col1:
            st.image(entry["img_left"], caption=entry["cap_left"], use_container_width=True)
        with g_col2:
            st.image(entry["img_right"], caption=entry["cap_right"], use_container_width=True)

    st.info(
        f"⚡ **Latest Run (#{latest['run_idx']}) Potential-Determining Step (PDS):** {thermo['pds']} | "
        f"**Limiting Potential ($U_L$):** `{thermo['u_limiting']:+.3f} V vs. RHE` | "
        f"**Overpotential (η):** `{thermo['overpotential']:.3f} V`"
    )

    st.markdown("---")

    # --- 2. Tabular Presentation (Latest Evaluation) ---
    sub_section_header(f"2. Elementary Step Thermochemical Data (Run #{latest['run_idx']}: U = {u_latest:+.2f} V, pH = {ph_latest:.1f})", "fa-solid fa-table")

    if rxn_type == "HER":
        v_std = thermo["dg_volmer"]
        h_std = thermo["dg_heyrovsky"]
        v_u = thermo["dg_volmer_shifted"]
        h_u = thermo["dg_heyrovsky_shifted"]

        df_her = pd.DataFrame([
            {
                "Step #": "Step 1 (Volmer)",
                "Elementary Reaction": "* + H⁺ + e⁻ → H*",
                "Intermediate": "H*",
                "ΔE (eV)": f"{thermo['delta_e']:.4f}",
                "ΔZPE (eV)": f"{thermo['delta_zpe']:.4f}",
                "-TΔS (eV)": f"{-thermo['t_delta_s']:.4f}",
                "ΔG⁰ (U=0 V) [eV]": f"{v_std:+.3f}",
                f"ΔG (U={u_latest:.2f} V) [eV]": f"{v_u:+.3f}",
                "Role / Status": "★ Rate-Limiting (PDS)" if thermo["pds"].startswith("Volmer") else ("Exergonic" if v_u <= 0 else "Endergonic")
            },
            {
                "Step #": "Step 2 (Heyrovsky)",
                "Elementary Reaction": "H* + H⁺ + e⁻ → * + H₂",
                "Intermediate": "H₂ (gas)",
                "ΔE (eV)": f"{-thermo['delta_e']:.4f}",
                "ΔZPE (eV)": f"{-thermo['delta_zpe']:.4f}",
                "-TΔS (eV)": f"{thermo['t_delta_s']:.4f}",
                "ΔG⁰ (U=0 V) [eV]": f"{h_std:+.3f}",
                f"ΔG (U={u_latest:.2f} V) [eV]": f"{h_u:+.3f}",
                "Role / Status": "★ Rate-Limiting (PDS)" if thermo["pds"].startswith("Heyrovsky") else ("Exergonic" if h_u <= 0 else "Endergonic")
            }
        ])
        st.dataframe(df_her, use_container_width=True)

    else:
        # 4-Step OER Table
        dg1_4_std = round(thermo["dg1"] + thermo["dg2"], 4)
        dg2_4_std = round(thermo["dg3"], 4)
        dg3_4_std = round(thermo["dg4"], 4)
        dg4_4_std = round(thermo["dg5"] + thermo["dg6"], 4)

        dg1_4_u = round(thermo["dg1_u"] + thermo["dg2_u"], 4)
        dg2_4_u = round(thermo["dg3_u"], 4)
        dg3_4_u = round(thermo["dg4_u"], 4)
        dg4_4_u = round(thermo["dg5_u"] + thermo["dg6_u"], 4)

        steps_std = [dg1_4_std, dg2_4_std, dg3_4_std, dg4_4_std]
        steps_u = [dg1_4_u, dg2_4_u, dg3_4_u, dg4_4_u]
        
        levels = [0.0]
        for s in steps_u:
            levels.append(round(levels[-1] + s, 4))

        max_std = max(steps_std)

        df_oer_4step = pd.DataFrame([
            {
                "Step #": "Step 1",
                "Elementary Reaction": "* + H₂O → OH* + H⁺ + e⁻",
                "Adsorbate": "OH*",
                "ΔG⁰ (U=0 V) [eV]": f"{dg1_4_std:+.3f}",
                f"ΔG (U={u_latest:.2f} V) [eV]": f"{dg1_4_u:+.3f}",
                "Energy Level G [eV]": f"{levels[1]:+.3f}",
                "Step Status": "★ Rate-Limiting (PDS)" if dg1_4_std == max_std else ("Exergonic" if dg1_4_u <= 0 else "Endergonic")
            },
            {
                "Step #": "Step 2",
                "Elementary Reaction": "OH* → O* + H⁺ + e⁻",
                "Adsorbate": "O*",
                "ΔG⁰ (U=0 V) [eV]": f"{dg2_4_std:+.3f}",
                f"ΔG (U={u_latest:.2f} V) [eV]": f"{dg2_4_u:+.3f}",
                "Energy Level G [eV]": f"{levels[2]:+.3f}",
                "Step Status": "★ Rate-Limiting (PDS)" if dg2_4_std == max_std else ("Exergonic" if dg2_4_u <= 0 else "Endergonic")
            },
            {
                "Step #": "Step 3",
                "Elementary Reaction": "O* + H₂O → OOH* + H⁺ + e⁻",
                "Adsorbate": "OOH*",
                "ΔG⁰ (U=0 V) [eV]": f"{dg3_4_std:+.3f}",
                f"ΔG (U={u_latest:.2f} V) [eV]": f"{dg3_4_u:+.3f}",
                "Energy Level G [eV]": f"{levels[3]:+.3f}",
                "Step Status": "★ Rate-Limiting (PDS)" if dg3_4_std == max_std else ("Exergonic" if dg3_4_u <= 0 else "Endergonic")
            },
            {
                "Step #": "Step 4",
                "Elementary Reaction": "OOH* → * + O₂ + H⁺ + e⁻",
                "Adsorbate": "O₂ (gas)",
                "ΔG⁰ (U=0 V) [eV]": f"{dg4_4_std:+.3f}",
                f"ΔG (U={u_latest:.2f} V) [eV]": f"{dg4_4_u:+.3f}",
                "Energy Level G [eV]": f"{levels[4]:+.3f}",
                "Step Status": "★ Rate-Limiting (PDS)" if dg4_4_std == max_std else ("Exergonic" if dg4_4_u <= 0 else "Endergonic")
            }
        ])
        st.dataframe(df_oer_4step, use_container_width=True)

        with st.expander("🔍 View Raw 6-Step Elementary Decomposition Table"):
            df_oer_6step = pd.DataFrame([
                {"Step #": "Step 1", "Reaction Type": "Chemical Adsorption", "Elementary Step": "* + H₂O → H₂O*", "Intermediate": "H₂O*", "ΔG⁰ (U=0 V) [eV]": f"{thermo['dg1']:+.3f}", f"ΔG(U) [eV]": f"{thermo['dg1_u']:+.3f}"},
                {"Step #": "Step 2", "Reaction Type": "Electrochemical (1e⁻)", "Elementary Step": "H₂O* → OH* + H⁺ + e⁻", "Intermediate": "OH*", "ΔG⁰ (U=0 V) [eV]": f"{thermo['dg2']:+.3f}", f"ΔG(U) [eV]": f"{thermo['dg2_u']:+.3f}"},
                {"Step #": "Step 3", "Reaction Type": "Electrochemical (1e⁻)", "Elementary Step": "OH* → O* + H⁺ + e⁻", "Intermediate": "O*", "ΔG⁰ (U=0 V) [eV]": f"{thermo['dg3']:+.3f}", f"ΔG(U) [eV]": f"{thermo['dg3_u']:+.3f}"},
                {"Step #": "Step 4", "Reaction Type": "Electrochemical (1e⁻)", "Elementary Step": "O* + H₂O → OOH* + H⁺ + e⁻", "Intermediate": "OOH*", "ΔG⁰ (U=0 V) [eV]": f"{thermo['dg4']:+.3f}", f"ΔG(U) [eV]": f"{thermo['dg4_u']:+.3f}"},
                {"Step #": "Step 5", "Reaction Type": "Electrochemical (1e⁻)", "Elementary Step": "OOH* → O₂* + H⁺ + e⁻", "Intermediate": "O₂*", "ΔG⁰ (U=0 V) [eV]": f"{thermo['dg5']:+.3f}", f"ΔG(U) [eV]": f"{thermo['dg5_u']:+.3f}"},
                {"Step #": "Step 6", "Reaction Type": "Chemical Desorption", "Elementary Step": "O₂* → * + O₂", "Intermediate": "O₂ (gas)", "ΔG⁰ (U=0 V) [eV]": f"{thermo['dg6']:+.3f}", f"ΔG(U) [eV]": f"{thermo['dg6_u']:+.3f}"}
            ])
            st.dataframe(df_oer_6step, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button(
        label=f"⬇️ Download Completed {surface_name} Archive (with All {len(history) * 2} Figures & Excel)",
        data=latest["out_zip"],
        file_name=f"{surface_name}_Module4_{rxn_type}_Completed.zip",
        mime="application/zip",
        use_container_width=True
    )
