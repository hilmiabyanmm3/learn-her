import pandas as pd
import streamlit as st
from components.ui_components import (
    highlight_box,
    inject_global_css,
    module_header,
    render_sidebar_progress,
    style_sidebar,
    sub_section_header,
)
from utils.module_3_utils import process_tab1_energies, process_tab2_vibrations

# 1. Page Configuration & Styling
st.set_page_config(
    page_title="Module 3: Adsorption & Vibrations | HER", layout="wide"
)
inject_global_css()
style_sidebar()
render_sidebar_progress(60)

# 2. Header
module_header(
    "03",
    "Adsorption Energy & Vibrational Logistics",
    "Extract electronic energies, generate finite-displacement inputs, and"
    " evaluate zero-point vibrational energy",
)

# 3. Workflow Tabs
tab1, tab2 = st.tabs([
    "Tab 1: Adsorption Energy & Vibration Setup",
    "Tab 2: Vibrational Modes & ZPE Extraction",
])

# ----------------------------------------------------------------------
# TAB 1: Adsorption Energy & Vibration Input Generation
# ----------------------------------------------------------------------
with tab1:
  highlight_box(
      "<b>Tab 1 Workflow:</b> Upload your project ZIP containing completed DFT"
      " calculations: <code>3-adsorption/H/PW.out</code> and"
      " <code>2-isolated-gas/H2/PW.out</code>.<br>This extracts total energies"
      " (converting Ry to eV), updates <code>3-ads-energy</code> and"
      " <code>2-isolated-mol</code> in the tracking workbook, and builds the 6"
      " finite-displacement calculation inputs inside"
      " <code>4-vibration/H/</code>.",
      box_type="info",
  )

  zip_tab1 = st.file_uploader(
      "Upload Project ZIP for Tab 1 (containing completed PW.out files)",
      type=["zip"],
      key="zip_tab1",
  )

  if zip_tab1:
    if st.button("Process Energies & Create Displacements →", type="primary"):
      with st.spinner("Parsing DFT outputs and generating displacement files..."):
        out_zip, summary, err = process_tab1_energies(zip_tab1.getvalue())

      if err:
        st.error(err)
      else:
        st.success(
            "Energies successfully recorded in Excel, and finite-displacement"
            " inputs created in `4-vibration/H/`!"
        )

        c1, c2, c3 = st.columns(3)
        c1.metric(
            "E(H*) [eV]",
            f"{summary['e_ads_ev']:.4f} eV" if summary["e_ads_ev"] else "N/A",
        )
        c2.metric(
            "E(H₂) [eV]",
            f"{summary['e_h2_ev']:.4f} eV" if summary["e_h2_ev"] else "N/A",
        )
        c3.metric(
            "E(H₂O) [eV]",
            f"{summary['e_h2o_ev']:.4f} eV" if summary["e_h2o_ev"] else "N/A",
        )

        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            label="⬇️ Download Project ZIP with Vibration Inputs",
            data=out_zip,
            file_name="HER_Project_Module3_Tab1.zip",
            mime="application/zip",
            use_container_width=True,
        )

# ----------------------------------------------------------------------
# TAB 2: Vibrational Modes & ZPE Extraction
# ----------------------------------------------------------------------
with tab2:
  highlight_box(
      "<b>Tab 2 Workflow:</b> Upload your project ZIP after running the"
      " displacement calculations.<br>• If log/output files (<code>LOG_*</code>"
      " or <code>PWINPUT_atm*.out</code>) are found in"
      " <code>4-vibration/H/</code>, frequencies and ZPE will be extracted"
      " automatically.<br>• If no log files are present, sheet"
      " <code>4-vibrasi</code> will be formatted with empty cells for manual"
      " entry.",
      box_type="info",
  )

  zip_tab2 = st.file_uploader(
      "Upload Project ZIP for Tab 2 (containing 4-vibration/H/ logs or updated"
      " Excel)",
      type=["zip"],
      key="zip_tab2",
  )

  if zip_tab2:
    if st.button("Process Frequencies & Sheet Setup →", type="primary"):
      with st.spinner("Inspecting vibrational calculation outputs..."):
        out_zip, freqs, zpe, err, logs_found = process_tab2_vibrations(
            zip_tab2.getvalue()
        )

      if err:
        st.error(err)
      elif logs_found:
        st.success(
            "Vibrational frequencies parsed and logged into sheet `4-vibrasi`!"
        )

        col_z1, col_z2 = st.columns(2)
        col_z1.metric("Total ZPE(H*)", f"{zpe:.4f} eV")
        col_z2.metric("Dominant Stretch Mode", f"{max(freqs):.1f} cm⁻¹")

        sub_section_header("Harmonic Normal Modes", "fa-solid fa-wave-square")
        df_freqs = pd.DataFrame({
            "Mode": [f"mode_{i+1}" for i in range(len(freqs))],
            "Frequency (cm⁻¹)": [f"{f:.1f}" for f in freqs],
            "Harmonic ZPE (eV)": [f"{0.5 * f / 8065.544:.4f}" for f in freqs],
        })
        st.dataframe(df_freqs, use_container_width=True)

        st.download_button(
            label="⬇️ Download Project ZIP with Populated Vibrations",
            data=out_zip,
            file_name="HER_Project_Module3_Tab2.zip",
            mime="application/zip",
            use_container_width=True,
        )
      else:
        st.warning(
            "**No vibrational LOG/output files detected in"
            " `4-vibration/H/`.**\n\nSheet `4-vibrasi` in your workbook has"
            " been prepared with empty cells in the `energy_ev` column for each"
            " vibrational mode (`mode_1`, `mode_2`, `mode_3`).\n\nDownload the"
            " ZIP below, open your Excel spreadsheet, enter your calculated"
            " vibrational energies (in eV) into column `energy_ev`, and proceed"
            " directly to **Module 4**."
        )

        st.download_button(
            label=(
                "⬇️ Download Project ZIP (Empty Vibrasi Sheet Ready for Manual"
                " Entry)"
            ),
            data=out_zip,
            file_name="HER_Project_Module3_Manual_Entry.zip",
            mime="application/zip",
            use_container_width=True,
        )