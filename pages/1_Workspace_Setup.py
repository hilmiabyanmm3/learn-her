import os
import sys
import streamlit as st

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from components.ui_components import (
    module_header, 
    highlight_box, 
    inject_global_css, 
    style_sidebar, 
    render_sidebar_progress
)
from config import get_reaction, REACTION_REGISTRY
from core.excel_manager import generate_workspace_archive

st.set_page_config(
    page_title="Module 1: Workspace Setup | Catalysis", 
    page_icon="https://img.icons8.com/?size=100&id=vtLGHdmfoSt8&format=png&color=000000", 
    layout="wide"
)
inject_global_css()
style_sidebar()
render_sidebar_progress(20)

module_header("01", "Workspace Setup & Data Template", "Scaffold computational directory structure and initialize tracking spreadsheet")

highlight_box(
    "<b>Instructions:</b> Specify the catalyst surface formula and target electrochemical mechanism (HER, OER, or ORR). "
    "The generator will build your initial workspace directory containing isolated molecule inputs (<code>PW.in</code>) "
    "and a tailored Excel tracking workbook.", 
    box_type="info"
)

col1, col2 = st.columns(2)
with col1:
    surface_name = st.text_input("Catalyst Surface Name / Composition", value="Pt111", help="e.g., Pt111, MoS2, FeN4, LaNiO3_001")
with col2:
    current_rxn = st.session_state.get('active_reaction', 'HER')
    rxn_options = list(REACTION_REGISTRY.keys())
    default_idx = rxn_options.index(current_rxn) if current_rxn in rxn_options else 0
    selected_rxn_name = st.selectbox(
        "Electrochemical Reaction Mechanism", 
        [f"{k} ({REACTION_REGISTRY[k].full_name})" for k in rxn_options], 
        index=default_idx
    )
    rxn_key = selected_rxn_name.split()[0]
    st.session_state['active_reaction'] = rxn_key

reaction = get_reaction(st.session_state['active_reaction'])

st.markdown("<br>", unsafe_allow_html=True)
if st.button("Generate Workspace Archive →", type="primary"):
    if not surface_name.strip():
        st.error("Please enter a valid surface name.")
    else:
        with st.spinner(f"Scaffolding {reaction.name} directory structure and Excel workbook..."):
            zip_bytes = generate_workspace_archive(surface_name, reaction, ROOT_DIR)
            st.success(f"Workspace successfully prepared for surface: **{surface_name}** ({reaction.name})!")
            
            st.download_button(
                label=f"⬇️ Download {surface_name}_Module1_{reaction.name}_Setup.zip",
                data=zip_bytes,
                file_name=f"{surface_name}_Module1_{reaction.name}_Setup.zip",
                mime="application/zip"
            )
