import os
import sys
import streamlit as st
import pandas as pd
import openpyxl
import io

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
from core.qe_parser import parse_qe_total_energy, parse_qe_atomic_positions, filter_topmost_active_sites
from core.cell_builder import build_adsorbate_system, build_all_adsorbate_systems, DEFAULT_HEIGHTS
from core.excel_manager import extract_zip_to_dict, build_zip_from_dict, find_excel_file, detect_reaction_type

st.set_page_config(
    page_title="Module 2: Adsorbate Creation | Catalysis", 
    page_icon="https://img.icons8.com/?size=100&id=vtLGHdmfoSt8&format=png&color=000000", 
    layout="wide"
)
inject_global_css()
style_sidebar()
render_sidebar_progress(40)

module_header("02", "Adsorbate Creation & Active Site Selection", "Identify topmost catalytic sites and construct adsorbate configuration")

highlight_box(
    "<b>Input Requirements:</b> Upload your workspace ZIP containing completed surface relaxation: "
    "<code>1-surface/PW.in</code> and <code>1-surface/PW.out</code>.",
    box_type="info"
)

uploaded_zip = st.file_uploader("Upload Project ZIP (containing 1-surface/PW.in & PW.out)", type=["zip"])

if uploaded_zip:
    files = extract_zip_to_dict(uploaded_zip.getvalue())
    in_key = next((k for k in files if k.endswith("1-surface/PW.in")), None)
    out_key = next((k for k in files if k.endswith("1-surface/PW.out")), None)

    if not in_key or not out_key:
        st.error("Missing `1-surface/PW.in` or `1-surface/PW.out` in the uploaded zip file.")
    else:
        out_content = files[out_key].decode("utf-8", errors="ignore") if isinstance(files[out_key], bytes) else files[out_key]
        e_ry, e_ev = parse_qe_total_energy(out_content)
        unit, atoms = parse_qe_atomic_positions(out_content)
        sites = filter_topmost_active_sites(atoms)
        
        detected_rxn_name = detect_reaction_type(files)
        reaction = get_reaction(detected_rxn_name)

        st.success(f"Successfully parsed `1-surface/PW.out`! Active Mechanism: **{reaction.name}**.")
        
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            st.metric("Pristine Slab Energy (Ry)", f"{e_ry:.6f} Ry" if e_ry else "N/A")
        with m_col2:
            st.metric("Pristine Slab Energy (eV)", f"{e_ev:.4f} eV" if e_ev else "N/A")
            
        sub_section_header("Topmost Layer Active Catalytic Sites", "fa-solid fa-crosshairs")
        if not sites:
            st.warning("No candidate active site atoms detected within the top layer threshold.")
        else:
            df_sites = pd.DataFrame(sites)
            st.dataframe(df_sites, use_container_width=True)
            
            site_options = [f"Atom #{s['index']} - {s['element']} (z = {s['z']:.3f} Å)" for s in sites]
            chosen_site_str = st.selectbox("Select Active Site for Adsorption:", site_options)
            chosen_idx = int(chosen_site_str.split("#")[1].split()[0])
            
            is_multi = len(reaction.intermediates) > 1

            if is_multi:
                sub_section_header("Adsorption Generation Mode", "fa-solid fa-layer-group")
                inter_list_str = ", ".join(reaction.intermediates)
                mode = st.radio(
                    "Adsorption Target:",
                    [f"All Intermediates (Recommended: Batch Generate {inter_list_str})", "Single Intermediate Only"],
                    index=0
                )
            else:
                mode = "Single Intermediate Only"

            if "All" in mode:
                st.markdown("**Surface–Adsorbate Bond Length (Å) per Intermediate:**")
                heights_map = {}
                h_cols = st.columns(len(reaction.intermediates))
                for col_ui, inter in zip(h_cols, reaction.intermediates):
                    inter_clean = inter.replace("*", "").strip().upper()
                    default_len = DEFAULT_HEIGHTS.get(inter_clean, 1.4)
                    with col_ui:
                        heights_map[inter_clean] = st.number_input(
                            f"{inter_clean}* Length (Å)",
                            min_value=0.50,
                            max_value=4.00,
                            value=float(default_len),
                            step=0.05,
                            format="%.2f",
                            key=f"batch_len_{inter_clean}"
                        )

                st.info(f"💡 **Batch Mode Active:** Constructs `PW.in` files for all {len(reaction.intermediates)} intermediates (`{inter_list_str}`) on Atom #{chosen_idx} using your specified surface–adsorbate lengths.")
                btn_label = f"Generate All {reaction.name} Adsorbate Structures →"
                if st.button(btn_label, type="primary"):
                    updated_files = build_all_adsorbate_systems(files, chosen_idx, reaction.intermediates, heights_map=heights_map)
                    
                    # Update clean surface energy in Excel (supports both OER and HER templates)
                    excel_info = find_excel_file(updated_files)
                    if excel_info and e_ry is not None:
                        excel_path, excel_bytes = excel_info
                        wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
                        if "1-adsorbates" in wb.sheetnames:
                            ws = wb["1-adsorbates"]
                            clean_row = 2
                            for r in range(2, ws.max_row + 1):
                                if str(ws.cell(row=r, column=2).value or "").strip().lower() in ["clean", "surface", "*"]:
                                    clean_row = r
                                    break
                            ws.cell(row=clean_row, column=3, value=e_ry)
                            ws.cell(row=clean_row, column=4, value=f"=C{clean_row}*13.605698066")
                        elif "1-adsorbate" in wb.sheetnames:
                            ws = wb["1-adsorbate"]
                            ws.cell(row=2, column=2, value=e_ry)
                            ws.cell(row=2, column=3, value="='1-adsorbate'!B2*13.605698066")

                        out_buf = io.BytesIO()
                        wb.save(out_buf)
                        updated_files[excel_path] = out_buf.getvalue()

                    updated_zip = build_zip_from_dict(updated_files)
                    st.success(f"All {len(reaction.intermediates)} intermediate structures successfully generated into `3-adsorption/`!")
                    summary_rows = [
                        {
                            "Intermediate": f"{inter.replace('*', '').strip()}*",
                            "Anchor Site": f"Atom #{chosen_idx}",
                            "Surface–Adsorbate Length (Å)": f"{heights_map[inter.replace('*', '').strip().upper()]:.2f}",
                            "Generated Input": f"3-adsorption/{inter.replace('*', '').strip()}/PW.in"
                        }
                        for inter in reaction.intermediates
                    ]
                    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)
                    st.download_button(
                        label="⬇️ Download Updated Project ZIP (All Adsorbates Added)",
                        data=updated_zip,
                        file_name=f"Project_Module2_{reaction.name}_AllAdsorbates.zip",
                        mime="application/zip"
                    )
            else:
                col_inter, col_h = st.columns(2)
                with col_inter:
                    chosen_intermediate = st.selectbox("Select Adsorbate to Bind:", reaction.intermediates, index=0)
                with col_h:
                    default_h = DEFAULT_HEIGHTS.get(chosen_intermediate.replace("*", "").strip().upper(), 1.4)
                    h_dist = st.number_input(
                        "Surface–Adsorbate Length (Å above selected site):",
                        min_value=0.50,
                        max_value=4.00,
                        value=float(default_h),
                        step=0.05,
                        format="%.2f"
                    )

                btn_label = f"Generate {chosen_intermediate} Adsorbate Structure (3-adsorption/{chosen_intermediate}/PW.in) →"
                if st.button(btn_label, type="primary"):
                    updated_files = build_adsorbate_system(files, chosen_idx, h_dist, chosen_intermediate)
                    
                    excel_info = find_excel_file(updated_files)
                    if excel_info and e_ry is not None:
                        excel_path, excel_bytes = excel_info
                        wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
                        if "1-adsorbate" in wb.sheetnames:
                            ws = wb["1-adsorbate"]
                            ws.cell(row=2, column=2, value=e_ry)
                            ws.cell(row=2, column=3, value="='1-adsorbate'!B2*13.605698066")
                        elif "1-adsorbates" in wb.sheetnames:
                            ws = wb["1-adsorbates"]
                            clean_row = 2
                            for r in range(2, ws.max_row + 1):
                                if str(ws.cell(row=r, column=2).value or "").strip().lower() in ["clean", "surface", "*"]:
                                    clean_row = r
                                    break
                            ws.cell(row=clean_row, column=3, value=e_ry)
                            ws.cell(row=clean_row, column=4, value=f"=C{clean_row}*13.605698066")

                        out_buf = io.BytesIO()
                        wb.save(out_buf)
                        updated_files[excel_path] = out_buf.getvalue()
                    
                    updated_zip = build_zip_from_dict(updated_files)
                    st.success(f"{chosen_intermediate} structure (length = {h_dist:.2f} Å) successfully generated into `3-adsorption/{chosen_intermediate}/PW.in`!")
                    st.download_button(
                        label=f"⬇️ Download Updated Project ZIP ({chosen_intermediate} Added)",
                        data=updated_zip,
                        file_name=f"Project_Module2_{chosen_intermediate}_Adsorbate.zip",
                        mime="application/zip"
                    )
