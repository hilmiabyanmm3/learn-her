import os
import sys
import streamlit as st

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from components.ui_components import inject_global_css, render_sidebar_progress

st.set_page_config(
    page_title="Catalysis Learning Module | CMD-ITB",
    page_icon="https://img.icons8.com/?size=100&id=vtLGHdmfoSt8&format=png&color=000000",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_global_css()

if 'active_reaction' not in st.session_state:
    st.session_state['active_reaction'] = "HER"
if 'progress' not in st.session_state:
    st.session_state['progress'] = 0

def show_home():
    st.markdown("""
        <div style="text-align: center; padding: 35px 20px 15px 20px;">
            <div style="font-size: 3.5rem; margin-bottom: 12px;">⚡</div>
            <h1 style="font-size: 2.7rem; font-weight: 800; color: #1a1c1e; margin-bottom: 10px;">
                Computational Electrocatalysis Learning Platform
            </h1>
            <p style="font-size: 1.15rem; color: #6c757d; max-width: 720px; margin: 0 auto 25px auto; line-height: 1.6;">
                Modular Density Functional Theory (DFT) simulation suites for Hydrogen Evolution Reaction (HER),
                Oxygen Evolution Reaction (OER), and Oxygen Reduction Reaction (ORR) using Quantum ESPRESSO.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Repository Links
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("""
            <div style="display: flex; justify-content: center; align-items: center; gap: 15px; margin-bottom: 25px;">
                <a href="https://github.com/hilmiabyanmm3/learn-her" target="_blank" style="text-decoration: none;">
                    <button style="display: inline-flex; align-items: center; gap: 8px; background-color: #24292f; color: white; border: 1px solid #24292f; padding: 0.6rem 1.4rem; border-radius: 8px; font-weight: 600; cursor: pointer;">
                        <i class="fa-brands fa-github"></i> View on GitHub
                    </button>
                </a>
                <a href="https://github.com/hilmiabyanmm3/learn-her" target="_blank" style="text-decoration: none;">
                    <button style="display: inline-flex; align-items: center; gap: 8px; background-color: #fff; color: #0f172a; border: 1px solid #cbd5e1; padding: 0.6rem 1.4rem; border-radius: 8px; font-weight: 600; cursor: pointer;">
                        <i class="fa-solid fa-star" style="color: #eab308;"></i> Star us on GitHub
                    </button>
                </a>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    
    # Active Mechanism Selector
    st.subheader("🎯 Select Active Electrochemical Mechanism")
    rxn_choice = st.selectbox(
        "Active Computational Pipeline:",
        ["HER (Hydrogen Evolution Reaction — 2e⁻ Reduction)",
         "OER (Oxygen Evolution Reaction — 4e⁻ Oxidation)",
         "ORR (Oxygen Reduction Reaction — 4e⁻ Reduction)"],
        index=0 if st.session_state['active_reaction'] == "HER" else (1 if st.session_state['active_reaction'] == "OER" else 2)
    )
    if "HER" in rxn_choice:
        st.session_state['active_reaction'] = "HER"
    elif "OER" in rxn_choice:
        st.session_state['active_reaction'] = "OER"
    else:
        st.session_state['active_reaction'] = "ORR"
        
    st.info(f"Active Mechanism: **{st.session_state['active_reaction']}**. Proceed through Modules 1 to 5 in the sidebar.")

home_page = st.Page(show_home, title="Home Portal", default=True)
mod1 = st.Page("pages/1_Workspace_Setup.py", title="Module 1: Workspace Setup")
mod2 = st.Page("pages/2_Site_and_Adsorption.py", title="Module 2: Adsorbate Creation")
mod3 = st.Page("pages/3_Adsorption_and_ZPE.py", title="Module 3: Adsorption & Vibrations")
mod4 = st.Page("pages/4_Gibbs_and_Potential.py", title="Module 4: Delta Gibbs & Potential")
mod5 = st.Page("pages/5_Multi_Catalyst_Screening.py", title="Module 5: Catalyst Comparation")
mod6 = st.Page("pages/6_Documentation.py", title="Read More: Theory & Guide")

pg = st.navigation({
    "Overview": [home_page],
    "Simulation Modules": [mod1, mod2, mod3, mod4, mod5],
    "Documentation": [mod6]
})

render_sidebar_progress(st.session_state['progress'])
pg.run()
