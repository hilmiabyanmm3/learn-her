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
from core.qe_parser import parse_qe_total_energy, RY_TO_EV
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


def sync_and_validate_isolated_gas(files: dict, wb: openpyxl.Workbook | None, reaction) -> list[str]:
    """Extracts 2-isolated-gas/<MOL>/PW.out energies into '2-isolated-mol' without auto-filling defaults.
    Returns a list of missing gas references that have neither PW.out data nor existing Excel entries.
    """
    gas_parsed_ry = {}
    gas_parsed_ev = {}
    for mol in ["H2", "H2O", "O2"]:
        key = next((k for k in files if k.endswith(f"2-isolated-gas/{mol}/PW.out")), None)
        if key:
            content = files[key].decode("utf-8", errors="ignore") if isinstance(files[key], bytes) else files[key]
            e_ry, e_ev = parse_qe_total_energy(content)
            if e_ry is not None:
                gas_parsed_ry[mol] = e_ry
                gas_parsed_ev[mol] = e_ev

    existing_in_excel = set()
    if wb is not None and "2-isolated-mol" in wb.sheetnames:
        ws2 = wb["2-isolated-mol"]
        if reaction.name == "HER":
            row_map = {}
            for r in range(2, ws2.max_row + 1):
                m_val = str(ws2.cell(row=r, column=1).value or "").strip().upper()
                if m_val == "H2" or "H2_GAS" in m_val:
                    row_map["H2"] = r
                elif m_val == "H2O" or "H2O_GAS" in m_val:
                    row_map["H2O"] = r

            for mol, default_zpe, default_ts in [("H2", 0.2720, 0.4040), ("H2O", 0.5600, 0.6700)]:
                r_idx = row_map.get(mol)
                if r_idx is None:
                    r_idx = ws2.max_row + 1
                    ws2.cell(row=r_idx, column=1, value=mol)
                    ws2.cell(row=r_idx, column=3, value=default_zpe)
                    ws2.cell(row=r_idx, column=4, value=default_ts)
                if mol in gas_parsed_ev:
                    ws2.cell(row=r_idx, column=2, value=round(gas_parsed_ev[mol], 6))
                if isinstance(ws2.cell(row=r_idx, column=2).value, (int, float)):
                    existing_in_excel.add(mol)
        else:
            for r in range(2, ws2.max_row + 1):
                m_val = str(ws2.cell(row=r, column=1).value or "").strip().upper()
                mol_key = None
                if "H2O_GAS" in m_val or m_val == "H2O":
                    mol_key = "H2O"
                elif "H2_GAS" in m_val or m_val == "H2":
                    mol_key = "H2"
                elif "O2_GAS" in m_val or m_val == "O2":
                    mol_key = "O2"

                if mol_key:
                    if mol_key in gas_parsed_ry:
                        ws2.cell(row=r, column=2, value=round(gas_parsed_ry[mol_key], 6))
                        ws2.cell(row=r, column=3, value=f"=B{r}*13.605698066")
                    val_ry = ws2.cell(row=r, column=2).value
                    val_ev = ws2.cell(row=r, column=3).value
                    if isinstance(val_ry, (int, float)) or isinstance(val_ev, (int, float)):
                        existing_in_excel.add(mol_key)

    required_gases = getattr(reaction, "gas_references", ["H2", "H2O"])
    missing = [
        f"{mol} (2-isolated-gas/{mol}/PW.out)"
        for mol in required_gases
        if mol not in gas_parsed_ry and mol not in existing_in_excel
    ]
    return missing


