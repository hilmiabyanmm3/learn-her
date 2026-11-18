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
from core.excel_manager import extract_zip_to_dict, build_zip_from_dict, extract_thermochem_robust, detect_reaction_type
from core.plotting import render_comparative_reaction_coordinate, render_comparative_volcano

st.set_page_config(
    page_title="Module 5: Multi-Catalyst Screening | Catalysis", 
    page_icon="https://img.icons8.com/?size=100&id=vtLGHdmfoSt8&format=png&color=000000", 
    layout="wide"
)
inject_global_css()
style_sidebar()
render_sidebar_progress(100)

module_header(
    "05", 
    "Multi-Catalyst Screening & Comparation", 
    "Multi-surface reaction coordinate comparison, Sabatier volcano positioning, and relative activity screening"
)

highlight_box(
    "<b>Multi-Catalyst Screening:</b> Upload an archive containing multiple catalyst folders or spreadsheets "
    "(e.g., <code>Pt111/</code>, <code>MoS2/</code>, <code>FeN4/</code>, <code>LaNiO3/</code>, etc.). "
    "Automatically identifies the reaction mechanism (<b>HER</b> or <b>OER</b>) and overlays all systems on a single "
    "comparative reaction profile and Limiting Potential ($U_L$) Sabatier Volcano.",
    box_type="info"
)

st.latex(r"\text{HER: } \Delta G_{\text{Volmer}}(U) = \Delta G_{\mathrm{H}^*} + eU, \quad \Delta G_{\text{Heyrovsky}}(U) = -\Delta G_{\mathrm{H}^*} + eU, \quad U_L = -\frac{\max(\Delta G_1, \Delta G_2)}{e}")

zip_file = st.file_uploader("Upload Multi-Surface Project ZIP", type=["zip"])

col1, col2 = st.columns(2)
with col1:
    u_val = st.number_input("Electrode Potential U (V vs RHE)", value=0.0, step=0.05)
with col2:
    ph_val = st.number_input("Solution pH", value=0.0, min_value=0.0, max_value=14.0, step=0.5)

