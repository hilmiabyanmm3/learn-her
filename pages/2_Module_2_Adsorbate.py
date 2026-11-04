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
from utils.module_2_utils import inspect_surface_zip, build_adsorbate_system

st.set_page_config(page_title="Module 2: Adsorbate Creation | HER", page_icon="https://img.icons8.com/?size=100&id=vtLGHdmfoSt8&format=png&color=000000", layout="wide")
inject_global_css()
style_sidebar()
render_sidebar_progress(40)

module_header("02", "Adsorbate Creation & Active Site Selection", "Identify topmost catalytic sites and construct hydrogen-adsorbed slab configuration")

highlight_box(
    "<b>Input Requirements:</b> Upload your workspace ZIP containing completed surface relaxation: "
    "<code>1-surface/PW.in</code> and <code>1-surface/PW.out</code>.",
    box_type="info"
)

uploaded_zip = st.file_uploader("Upload Project ZIP (containing 1-surface/PW.in & PW.out)", type=["zip"])

if uploaded_zip:
    res, err = inspect_surface_zip(uploaded_zip.getvalue())
    if err:
        st.error(err)
    else:
        st.success("Successfully parsed Quantum ESPRESSO output from `1-surface/PW.out`!")
        
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            st.metric("Pristine Slab Energy (Ry)", f"{res['e_ry']:.6f} Ry" if res['e_ry'] else "N/A")
        with m_col2:
            st.metric("Pristine Slab Energy (eV)", f"{res['e_ev']:.4f} eV" if res['e_ev'] else "N/A")
            
        sub_section_header("Topmost Layer Active Catalytic Sites", "fa-solid fa-crosshairs")
        sites = res['sites']
        if not sites:
            st.warning("No candidate active site atoms detected within the top layer threshold.")
        else:
            df_sites = pd.DataFrame(sites)
            st.dataframe(df_sites, use_container_width=True)
            
            site_options = [f"Atom #{s['index']} - {s['element']} (z = {s['z']:.3f} Å)" for s in sites]
            chosen_site_str = st.selectbox("Select Active Site for H Adsorption (1.0 Å above):", site_options)
            chosen_idx = int(chosen_site_str.split("#")[1].split()[0])
            
            h_dist = st.slider("H Adsorption Distance (Å above selected site):", min_value=0.8, max_value=2.0, value=1.0, step=0.05)
            
            if st.button("Generate Adsorbate Structure (3-adsorption/H/PW.in) →", type="primary"):
                updated_zip = build_adsorbate_system(res['files'], chosen_idx, h_dist)
                st.success("Structure successfully generated and Excel spreadsheet updated!")
                st.download_button(
                    label="⬇️ Download Updated Project ZIP (Module 2)",
                    data=updated_zip,
                    file_name="HER_Project_Module2_Adsorbate.zip",
                    mime="application/zip"
                )