def build_adsorbate_energy_dataframe(
    files: dict,
    reaction,
    displaced_species: set[str] | None = None,
    target_intermediates: list[str] | None = None
) -> pd.DataFrame:
    """Parses clean slab, isolated gas references, and adsorbate PW.out/Excel energies to build a summary table."""
    excel_info = find_excel_file(dict(files))
    wb = None
    if excel_info:
        try:
            wb = openpyxl.load_workbook(io.BytesIO(excel_info[1]), data_only=False)
        except Exception:
            wb = None

    # 1. Clean slab energy
    e_clean_ry, e_clean_ev = None, None
    surf_out_key = next((k for k in files if k.endswith("1-surface/PW.out")), None)
    if surf_out_key:
        c_surf = files[surf_out_key].decode("utf-8", errors="ignore") if isinstance(files[surf_out_key], bytes) else files[surf_out_key]
        e_clean_ry, e_clean_ev = parse_qe_total_energy(c_surf)

    if e_clean_ev is None and wb is not None:
        if "1-adsorbates" in wb.sheetnames:
            ws1 = wb["1-adsorbates"]
            for r in range(2, ws1.max_row + 1):
                if str(ws1.cell(row=r, column=2).value or "").strip().lower() in ["clean", "surface", "*"]:
                    v_ry = ws1.cell(row=r, column=3).value
                    v_ev = ws1.cell(row=r, column=4).value
                    if isinstance(v_ry, (int, float)):
                        e_clean_ry = float(v_ry)
                        e_clean_ev = e_clean_ry * RY_TO_EV
                    elif isinstance(v_ev, (int, float)):
                        e_clean_ev = float(v_ev)
                        e_clean_ry = e_clean_ev / RY_TO_EV
                    break
        elif "1-adsorbate" in wb.sheetnames:
            ws1 = wb["1-adsorbate"]
            v_ry = ws1.cell(row=2, column=2).value
            v_ev = ws1.cell(row=2, column=3).value
            if isinstance(v_ry, (int, float)):
                e_clean_ry = float(v_ry)
                e_clean_ev = e_clean_ry * RY_TO_EV
            elif isinstance(v_ev, (int, float)):
                e_clean_ev = float(v_ev)
                e_clean_ry = e_clean_ev / RY_TO_EV

    # 2. Isolated gas energies (in eV)
    gas_ev = {}
    for mol in ["H2", "H2O", "O2"]:
        g_key = next((k for k in files if k.endswith(f"2-isolated-gas/{mol}/PW.out")), None)
        if g_key:
            c_g = files[g_key].decode("utf-8", errors="ignore") if isinstance(files[g_key], bytes) else files[g_key]
            _, g_e = parse_qe_total_energy(c_g)
            if g_e is not None:
                gas_ev[mol] = g_e

    if wb is not None and "2-isolated-mol" in wb.sheetnames:
        ws2 = wb["2-isolated-mol"]
        for r in range(2, ws2.max_row + 1):
            m_val = str(ws2.cell(row=r, column=1).value or "").strip().upper()
            mol_k = None
            if "H2O" in m_val:
                mol_k = "H2O"
            elif "H2" in m_val:
                mol_k = "H2"
            elif "O2" in m_val:
                mol_k = "O2"
            if mol_k and mol_k not in gas_ev:
                if reaction.name == "HER":
                    v = ws2.cell(row=r, column=2).value
                    if isinstance(v, (int, float)):
                        gas_ev[mol_k] = float(v)
                else:
                    v_ry = ws2.cell(row=r, column=2).value
                    v_ev = ws2.cell(row=r, column=3).value
                    if isinstance(v_ev, (int, float)):
                        gas_ev[mol_k] = float(v_ev)
                    elif isinstance(v_ry, (int, float)):
                        gas_ev[mol_k] = float(v_ry) * RY_TO_EV

    # 3. Adsorbate SCF energies and ΔE_ads per intermediate
    inters = target_intermediates if target_intermediates is not None else reaction.intermediates
    rows = []
    for inter in inters:
        inter_clean = inter.replace("*", "").strip()
        inter_upper = inter_clean.upper()
        e_ads_ry, e_ads_ev = None, None
        source_lbl = "Missing PW.out"

        ads_key = next((k for k in files if k.endswith(f"3-adsorption/{inter_clean}/PW.out")), None)
        if ads_key:
            c_ads = files[ads_key].decode("utf-8", errors="ignore") if isinstance(files[ads_key], bytes) else files[ads_key]
            e_ads_ry, e_ads_ev = parse_qe_total_energy(c_ads)
            if e_ads_ry is not None:
                source_lbl = "Parsed from PW.out"

        if e_ads_ev is None and wb is not None:
            if reaction.name == "HER" and "1-adsorbate" in wb.sheetnames:
                ws1 = wb["1-adsorbate"]
                v_ry = ws1.cell(row=2, column=4).value
                v_ev = ws1.cell(row=2, column=5).value
                if isinstance(v_ry, (int, float)):
                    e_ads_ry = float(v_ry)
                    e_ads_ev = e_ads_ry * RY_TO_EV
                    source_lbl = "Loaded from Excel"
                elif isinstance(v_ev, (int, float)):
                    e_ads_ev = float(v_ev)
                    e_ads_ry = e_ads_ev / RY_TO_EV
                    source_lbl = "Loaded from Excel"
            elif "1-adsorbates" in wb.sheetnames:
                ws1 = wb["1-adsorbates"]
                for r in range(2, ws1.max_row + 1):
                    if str(ws1.cell(row=r, column=2).value or "").replace("*", "").strip().upper() == inter_upper:
                        v_ry = ws1.cell(row=r, column=3).value
                        v_ev = ws1.cell(row=r, column=4).value
                        if isinstance(v_ry, (int, float)):
                            e_ads_ry = float(v_ry)
                            e_ads_ev = e_ads_ry * RY_TO_EV
                            source_lbl = "Loaded from Excel"
                        elif isinstance(v_ev, (int, float)):
                            e_ads_ev = float(v_ev)
                            e_ads_ry = e_ads_ev / RY_TO_EV
                            source_lbl = "Loaded from Excel"
                        break

        # Calculate ΔE_ads (eV) if clean slab and required isolated gas energies are available
        de_ads = None
        if e_ads_ev is not None and e_clean_ev is not None:
            if reaction.name == "HER" and inter_upper == "H" and "H2" in gas_ev:
                de_ads = e_ads_ev - e_clean_ev - 0.5 * gas_ev["H2"]
            elif inter_upper == "H2O" and "H2O" in gas_ev:
                de_ads = e_ads_ev - e_clean_ev - gas_ev["H2O"]
            elif inter_upper == "OH" and "H2O" in gas_ev and "H2" in gas_ev:
                de_ads = e_ads_ev - e_clean_ev - (gas_ev["H2O"] - 0.5 * gas_ev["H2"])
            elif inter_upper == "O" and "O2" in gas_ev:
                de_ads = e_ads_ev - e_clean_ev - 0.5 * gas_ev["O2"]
            elif inter_upper == "OOH" and "H2O" in gas_ev and "H2" in gas_ev:
                de_ads = e_ads_ev - e_clean_ev - (2.0 * gas_ev["H2O"] - 1.5 * gas_ev["H2"])
            elif inter_upper == "O2" and "O2" in gas_ev:
                de_ads = e_ads_ev - e_clean_ev - gas_ev["O2"]

        if displaced_species and inter_upper in displaced_species:
            status_str = "✅ Displacements Generated"
        else:
            status_str = source_lbl

        rows.append({
            "Intermediate": f"{inter_clean}*",
            "Slab + Ads E_SCF (Ry)": f"{e_ads_ry:.6f}" if e_ads_ry is not None else "—",
            "Slab + Ads E_SCF (eV)": f"{e_ads_ev:.4f}" if e_ads_ev is not None else "—",
            "Clean Slab E_SCF (eV)": f"{e_clean_ev:.4f}" if e_clean_ev is not None else "—",
            "Adsorption Energy ΔE_ads (eV)": f"{de_ads:+.4f}" if de_ads is not None else "Pending Gas/Slab",
            "Status": status_str
        })

    return pd.DataFrame(rows)


