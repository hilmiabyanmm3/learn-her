import streamlit as st

def inject_global_css():
    """Injects modern typography, button styles matching reference.zip, and Font Awesome icons."""
    st.markdown("""
        <style>
            /* Import Inter Font & Font Awesome */
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
            @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css');

            html, body, [class*="css"] {
                font-family: 'Inter', sans-serif;
            }

            code, pre, .stCodeBlock {
                font-family: 'JetBrains Mono', monospace !important;
            }

            .stApp {
                background-color: #fcfcfc;
            }

            /* --- Reference-Grade Button Styles (#007BFF) --- */
            .stButton > button, 
            .stDownloadButton > button,
            button[kind="primary"],
            button[kind="secondary"] {
                border-radius: 8px !important;
                border: 1px solid #007BFF !important;
                background-color: #ffffff !important;
                color: #007BFF !important;
                font-weight: 600 !important;
                padding: 0.5rem 1.25rem !important;
                transition: all 0.3s ease !important;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
            }

            /* Primary submit buttons: solid blue by default */
            .stButton > button[kind="primary"],
            button[data-testid="baseButton-primary"] {
                background: linear-gradient(135deg, #007BFF 0%, #0056b3 100%) !important;
                color: #ffffff !important;
                border: 1px solid #0056b3 !important;
                box-shadow: 0 2px 6px rgba(0, 123, 255, 0.25) !important;
            }

            /* Hover states matching reference.zip */
            .stButton > button:hover, 
            .stDownloadButton > button:hover,
            button[kind="secondary"]:hover {
                background-color: #007BFF !important;
                color: #ffffff !important;
                border: 1px solid #007BFF !important;
                box-shadow: 0 4px 12px rgba(0, 123, 255, 0.25) !important;
                transform: translateY(-1px);
            }

            .stButton > button[kind="primary"]:hover {
                background: linear-gradient(135deg, #0069d9 0%, #004494 100%) !important;
                box-shadow: 0 6px 16px rgba(0, 123, 255, 0.35) !important;
                transform: translateY(-1px);
            }

            /* Sidebar styling */
            [data-testid="stSidebar"] {
                background-color: #ffffff;
                border-right: 1px solid #f0f2f6;
            }
            [data-testid="stSidebarNavItems"] li [aria-current="page"] {
                background-color: #eef6ff !important;
                color: #007BFF !important;
                font-weight: 700 !important;
                border-left: 4px solid #007BFF;
                border-radius: 4px 6px 6px 4px;
            }
            .stProgress > div > div > div > div {
                background-image: linear-gradient(to right, #007BFF, #00c6ff);
                border-radius: 10px;
                height: 6px;
            }
        </style>
    """, unsafe_allow_html=True)

def module_header(number: str, title: str, subtitle: str):
    """Refined header with gradient badge matching reference.zip."""
    st.markdown(f"""
        <div style="margin-bottom: 30px; padding-bottom: 15px; border-bottom: 1px solid #f0f2f6;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
                <span style="background: linear-gradient(135deg, #007BFF 0%, #0056b3 100%);
                             color: white; padding: 6px 16px; border-radius: 8px;
                             font-size: 0.85rem; font-weight: 800; letter-spacing: 0.5px;">
                    MODULE {number}
                </span>
                <h1 style="margin: 0; font-size: 2.0rem; font-weight: 800; color: #1a1c1e;">
                    {title}
                </h1>
            </div>
            <p style="margin: 0; color: #6c757d; font-size: 1.05rem;">
                {subtitle}
            </p>
        </div>
    """, unsafe_allow_html=True)

def sub_section_header(title: str, icon: str = "fa-solid fa-circle-chevron-right"):
    """Sub-section title with reference blue accent icon."""
    st.markdown(f"""
        <div style="margin-top: 25px; margin-bottom: 15px; display: flex; align-items: center; gap: 10px;">
            <i class="{icon}" style="color: #007BFF; font-size: 1.15rem;"></i>
            <h3 style="margin: 0; font-size: 1.25rem; font-weight: 700; color: #1a1c1e;">
                {title}
            </h3>
        </div>
    """, unsafe_allow_html=True)

def highlight_box(text: str, box_type: str = "info"):
    """Clean card-style callout box with blue border matching reference."""
    st.markdown(f"""
        <div style="
            background-color: #ffffff;
            border-left: 5px solid #007BFF;
            padding: 16px 20px;
            border-radius: 0 10px 10px 0;
            color: #3e444b;
            font-size: 0.95rem;
            margin: 15px 0 20px 0;
            box-shadow: 0 3px 10px rgba(0,0,0,0.04);
            line-height: 1.6;">
            {text}
        </div>
    """, unsafe_allow_html=True)

def style_sidebar():
    pass

def render_sidebar_progress(progress_val: int):
    with st.sidebar:
        st.markdown("<h2 style='font-size: 1.1rem; margin-top: 0; color: #1a1c1e;'>Workflow Journey</h2>", unsafe_allow_html=True)
        st.progress(progress_val / 100.0)
        st.caption(f"Pipeline Completion: **{progress_val}%**")
        st.markdown("---")
