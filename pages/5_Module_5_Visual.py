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
from utils.module_5_utils import generate_multi_surface_comparison

st.set_page_config(page_title="Module 5: Comparation | HER", page_icon="https://img.icons8.com/?size=100&id=vtLGHdmfoSt8&format=png&color=000000", layout="wide")
inject_global_css()
style_sidebar()
render_sidebar_progress(100)

module_header(
    "05", 
    "Catalyst Comparation", 
    "Multi-surface reaction coordinate comparison, Limiting Potential (U_L) Volcano curves, and Sabatier activity screening"
)

highlight_box(
    "<b>Multi-Catalyst Screening:</b> Upload an archive containing multiple catalyst folders or spreadsheets "
    "(e.g., <code>Pt111/</code>, <code>MoS2/</code>, <code>FeN4/</code>, etc.). This module generates two distinct comparative graphs:<br>"
    "1. <b>Comparative Gibbs Graph:</b> Multi-catalyst reaction coordinate profiles.<br>"
    "2. <b>Comparative U<sub>L</sub> Graph:</b> Multi-surface Limiting Potential vs. H Adsorption Energy volcano curve.",
    box_type="info"
)

st.latex(r"U_L = -\frac{|\Delta G_{\mathrm{H}^*}|}{e} \quad (\text{V vs. RHE}) \quad \Big[\Delta G < 0: \text{Heyrovsky limiting}, \quad \Delta G > 0: \text{Volmer limiting}\Big]")

zip_file = st.file_uploader("Upload Multi-Surface Project ZIP", type=["zip"])

col1, col2 = st.columns(2)
with col1:
    u_val = st.number_input("Electrode Potential U (V vs RHE)", value=0.0, step=0.05)
with col2:
    ph_val = st.number_input("Solution pH", value=0.0, min_value=0.0, max_value=14.0, step=0.5)

if zip_file:
    if st.button("Run Multi-Catalyst Comparison →", type="primary"):
        with st.spinner("Analyzing multi-surface datasets and rendering diagrams..."):
            out_zip, gibbs_img, ul_img, surfaces_data, err = generate_multi_surface_comparison(
                zip_file.getvalue(), u_val, ph_val
            )

        if err:
            st.error(err)
            if surfaces_data and len(surfaces_data) == 1:
                st.info(f"💡 Detected 1 surface: **{surfaces_data[0]['surface']}**. For single-surface visualization, limiting potential, and Excel updates, please use **Module 4 (Delta Gibbs & Visualization)**.")
        else:
            st.success(f"Successfully compared {len(surfaces_data)} catalyst surfaces!")

            # Display both diagrams side-by-side or in tabs
            col_comp1, col_comp2 = st.columns(2)

            with col_comp1:
                sub_section_header("1. Comparative Gibbs Graph", "fa-solid fa-chart-line")
                st.image(
                    gibbs_img, 
                    caption=f"HER Multi-Catalyst Free Energy Profiles (U = {u_val:.2f} V, pH = {ph_val:.1f})", 
                    use_container_width=True
                )

            with col_comp2:
                sub_section_header("2. Comparative U_L Graph", "fa-solid fa-mountain")
                st.image(
                    ul_img, 
                    caption="Comparative Limiting Potential (U_L vs. H Adsorption Energy)", 
                    use_container_width=True
                )

            st.markdown("---")
            sub_section_header("Comparative Performance Summary Table", "fa-solid fa-table-list")
            df_summary = pd.DataFrame([
                {
                    "Surface": s["surface"],
                    "*H Adsorption ΔE_H* (eV)": f"{s['delta_e']:.3f}",
                    "Base ΔG_H* (eV)": f"{s['delta_g']:.3f}",
                    "Limiting Potential U_L (V)": f"{s['u_l']:+.3f}",
                    "Overpotential η (V)": f"{s['overpotential']:.3f}",
                    "Shifted ΔG_H*(U, pH) (eV)": f"{s['delta_g_shifted']:.3f}",
                    "Catalytic Behavior": (
                        "Optimal (|ΔG| ≤ 0.1 eV)" if abs(s['delta_g_shifted']) <= 0.1
                        else ("Weak H Binding (Volmer limiting)" if s['delta_g_shifted'] > 0.1
                              else "Strong H Binding (Heyrovsky/Tafel limiting)")
                    )
                }
                for s in surfaces_data
            ])
            st.dataframe(df_summary, use_container_width=True)

            st.download_button(
                label="⬇️ Download Multi-Surface Comparison Archive",
                data=out_zip,
                file_name="HER_MultiSurface_Comparison.zip",
                mime="application/zip",
                use_container_width=True
            )