module_header("03", "Adsorption Energy & Vibrational Logistics", "Extract electronic energies, create finite displacements, and evaluate vibrational zero-point energy")

tab1, tab2 = st.tabs(["Tab 1: Adsorption Energy & Vibration Setup", "Tab 2: Vibrational Modes & ZPE Extraction"])

with tab1:
    highlight_box(
        "<b>Tab 1 Workflow:</b> Upload ZIP with completed calculations: <code>3-adsorption/&lt;species&gt;/PW.out</code> and "
        "all required isolated gas references in <code>2-isolated-gas/</code> (including <code>O2/PW.out</code> for OER). "
        "Extracts energies into Excel without auto-filling missing values, displays the adsorbate energy table, and creates finite displacement inputs in <code>4-vibration/&lt;species&gt;/</code>.",
        box_type="info"
    )
    zip_tab1 = st.file_uploader("Upload Project ZIP for Tab 1", type=["zip"], key="zip_tab1")
    if zip_tab1:
        files = extract_zip_to_dict(zip_tab1.getvalue())
        rxn_name = detect_reaction_type(files)
        reaction = get_reaction(rxn_name)
        st.info(f"Detected Mechanism: **{reaction.name}** ({reaction.full_name})")

        # Immediately display parsed adsorbate energy data table when new data is uploaded
        sub_section_header("Detected Adsorbate Energy Data", "fa-solid fa-table")
        df_preview = build_adsorbate_energy_dataframe(files, reaction)
        st.dataframe(df_preview, use_container_width=True)

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

                # 1. Extract and validate required isolated gas references (H2, H2O, and O2 for OER)
                missing_gas = sync_and_validate_isolated_gas(files, wb, reaction)
                if missing_gas:
                    st.error(
                        f"❌ Missing isolated gas data for: **{', '.join(missing_gas)}**. "
                        "Please run the isolated gas calculations in `2-isolated-gas/` or fill the `2-isolated-mol` sheet in Excel before continuing."
                    )
                    st.stop()

                # 2. Parse clean surface if present in the uploaded archive
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

                # 3. Parse all intermediate adsorption energies and build displacements
                displaced_set = set()
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
                            displaced_set.add(inter_clean.upper())

                if wb and excel_path:
                    buf = io.BytesIO()
                    wb.save(buf)
                    files[excel_path] = buf.getvalue()

                out_zip = build_zip_from_dict(files)
                if displaced_set:
                    st.success(f"Successfully processed {len(displaced_set)} intermediates, updated Excel, and generated displacement inputs in `4-vibration/`!")
                    df_final = build_adsorbate_energy_dataframe(files, reaction, displaced_species=displaced_set)
                    st.dataframe(df_final, use_container_width=True)
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
                excel_info = find_excel_file(files)
                wb, excel_path = None, None
                if excel_info:
                    excel_path, excel_bytes = excel_info
                    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))

                missing_gas = sync_and_validate_isolated_gas(files, wb, reaction)
                if missing_gas:
                    st.error(
                        f"❌ Missing isolated gas data for: **{', '.join(missing_gas)}**. "
                        "Please run the isolated gas calculations in `2-isolated-gas/` or fill the `2-isolated-mol` sheet in Excel before continuing."
                    )
                    st.stop()

                ads_out_key = next((k for k in files if k.endswith(f"3-adsorption/{chosen_inter}/PW.out")), None)
                if not ads_out_key:
                    st.error(f"Missing `3-adsorption/{chosen_inter}/PW.out` in the uploaded zip.")
                else:
                    content = files[ads_out_key].decode("utf-8", errors="ignore") if isinstance(files[ads_out_key], bytes) else files[ads_out_key]
                    e_ry, e_ev = parse_qe_total_energy(content)
                    if wb and e_ry is not None:
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
                    df_single = build_adsorbate_energy_dataframe(
                        files,
                        reaction,
                        displaced_species={chosen_inter.replace("*", "").strip().upper()},
                        target_intermediates=[chosen_inter]
                    )
                    st.dataframe(df_single, use_container_width=True)
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
                st.dataframe(
                    pd.DataFrame([{
                        "Intermediate": f"{chosen_inter_tab2.replace('*', '').strip()}*",
                        "Total ZPE (eV)": f"{zpe:.4f}" if zpe is not None else "N/A",
                        "Modes Found": len(modes),
                        "Frequencies (cm⁻¹)": ", ".join(f"{m:.1f}" for m in modes) if modes else "None",
                        "Status": "⚠️ Imaginary Freq Detected" if any(m < 0 for m in modes) else ("✅ Local Minimum" if modes else "No Logs Found")
                    }]),
                    use_container_width=True
                )
                st.download_button(
                    label=f"⬇️ Download Project ZIP ({chosen_inter_tab2})",
                    data=out_zip,
                    file_name=f"Project_Module3_{chosen_inter_tab2}_Tab2.zip",
                    mime="application/zip",
                    use_container_width=True
                )
