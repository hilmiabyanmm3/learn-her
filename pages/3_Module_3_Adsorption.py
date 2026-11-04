import streamlit as st
import pandas as pd
from components.ui_components import (
    module_header, 
    sub_section_header, 
    highlight_box, 
    inject_global_css, 
    style_sidebar, 
    render_sidebar_progress
)
from utils.module_3_utils import process_tab1_energies, process_tab2_vibrations

st.set_page_config(page_title="Module 3: Adsorption & Vibrations | HER", page_icon="https://img.icons8.com/?size=100&id=vtLGHdmfoSt8&format=png&color=000000", layout="wide")
inject_global_css()
style_sidebar()
render_sidebar_progress(60)

module_header("03", "Adsorption Energy & Vibrational Logistics", "Extract electronic energies, create finite displacements, and evaluate vibrational zero-point energy")

tab1, tab2 = st.tabs(["Tab 1: Adsorption Energy & Vibration Setup", "Tab 2: Vibrational Modes & ZPE Extraction"])

with tab1:
    highlight_box(
        "<b>Tab 1 Workflow:</b> Upload ZIP with completed calculations: <code>3-adsorption/H/PW.out</code> and "
        "<code>2-isolated-gas/H2/PW.out</code>. This writes total energies into Excel and creates finite displacement scripts in <code>4-vibration/H/</code>.",
        box_type="info"
    )
    zip_tab1 = st.file_uploader("Upload Project ZIP for Tab 1", type=["zip"], key="zip_tab1")
    if zip_tab1:
        if st.button("Process Energies & Create Displacements →", type="primary"):
            out_zip, summary, err = process_tab1_energies(zip_tab1.getvalue())
            if err:
                st.error(err)
            else:
                st.success("Energies logged to Excel and finite-displacement inputs generated in `4-vibration/H/`!")
                c1, c2 = st.columns(2)
                c1.metric("E(H*) eV", f"{summary['e_ads_ev']:.4f} eV" if summary['e_ads_ev'] else "N/A")
                c2.metric("E(H2) eV", f"{summary['e_h2_ev']:.4f} eV" if summary['e_h2_ev'] else "N/A")
                
                st.download_button(
                    label="⬇️ Download Project ZIP with Vibration Inputs",
                    data=out_zip,
                    file_name="HER_Project_Module3_Tab1.zip",
                    mime="application/zip"
                )

with tab2:
    highlight_box(
        "<b>Tab 2 Workflow:</b> Upload ZIP containing vibrational logs or frequency calculations in <code>4-vibration/H/</code>. "
        "Harmonic vibrational frequencies and zero-point energies will be appended to sheet <code>4-vibrasi</code>.",
        box_type="info"
    )
    zip_tab2 = st.file_uploader("Upload Project ZIP with Vibration Logs", type=["zip"], key="zip_tab2")
    if zip_tab2:
        if st.button("Extract Frequencies & Compute ZPE →", type="primary"):
            out_zip, freqs, zpe, err = process_tab2_vibrations(zip_tab2.getvalue())
            if err:
                st.error(err)
            else:
                st.success("Vibrational frequencies parsed and written to `4-vibrasi` sheet!")
                col_z1, col_z2 = st.columns(2)
                col_z1.metric("Total ZPE(H*)", f"{zpe:.4f} eV")
                col_z2.metric("Dominant Stretch Mode", f"{max(freqs):.1f} cm⁻¹")
                
                df_freqs = pd.DataFrame({
                    "Mode": [f"mode_{i+1}" for i in range(len(freqs))],
                    "Frequency (cm⁻¹)": [f"{f:.1f}" for f in freqs],
                    "Harmonic ZPE (eV)": [f"{0.5 * f / 8065.544:.4f}" for f in freqs]
                })
                st.dataframe(df_freqs, use_container_width=True)
                
                st.download_button(
                    label="⬇️ Download Project ZIP with Populated Vibrations",
                    data=out_zip,
                    file_name="HER_Project_Module3_Tab2.zip",
                    mime="application/zip"
                )
