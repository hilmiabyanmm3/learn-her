import streamlit as st
from components.ui_components import (
    module_header, 
    sub_section_header, 
    highlight_box, 
    inject_global_css, 
    style_sidebar, 
    render_sidebar_progress
)
from utils.module_1_utils import generate_module_1_workspace

st.set_page_config(page_title="Module 1: Workspace Setup | HER", page_icon="https://img.icons8.com/?size=100&id=vtLGHdmfoSt8&format=png&color=000000", layout="wide")
inject_global_css()
style_sidebar()
render_sidebar_progress(20)

module_header("01", "Workspace Setup & Data Template", "Scaffold computational directory structure and initialize tracking spreadsheet")

highlight_box(
    "<b>Instructions:</b> Specify the catalyst surface formula and target electrochemical mechanism. "
    "The generator will build your initial workspace directory containing isolated molecule inputs (<code>PW.in</code>) "
    "and a tailored Excel tracking workbook.", 
    box_type="info"
)

col1, col2 = st.columns(2)
with col1:
    surface_name = st.text_input("Catalyst Surface Name / Composition", value="Pt111", help="e.g., Pt111, MoS2, FeN4, NiO")
with col2:
    reaction = st.selectbox("Electrochemical Reaction Mechanism", ["HER (Hydrogen Evolution Reaction)"], index=0)

st.markdown("<br>", unsafe_allow_html=True)
if st.button("Generate Workspace Archive →", type="primary"):
    if not surface_name.strip():
        st.error("Please enter a valid surface name.")
    else:
        with st.spinner("Scaffolding directory structure and Excel workbook..."):
            zip_bytes = generate_module_1_workspace(surface_name)
            st.success(f"Workspace successfully prepared for surface: **{surface_name}**!")
            
            st.download_button(
                label=f"⬇️ Download {surface_name}_Module1_Setup.zip",
                data=zip_bytes,
                file_name=f"{surface_name}_Module1_Setup.zip",
                mime="application/zip"
            )