if zip_file:
    if st.button("Run Multi-Catalyst Comparison →", type="primary"):
        with st.spinner("Analyzing multi-surface datasets and rendering diagrams..."):
            files = extract_zip_to_dict(zip_file.getvalue())
            
            # Robust reaction detection
            detected_rxn = detect_reaction_type(files)
            reaction = get_reaction(detected_rxn)

            surfaces_data = []
            validation_errors = []
            for path, data in files.items():
                if path.endswith('.xlsx') and not os.path.basename(path).startswith('~$'):
                    try:
                        wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
                        raw = extract_thermochem_robust(wb, reaction.name)
                        if not raw.get("surface") or raw["surface"] in ["Surface", "<surface>", ""]:
                            raw["surface"] = os.path.splitext(os.path.basename(path))[0].replace("_her_data_sheet", "").replace("_oer_data_sheet", "")
                        thermo = reaction.calculate_thermodynamics(raw, u_val, ph_val)
                        
                        # Enforce exact HER G2 = -G1 and +eU + 0.0592*pH cathodic shift
                        if reaction.name == "HER":
                            shift = u_val + 0.0592 * ph_val
                            dg_v = round(thermo["dg_volmer"], 4)
                            dg_h = round(-dg_v, 4)
                            thermo["dg_volmer"] = dg_v
                            thermo["dg_heyrovsky"] = dg_h
                            thermo["dg_volmer_shifted"] = round(dg_v + shift, 4)
                            thermo["dg_heyrovsky_shifted"] = round(dg_h + shift, 4)
                            thermo["steps"] = [thermo["dg_volmer_shifted"], thermo["dg_heyrovsky_shifted"]]

                        thermo["path"] = path
                        surfaces_data.append(thermo)
                    except ValueError as err:
                        validation_errors.append(f"**{os.path.basename(path)}**: {err}")
                    except Exception:
                        continue

            for verr in validation_errors:
                st.error(f"❌ Incomplete Data in {verr}")

            if len(surfaces_data) < 2:
                st.error("Please upload an archive containing at least two completed catalyst folders/spreadsheets.")
            else:
                st.success(f"Successfully compared {len(surfaces_data)} catalyst surfaces ({reaction.name})!")

                gibbs_img = render_comparative_reaction_coordinate(reaction, surfaces_data, u_val, ph_val)
                volcano_img = render_comparative_volcano(reaction, surfaces_data)

                # Save generated images into zip
                for s in surfaces_data:
                    root_match = re.match(r"^([^/]+)/", s["path"])
                    root = f"{root_match.group(1)}/" if root_match else ""
                    files[f"{root}5-data-visual/{reaction.name.lower()}_free_energy_comparison.png"] = gibbs_img
                    files[f"{root}5-data-visual/{reaction.name.lower()}_ul_volcano_comparison.png"] = volcano_img

                out_zip = build_zip_from_dict(files)

                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    sub_section_header(f"1. Comparative {reaction.name} Gibbs Profiles", "fa-solid fa-chart-line")
                    st.image(gibbs_img, caption=f"Multi-Catalyst {reaction.name} Free Energy Profiles (U={u_val:.2f} V, pH={ph_val:.1f})", use_container_width=True)

                with col_c2:
                    sub_section_header(f"2. Comparative {reaction.name} Sabatier Volcano", "fa-solid fa-mountain")
                    st.image(volcano_img, caption=f"Comparative {reaction.name} Volcano Overlay", use_container_width=True)

                st.markdown("---")
                sub_section_header("Comparative Performance Summary Table", "fa-solid fa-table-list")

                if reaction.name == "HER":
                    df_summary = pd.DataFrame([
                        {
                            "Surface": s["surface"],
                            "*H Adsorption ΔE (eV)": f"{s['delta_e']:.3f}",
                            "Volmer ΔG₁⁰ (eV)": f"{s['dg_volmer']:+.3f}",
                            "Heyrovsky ΔG₂⁰ (eV)": f"{s['dg_heyrovsky']:+.3f}",
                            f"Shifted ΔG₁(U={u_val:.2f} V) [eV]": f"{s['dg_volmer_shifted']:+.3f}",
                            f"Shifted ΔG₂(U={u_val:.2f} V) [eV]": f"{s['dg_heyrovsky_shifted']:+.3f}",
                            "Rate-Limiting Step (PDS)": s["pds"],
                            "Limiting Potential U_L (V)": f"{s['u_limiting']:+.3f}",
                            "Overpotential η (V)": f"{s['overpotential']:.3f}",
                            "Behavior": (
                                "Optimal (|ΔG⁰| ≤ 0.1 eV)" if abs(s['dg_volmer']) <= 0.1
                                else ("Weak H Binding (Volmer limiting)" if s['dg_volmer'] > 0.1
                                      else "Strong H Binding (Heyrovsky limiting)")
                            )
                        }
                        for s in surfaces_data
                    ])
                else:
                    df_summary = pd.DataFrame([
                        {
                            "Surface": s["surface"],
                            "Step 1 (OH*)": f"{(s['dg1'] + s['dg2']):+.3f} eV",
                            "Step 2 (O*)": f"{s['dg3']:+.3f} eV",
                            "Step 3 (OOH*)": f"{s['dg4']:+.3f} eV",
                            "Step 4 (O2)": f"{(s.get('dg5', 0.0) + s.get('dg6', 0.0)):+.3f} eV",
                            "Descriptor (ΔG_O - ΔG_OH)": f"{s['descriptor']:.3f} eV",
                            "Rate-Limiting Step (PDS)": s["pds"],
                            "Limiting Potential U_L": f"{s['u_limiting']:.3f} V",
                            "Overpotential η_OER": f"{s['overpotential']:.3f} V",
                        }
                        for s in surfaces_data
                    ])
                st.dataframe(df_summary, use_container_width=True)

                st.download_button(
                    label=f"⬇️ Download Multi-Surface {reaction.name} Comparison Archive",
                    data=out_zip,
                    file_name=f"MultiSurface_{reaction.name}_Comparison.zip",
                    mime="application/zip",
                    use_container_width=True
                )
