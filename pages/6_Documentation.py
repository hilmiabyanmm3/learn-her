import os
import sys
import streamlit as st

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from components.ui_components import (
    module_header, 
    inject_global_css, 
    style_sidebar
)

st.set_page_config(
    page_title="Read More: Theory & Guide | Catalysis", 
    page_icon="https://img.icons8.com/?size=100&id=vtLGHdmfoSt8&format=png&color=000000", 
    layout="wide"
)
inject_global_css()
style_sidebar()

module_header("06", "Knowledge Base & Technical Troubleshooting", "Theoretical foundations, Volcano plots, and troubleshooting guide")

tab_theory, tab_tech = st.tabs(["Sub-Tab 1: Electrocatalysis Scientific Theory", "Sub-Tab 2: Technical & Error Recovery Guide"])

with tab_theory:
    st.markdown(r"""
    ### 1. Fundamentals of Hydrogen Evolution Reaction (HER)
    HER reduces aqueous protons into molecular hydrogen via a 2-electron pathway:
    $$2\text{H}^+ + 2e^- \rightarrow \text{H}_2 \quad (U^0 = 0.00\text{ V vs. RHE})$$

    * **Volmer Step (Proton Adsorption):**
      $$* + \text{H}^+ + e^- \rightarrow \text{H}^* \quad (\Delta G_1 = \Delta G_{\text{H}^*})$$
    * **Heyrovsky Step (Electrochemical Desorption):**
      $$\text{H}^* + \text{H}^+ + e^- \rightarrow * + \text{H}_2 \quad (\Delta G_2 = -\Delta G_{\text{H}^*})$$
    * **Limiting Potential & Overpotential:**
      $$U_L = -\frac{\max(\Delta G_1, \Delta G_2)}{e} = -\frac{|\Delta G_{\text{H}^*}|}{e}, \quad \eta_{\text{HER}} = -U_L$$

    ---

    ### 2. Fundamentals of Oxygen Evolution Reaction (OER — 6-Step Mechanism)
    OER oxidizes water to evolve molecular oxygen gas via 4 concerted proton-electron steps, explicitly decoupling water adsorption and oxygen release:
    $$2\text{H}_2\text{O} \rightarrow \text{O}_2 + 4\text{H}^+ + 4e^- \quad (U^0 = 1.23\text{ V vs. RHE})$$

    * **Step 1 (Chemical):** $* + \text{H}_2\text{O} \rightarrow \text{H}_2\text{O}^* \quad (\Delta G_1 = \Delta E_{\text{ads}}(\text{H}_2\text{O}^*))$
    * **Step 2 (PCET):** $\text{H}_2\text{O}^* \rightarrow \text{OH}^* + \text{H}^+ + e^- \quad (\Delta G_2 = \Delta E_{\text{ads}}(\text{OH}^*) - \Delta E_{\text{ads}}(\text{H}_2\text{O}^*) + 0.35\text{ eV})$
    * **Step 3 (PCET):** $\text{OH}^* \rightarrow \text{O}^* + \text{H}^+ + e^- \quad (\Delta G_3 = \Delta E_{\text{ads}}(\text{O}^*) - \Delta E_{\text{ads}}(\text{OH}^*) + 0.05\text{ eV})$
    * **Step 4 (PCET):** $\text{O}^* + \text{H}_2\text{O} \rightarrow \text{OOH}^* + \text{H}^+ + e^- \quad (\Delta G_4 = \Delta E_{\text{ads}}(\text{OOH}^*) - \Delta E_{\text{ads}}(\text{O}^*) + 0.40\text{ eV})$
    * **Step 5 (PCET):** $\text{OOH}^* \rightarrow \text{O}_2^* + \text{H}^+ + e^- \quad (\Delta G_5 = \Delta E_{\text{ads}}(\text{O}_2^*) - \Delta E_{\text{ads}}(\text{OOH}^*) + 0.30\text{ eV})$
    * **Step 6 (Chemical):** $\text{O}_2^* \rightarrow * + \text{O}_2 \quad (\Delta G_6 = 4.92\text{ eV} - \sum_{i=1}^5 \Delta G_i)$

    The Potential-Determining Step (PDS) is determined by the most endergonic electrochemical step:
    $$G_{\max} = \max(\Delta G_2, \Delta G_3, \Delta G_4, \Delta G_5) \quad \Longrightarrow \quad U_L = \frac{G_{\max}}{e}, \quad \eta_{\text{OER}} = U_L - 1.23\text{ V}$$

    ---

    ### 3. The Sabatier Principle & Volcano Relations
    According to the Sabatier principle, optimal electrocatalytic performance is reached when intermediate binding is neither too weak (rate-limited by adsorption) nor too strong (rate-limited by desorption/poisoning).
    """)

with tab_tech:
    st.markdown(r"""
    ### Technical Manual & Module Troubleshooting

    | Module | Expected Inputs | Key Outputs | Common Pitfalls & Solutions |
    | :--- | :--- | :--- | :--- |
    | **Module 1 (Setup)** | Surface Name (e.g. `Pt111`), Reaction (`HER` / `OER`) | Workspace ZIP with tracking spreadsheet | **Path casing:** Use uppercase chemical directories (`H2/`, `H2O/`, `OH/`, `O/`, `OOH/`, `O2/`). |
    | **Module 2 (Adsorbate)** | `1-surface/PW.in` & relaxed `PW.out` | `3-adsorption/<species>/PW.in` | **Batch Mode:** In OER, batch generates all intermediates at once by default. |
    | **Module 3 (Tab 1)** | `3-adsorption/<species>/PW.out`, `2-isolated-gas/` | 6 displaced inputs (`PWINPUT_atm*`) per species | **Batch Mode:** Automatically logs all available intermediate energies and builds displacements. |
    | **Module 3 (Tab 2)** | Log files or frequency outputs in `4-vibration/` | Harmonic modes & ZPE in sheet `4-vibrasi` | **Batch Mode:** Automatically parses all available vibration outputs into Excel. |
    | **Module 4 (Gibbs)** | Tracking workbook with sheets 1–4 | Evaluated $\Delta G_i$, $U_L$, and publication diagrams | **Formula `#VALUE!`:** In-Python evaluator provides dynamic fallback values if Excel formulas haven't executed. |
    | **Module 5 (Screening)**| Multi-catalyst project `.zip` | Comparative diagrams & Sabatier volcano overlay | **Multi-surface:** Automatically distinguishes HER and OER archives to generate comparative tables and volcanoes. |
    """)
