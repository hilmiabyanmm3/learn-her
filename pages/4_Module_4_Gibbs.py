import streamlit as st
from components.ui_components import (
    module_header, 
    sub_section_header, 
    highlight_box, 
    inject_global_css, 
    style_sidebar, 
    render_sidebar_progress
)
from utils.module_4_utils import calculate_gibbs_and_visualize

st.set_page_config(page_title="Module 4: Delta Gibbs & Visualization | HER", page_icon="https://img.icons8.com/?size=100&id=vtLGHdmfoSt8&format=png&color=000000", layout="wide")
inject_global_css()
style_sidebar()
render_sidebar_progress(80)

module_header(
    "04", 
    "Delta Gibbs & Visualization", 
    "Evaluate standard reaction Gibbs energy, compute Limiting Potential (U_L), update Excel tracker, and render separated profiles"
)

highlight_box(
    "<b>Objective:</b> Evaluates the standard reaction Gibbs free energy and computes the "
    "<b>Limiting Potential (U<sub>L</sub> = -|ΔG<sub>H*</sub>|/e)</b>. "
    "Populates sheet <code>5-gibbs</code> with dynamic Excel formulas and evaluated numeric floats. "
    "Produces two distinctly separate graphs saved directly into <code>5-data-visual/</code>:<br>"
    "1. <b>Gibbs Graph:</b> Reaction Coordinate Free Energy Profile (ΔG vs. Reaction Coordinate).<br>"
    "2. <b>U<sub>L</sub> Graph:</b> Limiting Potential vs. H Adsorption Energy Volcano Plot.",
    box_type="info"
)

st.latex(r"\Delta G_{\mathrm{H}^*} = \Delta E_{\mathrm{H}} + \Delta \mathrm{ZPE} - T\Delta S \quad \Longrightarrow \quad U_L = -\frac{|\Delta G_{\mathrm{H}^*}|}{e} \quad (\text{V vs. RHE})")

zip_file = st.file_uploader("Upload Project ZIP (with populated sheets 1 through 4)", type=["zip"])

col1, col2 = st.columns(2)
with col1:
    u_val = st.number_input("Electrode Potential U (V vs RHE)", value=0.0, step=0.05)
with col2:
    ph_val = st.number_input("Solution pH", value=0.0, min_value=0.0, max_value=14.0, step=0.5)

if zip_file:
    if st.button("Evaluate Gibbs Free Energy & Generate Diagrams →", type="primary"):
        with st.spinner("Calculating thermochemistry and rendering diagrams..."):
            out_zip, summary, gibbs_img, ul_img, err = calculate_gibbs_and_visualize(
                zip_file.getvalue(), u_val, ph_val
            )
        
        if err:
            st.error(err)
        else:
            st.success("Gibbs Free Energy and Limiting Potential computed; sheet `5-gibbs` updated!")
            
            # 5 Key Metric Cards
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("ΔE_H (eV)", f"{summary['delta_e']:.4f}")
            c2.metric("ΔZPE (eV)", f"{summary['delta_zpe']:.4f}")
            c3.metric("-TΔS (eV)", f"{-summary['t_delta_s']:.4f}")
            c4.metric("ΔG_H* (eV)", f"{summary['delta_g']:.4f}")
            c5.metric("Limiting Potential U_L", f"{summary['u_limiting']:+.4f} V")
            
            st.markdown("---")
            
            # Displaying both graphs separately with clear headers
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                sub_section_header("1. Gibbs Graph (Reaction Profile)", "fa-solid fa-chart-line")
                st.image(
                    gibbs_img, 
                    caption=f"Gibbs Free Energy Profile — {summary['surface']} (U = {u_val:.2f} V, pH = {ph_val:.1f})", 
                    use_container_width=True
                )
                
                dg_shifted = summary["delta_g_shifted"]
                if dg_shifted > 0.1:
                    st.warning(f"**Volmer Rate-Limiting:** ΔG_H*(U) = {dg_shifted:+.2f} eV > 0. Weak H adsorption.")
                elif dg_shifted < -0.1:
                    st.warning(f"**Heyrovsky/Tafel Rate-Limiting:** ΔG_H*(U) = {dg_shifted:+.2f} eV < 0. Strong H adsorption.")
                else:
                    st.success(f"**Optimal Performance:** |ΔG_H*(U)| = {abs(dg_shifted):.2f} eV ≈ 0. Near volcano apex.")

            with col_g2:
                sub_section_header("2. U_L Graph (Limiting Potential)", "fa-solid fa-mountain")
                st.image(
                    ul_img, 
                    caption=f"U_L Graph — Limiting Potential U_L vs. H Adsorption Energy ({summary['surface']})", 
                    use_container_width=True
                )
                st.info(f"**Limiting Potential:** U_L = **{summary['u_limiting']:+.3f} V vs. RHE** (Overpotential η = {summary['overpotential']:.3f} V).")

            st.download_button(
                label="⬇️ Download Updated Project ZIP (with Figures & Excel)",
                data=out_zip,
                file_name=f"{summary['surface']}_Module4_Completed.zip",
                mime="application/zip",
                use_container_width=True
            )
