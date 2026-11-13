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
from core.qe_parser import parse_qe_total_energy
from core.displacement_builder import generate_finite_displacements, parse_vibrational_frequencies, CM_TO_EV
from core.excel_manager import extract_zip_to_dict, build_zip_from_dict, find_excel_file, detect_reaction_type

st.set_page_config(
    page_title="Module 3: Adsorption & Vibrations | Catalysis", 
    page_icon="https://img.icons8.com/?size=100&id=vtLGHdmfoSt8&format=png&color=000000", 
    layout="wide"
)
inject_global_css()
style_sidebar()
render_sidebar_progress(60)

module_header("03", "Adsorption Energy & Vibrational Logistics", "Extract electronic energies, create finite displacements, and evaluate vibrational zero-point energy")

tab1, tab2 = st.tabs(["Tab 1: Adsorption Energy & Vibration Setup", "Tab 2: Vibrational Modes & ZPE Extraction"])

with tab1:
    highlight_box(
        "<b>Tab 1 Workflow:</b> Upload ZIP with completed calculations: <code>3-adsorption/&lt;species&gt;/PW.out</code> and "
        "gas references in <code>2-isolated-gas/</code>. By default, processes <b>every available intermediate</b>, updates Excel, and creates finite displacement inputs in <code>4-vibration/&lt;species&gt;/</code>.",
        box_type="info"
    )
    zip_tab1 = st.file_uploader("Upload Project ZIP for Tab 1", type=["zip"], key="zip_tab1")
    if zip_tab1:
        files = extract_zip_to_dict(zip_tab1.getvalue())
        rxn_name = detect_reaction_type(files)
        reaction = get_reaction(rxn_name)
        st.info(f"Detected Mechanism: **{reaction.name}** ({reaction.full_name})")

        is_multi = len(reaction.intermediates) > 1
        if is_multi:
            tab1_mode = st.radio(
                "Processing Scope:",
                ["All Available Intermediates (Recommended Default)", "Single Intermediate Only"],
                index=0,
                key="tab1_scope"
            )
        else:
            tab1_mode = "Single Intermediate Only"

        if "All" in tab1_mode:
            if st.button(f"Process All {reaction.name} Intermediates & Create Displacements →", type="primary"):
                excel_info = find_excel_file(files)
                wb, excel_path = None, None
                if excel_info:
                    excel_path, excel_bytes = excel_info
                    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))

                # 1. Parse clean surface if present in the uploaded archive
                surf_out_key = next((k for k in files if k.endswith("1-surface/PW.out")), None)
                if surf_out_key and wb:
                    content_surf = files[surf_out_key].decode("utf-8", errors="ignore") if isinstance(files[surf_out_key], bytes) else files[surf_out_key]
                    e_surf_ry, e_surf_ev = parse_qe_total_energy(content_surf)
                    if e_surf_ry is not None:
                        if "1-adsorbates" in wb.sheetnames:
                            ws1 = wb["1-adsorbates"]
                            for r in range(2, ws1.max_row + 1):
                                if str(ws1.cell(row=r, column=2).value or "").strip().lower() in ["clean", "surface"]:
                                    ws1.cell(row=r, column=3, value=e_surf_ry)
                                    ws1.cell(row=r, column=4, value=f"=C{r}*13.605698066")
                        elif "1-adsorbate" in wb.sheetnames:
                            ws1 = wb["1-adsorbate"]
                            ws1.cell(row=2, column=2, value=e_surf_ry)
                            ws1.cell(row=2, column=3, value="='1-adsorbate'!B2*13.605698066")

                # 2. Parse gas references
                h2_key = next((k for k in files if k.endswith("2-isolated-gas/H2/PW.out")), None)
                h2o_key = next((k for k in files if k.endswith("2-isolated-gas/H2O/PW.out")), None)
                o2_key = next((k for k in files if k.endswith("2-isolated-gas/O2/PW.out")), None)
                e_h2 = parse_qe_total_energy(files[h2_key].decode("utf-8", errors="ignore"))[1] if h2_key else None
                e_h2o = parse_qe_total_energy(files[h2o_key].decode("utf-8", errors="ignore"))[1] if h2o_key else None
                e_o2 = parse_qe_total_energy(files[o2_key].decode("utf-8", errors="ignore"))[1] if o2_key else None

                if wb and "2-isolated-mol" in wb.sheetnames:
                    ws2 = wb["2-isolated-mol"]
                    for r in range(2, ws2.max_row + 1):
                        mol = str(ws2.cell(row=r, column=1).value or "").upper()
                        if "H2_GAS" in mol or mol == "H2":
                            if e_h2 is not None: ws2.cell(row=r, column=3, value=e_h2)
                        elif "H2O_GAS" in mol or mol == "H2O":
                            if e_h2o is not None: ws2.cell(row=r, column=3, value=e_h2o)
                        elif "O2_GAS" in mol or mol == "O2":
                            if e_o2 is not None: ws2.cell(row=r, column=3, value=e_o2)

                # 3. Parse all intermediate adsorption energies and build displacements
                processed = []
                for inter in reaction.intermediates:
                    inter_clean = inter.replace("*", "").strip()
                    ads_out_key = next((k for k in files if k.endswith(f"3-adsorption/{inter_clean}/PW.out")), None)
                    if ads_out_key:
                        content = files[ads_out_key].decode("utf-8", errors="ignore") if isinstance(files[ads_out_key], bytes) else files[ads_out_key]
                        e_ry, e_ev = parse_qe_total_energy(content)
                        if e_ry is not None:
                            if wb:
                                if reaction.name == "HER" and "1-adsorbate" in wb.sheetnames:
                                    ws1 = wb["1-adsorbate"]
                                    ws1.cell(row=2, column=4, value=e_ry)
                                    ws1.cell(row=2, column=5, value="='1-adsorbate'!D2*13.605698066")
                                elif "1-adsorbates" in wb.sheetnames:
                                    ws1 = wb["1-adsorbates"]
                                    for r in range(2, ws1.max_row + 1):
                                        if str(ws1.cell(row=r, column=2).value).replace("*", "").strip().upper() == inter_clean.upper():
                                            ws1.cell(row=r, column=3, value=e_ry)
                                            ws1.cell(row=r, column=4, value=f"=C{r}*13.605698066")
                            
                            files = generate_finite_displacements(files, inter_clean)
                            processed.append({"Intermediate": inter_clean, "E (Ry)": f"{e_ry:.6f}", "E (eV)": f"{e_ev:.4f}", "Status": "Displacements Generated"})

                if wb and excel_path:
                    buf = io.BytesIO()
                    wb.save(buf)
                    files[excel_path] = buf.getvalue()

                out_zip = build_zip_from_dict(files)
                if processed:
                    st.success(f"Successfully processed {len(processed)} intermediates and generated displacement inputs in `4-vibration/`!")
                    st.dataframe(pd.DataFrame(processed), use_container_width=True)
                else:
                    st.warning("No completed `PW.out` files found in `3-adsorption/`. Please check your calculations.")

                st.download_button(
                    label=f"⬇️ Download Project ZIP with All Displacements",
                    data=out_zip,
                    file_name=f"Project_Module3_{reaction.name}_AllTab1.zip",
                    mime="application/zip",
                    use_container_width=True
                )
        else:
            chosen_inter = st.selectbox("Intermediate to Process:", reaction.intermediates, index=0)
            if st.button("Process Single Intermediate →", type="primary"):
                ads_out_key = next((k for k in files if k.endswith(f"3-adsorption/{chosen_inter}/PW.out")), None)
                if not ads_out_key:
                    st.error(f"Missing `3-adsorption/{chosen_inter}/PW.out` in the uploaded zip.")
                else:
                    content = files[ads_out_key].decode("utf-8", errors="ignore") if isinstance(files[ads_out_key], bytes) else files[ads_out_key]
                    e_ry, e_ev = parse_qe_total_energy(content)
                    excel_info = find_excel_file(files)
                    if excel_info and e_ry is not None:
                        excel_path, excel_bytes = excel_info
                        wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))

                        # Also sync clean surface if present
                        surf_out_key = next((k for k in files if k.endswith("1-surface/PW.out")), None)
                        if surf_out_key:
                            content_s = files[surf_out_key].decode("utf-8", errors="ignore") if isinstance(files[surf_out_key], bytes) else files[surf_out_key]
                            es_ry, _ = parse_qe_total_energy(content_s)
                            if es_ry is not None and "1-adsorbates" in wb.sheetnames:
                                ws1 = wb["1-adsorbates"]
                                for r in range(2, ws1.max_row + 1):
                                    if str(ws1.cell(row=r, column=2).value or "").strip().lower() in ["clean", "surface"]:
                                        ws1.cell(row=r, column=3, value=es_ry)
                                        ws1.cell(row=r, column=4, value=f"=C{r}*13.605698066")

                        if reaction.name == "HER" and "1-adsorbate" in wb.sheetnames:
                            wb["1-adsorbate"].cell(row=2, column=4, value=e_ry)
                            wb["1-adsorbate"].cell(row=2, column=5, value="='1-adsorbate'!D2*13.605698066")
                        elif "1-adsorbates" in wb.sheetnames:
                            ws1 = wb["1-adsorbates"]
                            for r in range(2, ws1.max_row + 1):
                                if str(ws1.cell(row=r, column=2).value).replace("*", "") == chosen_inter:
                                    ws1.cell(row=r, column=3, value=e_ry)
                                    ws1.cell(row=r, column=4, value=f"=C{r}*13.605698066")
                        out_buf = io.BytesIO()
                        wb.save(out_buf)
                        files[excel_path] = out_buf.getvalue()

                    files = generate_finite_displacements(files, chosen_inter)
                    out_zip = build_zip_from_dict(files)
                    st.success(f"{chosen_inter} processed and displacements generated!")
                    st.download_button(
                        label=f"⬇️ Download Project ZIP ({chosen_inter})",
                        data=out_zip,
                        file_name=f"Project_Module3_{chosen_inter}_Tab1.zip",
                        mime="application/zip",
                        use_container_width=True
                    )

