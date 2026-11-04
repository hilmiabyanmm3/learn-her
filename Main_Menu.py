import os
import sys
import streamlit as st

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from components.ui_components import (
    module_header, 
    highlight_box, 
    inject_global_css, 
    style_sidebar, 
    render_sidebar_progress
)

st.set_page_config(
    page_title="HER Computational Learning Module | CMD-ITB",
    page_icon="https://img.icons8.com/?size=100&id=vtLGHdmfoSt8&format=png&color=000000",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_global_css()
style_sidebar()

if 'progress' not in st.session_state:
    st.session_state['progress'] = 0

def show_home():
    st.markdown("""
        <div style="text-align: center; padding: 40px 20px 20px 20px;">
            <div style="font-size: 3.5rem; margin-bottom: 15px;">⚡</div>
            <h1 style="font-size: 2.8rem; font-weight: 800; color: #0f172a; margin-bottom: 10px;">
                Hydrogen Evolution Reaction (HER)
            </h1>
            <p style="font-size: 1.2rem; color: #64748b; max-width: 700px; margin: 0 auto 25px auto; line-height: 1.6;">
                Interactive computational simulation & educational pipeline using Quantum ESPRESSO DFT workflows.
                From pristine slab preparation to single-catalyst Gibbs free energy evaluation and multi-catalyst comparative screening.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # GitHub Action Buttons
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("""
            <div style="display: flex; justify-content: center; align-items: center; gap: 15px; margin-bottom: 25px;">
                <a href="https://github.com/hilmiabyanmm3/learn-her" target="_blank" style="text-decoration: none;">
                    <button style="
                        display: inline-flex;
                        align-items: center;
                        gap: 8px;
                        background-color: #24292f;
                        color: white;
                        border: 1px solid #24292f;
                        padding: 0.6rem 1.4rem;
                        border-radius: 8px;
                        font-weight: 600;
                        font-size: 1rem;
                        cursor: pointer;
                        transition: all 0.2s ease;">
                        <i class="fa-brands fa-github" style="font-size: 1.2rem;"></i> View on GitHub
                    </button>
                </a>
                <a href="https://github.com/hilmiabyanmm3/learn-her" target="_blank" style="text-decoration: none;">
                    <button style="
                        display: inline-flex;
                        align-items: center;
                        gap: 8px;
                        background-color: #fff;
                        color: #0f172a;
                        border: 1px solid #cbd5e1;
                        padding: 0.6rem 1.4rem;
                        border-radius: 8px;
                        font-weight: 600;
                        font-size: 1rem;
                        cursor: pointer;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                        transition: all 0.2s ease;">
                        <i class="fa-solid fa-star" style="color: #eab308; font-size: 1.1rem;"></i> Star us on GitHub
                    </button>
                </a>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("""
        #### 📁 Directory & Data
        * Automated directory structure setup
        * Multi-tab Excel data sheet management
        * Quantum ESPRESSO `PW.in` and `PW.out` standardization
        """)
    with col_b:
        st.markdown("""
        #### ⚛️ Active Site & DFT
        * Surface topmost layer active atom detection
        * 1.0 Å H-adsorption slab construction
        * Finite-displacement vibration setup
        """)
    with col_c:
        st.markdown("""
        #### 📊 Thermodynamics & Comparation
        * CHE model $\Delta G_{\\text{H*}}$ integration & single-profile visualization
        * Limiting Potential ($U_L$) Volcano curve integration
        * Multi-catalyst comparative screening & Sabatier volcano positioning
        """)

    st.markdown("""
        <div style="text-align: center; margin-top: 50px; padding: 20px; border-top: 1px solid #e2e8f0; color: #94a3b8; font-size: 0.85rem;">
            Computational Materials Design Laboratory (CMD-ITB) © 2026
        </div>
    """, unsafe_allow_html=True)

home_page = st.Page(show_home, title="Home Portal", default=True)
mod1 = st.Page("pages/1_Module_1_Setup.py", title="Module 1: Setup")
mod2 = st.Page("pages/2_Module_2_Adsorbate.py", title="Module 2: Adsorbate")
mod3 = st.Page("pages/3_Module_3_Adsorption.py", title="Module 3: Adsorption & ZPE")
mod4 = st.Page("pages/4_Module_4_Gibbs.py", title="Module 4: Delta Gibbs & Visualization")
mod5 = st.Page("pages/5_Module_5_Visual.py", title="Module 5: Comparation")
mod6 = st.Page("pages/6_Read_More.py", title="Read More: Theory & Guide")

pg = st.navigation({
    "Overview": [home_page],
    "HER Simulation Modules": [mod1, mod2, mod3, mod4, mod5],
    "Documentation": [mod6]
})

render_sidebar_progress(st.session_state['progress'])
pg.run()
