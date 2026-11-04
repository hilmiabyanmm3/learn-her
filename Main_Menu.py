import os
import sys
import streamlit as st

# Ensure root application directory is always in sys.path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
  sys.path.insert(0, ROOT_DIR)

from components.ui_components import (
    highlight_box,
    inject_global_css,
    module_header,
    render_sidebar_progress,
    style_sidebar,
)

st.set_page_config(
    page_title="HER Computational Learning Module | CMD-ITB",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()
style_sidebar()

if "progress" not in st.session_state:
  st.session_state["progress"] = 0


def show_home():
  st.markdown(
      """
        <div style="text-align: center; padding: 40px 20px 20px 20px;">
            <div style="font-size: 3.5rem; margin-bottom: 15px;">⚡</div>
            <h1 style="font-size: 2.8rem; font-weight: 800; color: #0f172a; margin-bottom: 10px;">
                Hydrogen Evolution Reaction (HER)
            </h1>
            <p style="font-size: 1.2rem; color: #64748b; max-width: 700px; margin: 0 auto 30px auto; line-height: 1.6;">
                Interactive computational simulation & educational pipeline using Quantum ESPRESSO DFT workflows.
                From pristine slab preparation to Gibbs free energy volcano assessment.
            </p>
        </div>
    """,
      unsafe_allow_html=True,
  )

  c1, c2, c3 = st.columns([1, 2, 1])
  with c2:
    if st.button(
        "🚀 Start Pipeline (Module 1) →",
        type="primary",
        use_container_width=True,
    ):
      st.switch_page("pages/1_Module_1_Setup.py")

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
        #### 📊 Thermodynamics
        * CHE model $\Delta G_{\\text{H*}}$ integration
        * Harmonic zero-point energy (ZPE) calculation
        * Publication-ready reaction profile plotting
        """)

  st.markdown(
      """
        <div style="text-align: center; margin-top: 50px; padding: 20px; border-top: 1px solid #e2e8f0; color: #94a3b8; font-size: 0.85rem;">
            Computational Materials Design Laboratory (CMD-ITB) © 2026
        </div>
    """,
      unsafe_allow_html=True,
  )


# Streamlit Multi-Page Navigation
home_page = st.Page(show_home, title="Home Portal", default=True)
mod1 = st.Page("pages/1_Module_1_Setup.py", title="Module 1: Setup")
mod2 = st.Page("pages/2_Module_2_Adsorbate.py", title="Module 2: Adsorbate")
mod3 = st.Page(
    "pages/3_Module_3_Adsorption.py", title="Module 3: Adsorption & ZPE"
)
mod4 = st.Page("pages/4_Module_4_Gibbs.py", title="Module 4: Gibbs Energy and Visualization")
mod5 = st.Page("pages/5_Module_5_Visual.py", title="Module 5: Data Comparison")
mod6 = st.Page("pages/6_Read_More.py", title="Read More: Theory & Guide")

pg = st.navigation({
    "Overview": [home_page],
    "HER Simulation Modules": [mod1, mod2, mod3, mod4, mod5],
    "Documentation": [mod6],
})

render_sidebar_progress(st.session_state["progress"])
pg.run()