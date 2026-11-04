import streamlit as st
from components.ui_components import (
    module_header, 
    sub_section_header, 
    highlight_box, 
    inject_global_css, 
    style_sidebar
)

st.set_page_config(page_title="Read More: Theory & Guide | HER", page_icon="https://img.icons8.com/?size=100&id=vtLGHdmfoSt8&format=png&color=000000", layout="wide")
inject_global_css()
style_sidebar()

module_header("06", "Knowledge Base & Technical Troubleshooting", "Theoretical foundations, Volcano plots, and troubleshooting guide")

tab_theory, tab_tech = st.tabs(["Sub-Tab 1: HER Scientific Theory", "Sub-Tab 2: Technical & Error Recovery Guide"])

with tab_theory:
    st.markdown(r"""
    ### Fundamentals of the Hydrogen Evolution Reaction (HER)
    The Hydrogen Evolution Reaction is a fundamental multi-step electrochemical process that reduces aqueous protons into molecular hydrogen gas:
    $$2\text{H}^+ + 2e^- \rightarrow \text{H}_2$$

    #### 1. Reaction Pathways
    Depending on the catalyst surface and reaction conditions (acidic vs. alkaline), HER proceeds via two distinct mechanisms:
    
    * **Volmer Step (Proton Adsorption / Discharge):**
      $$\text{H}^+ + e^- + * \rightarrow \text{H}^*$$
      *A proton from the electrolyte accepts an electron at an active surface site ($*$) to form an adsorbed hydrogen intermediate ($\text{H}^*$).*

    * **Followed by either:**
      * **Heyrovsky Step (Electrochemical Desorption):**
        $$\text{H}^* + \text{H}^+ + e^- \rightarrow \text{H}_2 + *$$
        *A second proton from solution reacts with the adsorbed hydrogen and an incoming electron to evolve molecular $\text{H}_2$.*
      * **Or Tafel Step (Chemical Recombination):**
        $$2\text{H}^* \rightarrow \text{H}_2 + 2*$$
        *Two neighboring adsorbed hydrogen atoms recombine chemically on the surface to produce $\text{H}_2$.*

    ---

    #### 2. The Sabatier Principle & Volcano Curve
    According to the **Sabatier principle**, an optimal catalyst must bind the intermediate with moderate strength:
    - If hydrogen binds **too weakly** ($\Delta G_{\text{H}^*} \gg 0$), the initial **Volmer** adsorption step is energetically hindered.
    - If hydrogen binds **too strongly** ($\Delta G_{\text{H}^*} \ll 0$), the **Heyrovsky / Tafel** desorption step is sluggish, leading to active site poisoning.
    - Optimum electrocatalytic activity occurs at the peak of the Volcano curve where **$\Delta G_{\text{H}^*} \approx 0\text{ eV}$** (e.g., Platinum group benchmark).

    ---

    #### 3. Computational Hydrogen Electrode (CHE) Model
    Under standard conditions ($U = 0\text{ V}$ vs. RHE, $\text{pH} = 0$, $T = 298.15\text{ K}$), the chemical potential of a proton-electron pair is equal to half that of gas-phase hydrogen:
    $$\mu(\text{H}^+) + \mu(e^-) = \frac{1}{2}\mu(\text{H}_2)$$
    
    The reaction free energy of hydrogen adsorption is evaluated as:
    $$\Delta G_{\text{H}^*} = \Delta E_{\text{H}} + \Delta\text{ZPE} - T\Delta S - eU + 0.0592 \times \text{pH}$$
    where:
    * $\Delta E_{\text{H}} = E(\text{slab+H}) - E(\text{slab}) - \frac{1}{2}E(\text{H}_2)$
    * $\Delta\text{ZPE} = \text{ZPE}(\text{H}^*) - \frac{1}{2}\text{ZPE}(\text{H}_2)$
    * $-T\Delta S \approx +\frac{1}{2} T S^\circ(\text{H}_2) \approx +0.202\text{ eV}$ at $298.15\text{ K}$
    """)

with tab_tech:
    st.markdown(r"""
    ### Technical Manual & Module Troubleshooting

    | Module | Expected Inputs | Key Output | Common Pitfalls & Solutions |
    | :--- | :--- | :--- | :--- |
    | **Module 1 (Setup)** | Surface Name (e.g., `Pt111`), Reaction (`HER`) | Workspace archive (`<Surface>_Module1_Setup.zip`) containing `<Surface>_her_data_sheet.xlsx` and subfolders | **Empty name:** Ensure surface name is not blank.<br>**Path casing:** Use uppercase chemical directories (`H2/`, `H2O/`, `H/`). |
    | **Module 2 (Adsorbate)** | `1-surface/PW.in` & relaxed `PW.out` | `3-adsorption/H/PW.in` with relaxed slab + H 1.0 Å above active site | **Duplicate coordinates:** Fixed via clean card decomposition.<br>**Unrelaxed coordinates:** Ensure relaxation has completed (`Begin final coordinates`). |
    | **Module 3 (Tab 1)** | `3-adsorption/H/PW.out`, `2-isolated-gas/H2/PW.out` | 6 displaced inputs (`PWINPUT_atm*`) in `4-vibration/H/` | **Calculation mode:** Fixed to enforce `calculation = 'scf'`, `nstep = 1`, and `tprnfor = .true.`.<br>**Extension:** Output files omit `.in` so cluster scripts can add it. |
    | **Module 3 (Tab 2)** | Log files or frequency outputs in `4-vibration/H/` | Harmonic modes & ZPE in sheet `4-vibrasi` | **Missing logs:** If no log files exist, sheet `4-vibrasi` is left blank for manual user entry. |
    | **Module 4 (Gibbs)** | Tracking workbook with sheets 1–4 populated | Evaluated $\Delta G_{\text{H}^*}$ registered into sheet `5-gibbs` | **Formula `#VALUE!`:** Verify all previous energy cells are numeric. If vibration logs were missing, fill column `energy_ev` in `4-vibrasi` manually. |
    | **Module 5 (Visual)** | Completed project `.zip` (single or multi-surface) | `5-data-visual/her_free_energy_diagram.png` | **Multi-surface comparison:** Archive can contain multiple `<Surface>_her_data_sheet.xlsx` files to compare catalyst profiles on one plot. |

    ---

    #### Quantum ESPRESSO File Standards
    1. **Strict File Naming:** All QE calculation runs inside subfolders must be named `PW.in` and `PW.out`.
    2. **Dedicated Adsorbate Vibration Folder:** Finite displacement calculation files are organized in `4-vibration/H/`.
    3. **Canonical Excel Workbook:** Always use `<SurfaceName>_her_data_sheet.xlsx` to track parameters across all modules.
    """)