with tab2:
    highlight_box(
        "<b>Tab 2 Workflow:</b> Upload ZIP containing vibrational logs in <code>4-vibration/</code>. "
        "Extracts vibrational frequencies, detects imaginary modes (&lt; 0 cm⁻¹), computes zero-point energy (ZPE), "
        "and writes each adsorbate's ZPE and mode frequencies horizontally in single rows in sheet <code>4-vibrasi</code>.",
        box_type="info"
    )
    zip_tab2 = st.file_uploader("Upload Project ZIP with Vibration Logs", type=["zip"], key="zip_tab2")
    if zip_tab2:
        files = extract_zip_to_dict(zip_tab2.getvalue())
        rxn_name = detect_reaction_type(files)
        reaction = get_reaction(rxn_name)

        is_multi = len(reaction.intermediates) > 1
        if is_multi:
            tab2_mode = st.radio(
                "Extraction Scope:",
                ["All Available Intermediates (Recommended Default)", "Single Intermediate Only"],
                index=0,
                key="tab2_scope"
            )
        else:
            tab2_mode = "Single Intermediate Only"

        if "All" in tab2_mode:
            if st.button(f"Extract Vibrations for All {reaction.name} Intermediates →", type="primary"):
                excel_info = find_excel_file(files)
                wb, excel_path = None, None
                if excel_info:
                    excel_path, excel_bytes = excel_info
                    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))

                vib_summary = []
                for inter in reaction.intermediates:
                    inter_clean = inter.replace("*", "").strip()
                    modes, zpe = parse_vibrational_frequencies(files, inter_clean)

                    if wb and "4-vibrasi" in wb.sheetnames:
                        ws4 = wb["4-vibrasi"]
                        surface_name = "Surface"
                        if "1-adsorbates" in wb.sheetnames:
                            surface_name = wb["1-adsorbates"].cell(row=2, column=1).value or surface_name
                        elif "1-adsorbate" in wb.sheetnames:
                            surface_name = wb["1-adsorbate"].cell(row=2, column=1).value or surface_name

                        if reaction.name == "HER":
                            if modes:
                                energies_ev = [0.5 * f * CM_TO_EV for f in modes if f > 0]
                                while ws4.max_row > 1:
                                    ws4.delete_rows(2)
                                for i, e_val in enumerate(energies_ev):
                                    ws4.append([surface_name, "H", round(e_val, 4), f"mode_{i+1}"])
                        else:
                            # OER: Single-row horizontal mode format
                            target_row = None
                            for r in range(2, ws4.max_row + 1):
                                if str(ws4.cell(row=r, column=2).value or "").replace("*", "").strip().upper() == inter_clean.upper():
                                    target_row = r
                                    break
                            
                            if target_row is None:
                                target_row = ws4.max_row + 1
                                ws4.cell(row=target_row, column=1, value=surface_name)
                                ws4.cell(row=target_row, column=2, value=f"{inter_clean}*")

                            if zpe is not None:
                                ws4.cell(row=target_row, column=3, value=round(zpe, 4))
                                # Leave column 4 (ts_ev) for user manual input

                                for idx, mode_val in enumerate(modes):
                                    col_idx = 5 + idx
                                    if ws4.cell(row=1, column=col_idx).value is None:
                                        ws4.cell(row=1, column=col_idx, value=f"mode_{idx+1}_cm-1")
                                    ws4.cell(row=target_row, column=col_idx, value=round(mode_val, 2))

                    if modes:
                        has_imaginary = any(m < 0 for m in modes)
                        status_label = "⚠️ Imaginary Freq Detected" if has_imaginary else "✅ Local Minimum"
                        vib_summary.append({
                            "Intermediate": inter_clean,
                            "Total ZPE (eV)": f"{zpe:.4f}" if zpe else "N/A",
                            "Modes Found": len(modes),
                            "Frequencies (cm⁻¹)": ", ".join(f"{m:.1f}" for m in modes),
                            "Status": status_label
                        })

                if wb and excel_path:
                    buf = io.BytesIO()
                    wb.save(buf)
                    files[excel_path] = buf.getvalue()

                out_zip = build_zip_from_dict(files)
                if vib_summary:
                    st.success(f"Vibrational modes and ZPE parsed for {len(vib_summary)} intermediates!")
                    st.dataframe(pd.DataFrame(vib_summary), use_container_width=True)
                else:
                    st.warning("No vibration outputs found in `4-vibration/`. Sheet `4-vibrasi` left open for manual input.")

                st.download_button(
                    label=f"⬇️ Download Project ZIP with All Vibrations Populated",
                    data=out_zip,
                    file_name=f"Project_Module3_{reaction.name}_AllVibrations.zip",
                    mime="application/zip",
                    use_container_width=True
                )
        else:
            chosen_inter_tab2 = st.selectbox("Select Intermediate:", reaction.intermediates, index=0, key="single_inter_tab2")
            if st.button("Extract Single Intermediate Vibrations →", type="primary"):
                modes, zpe = parse_vibrational_frequencies(files, chosen_inter_tab2)
                excel_info = find_excel_file(files)
                if excel_info:
                    excel_path, excel_bytes = excel_info
                    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
                    if "4-vibrasi" in wb.sheetnames and modes:
                        ws4 = wb["4-vibrasi"]
                        inter_clean = chosen_inter_tab2.replace("*", "").strip()

                        if reaction.name == "HER":
                            energies_ev = [0.5 * f * CM_TO_EV for f in modes if f > 0]
                            while ws4.max_row > 1:
                                ws4.delete_rows(2)
                            for i, e_val in enumerate(energies_ev):
                                ws4.append(["Surface", "H", round(e_val, 4), f"mode_{i+1}"])
                        else:
                            target_row = None
                            for r in range(2, ws4.max_row + 1):
                                if str(ws4.cell(row=r, column=2).value or "").replace("*", "").strip().upper() == inter_clean.upper():
                                    target_row = r
                                    break
                            if target_row is None:
                                target_row = ws4.max_row + 1
                                ws4.cell(row=target_row, column=1, value="Surface")
                                ws4.cell(row=target_row, column=2, value=f"{inter_clean}*")

                            if zpe is not None:
                                ws4.cell(row=target_row, column=3, value=round(zpe, 4))
                                for idx, mode_val in enumerate(modes):
                                    col_idx = 5 + idx
                                    if ws4.cell(row=1, column=col_idx).value is None:
                                        ws4.cell(row=1, column=col_idx, value=f"mode_{idx+1}_cm-1")
                                    ws4.cell(row=target_row, column=col_idx, value=round(mode_val, 2))

                        buf = io.BytesIO()
                        wb.save(buf)
                        files[excel_path] = buf.getvalue()

                out_zip = build_zip_from_dict(files)
                st.success(f"Vibrations parsed for {chosen_inter_tab2}!")
                st.download_button(
                    label=f"⬇️ Download Project ZIP ({chosen_inter_tab2})",
                    data=out_zip,
                    file_name=f"Project_Module3_{chosen_inter_tab2}_Tab2.zip",
                    mime="application/zip",
                    use_container_width=True
                )
