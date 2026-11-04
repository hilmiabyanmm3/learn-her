import streamlit as st

def inject_global_css():
    """Injects modern typography, button styles, custom cards, and Font Awesome."""
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
            @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css');

            html, body, [class*="css"] {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            }

            code, pre, .stCodeBlock {
                font-family: 'JetBrains Mono', monospace !important;
            }

            .stApp {
                background-color: #f8fafc;
            }

            /* Buttons */
            .stButton > button {
                border-radius: 8px;
                font-weight: 600;
                padding: 0.55rem 1.25rem;
                transition: all 0.2s ease;
                border: 1px solid #2563eb;
            }
            .stButton > button:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
            }

            /* Custom metric card */
            .custom-card {
                background: white;
                border-radius: 12px;
                padding: 1.5rem;
                border: 1px solid #e2e8f0;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
                margin-bottom: 1.2rem;
            }
            
            .custom-card-title {
                font-size: 0.875rem;
                font-weight: 600;
                color: #64748b;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                margin-bottom: 0.5rem;
            }
            
            .custom-card-value {
                font-size: 1.75rem;
                font-weight: 700;
                color: #0f172a;
            }

            /* Info Box */
            .info-callout {
                background: #eff6ff;
                border-left: 4px solid #3b82f6;
                padding: 1rem 1.25rem;
                border-radius: 0 8px 8px 0;
                color: #1e3a8a;
                margin: 1rem 0;
            }
        </style>
    """, unsafe_allow_html=True)

def module_header(number: str, title: str, subtitle: str):
    """Renders a standard clean module header with numbered badge."""
    st.markdown(f"""
        <div style="margin-bottom: 30px; padding-bottom: 15px; border-bottom: 1px solid #e2e8f0;">
            <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 8px;">
                <span style="
                    background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
                    color: white;
                    padding: 4px 12px;
                    border-radius: 6px;
                    font-size: 0.85rem;
                    font-weight: 700;
                    letter-spacing: 0.05em;">
                    MODULE {number}
                </span>
                <h1 style="margin: 0; font-size: 1.9rem; font-weight: 800; color: #0f172a;">
                    {title}
                </h1>
            </div>
            <p style="margin: 0; color: #64748b; font-size: 1.05rem;">
                {subtitle}
            </p>
        </div>
    """, unsafe_allow_html=True)

def sub_section_header(title: str, icon: str = "fa-solid fa-layer-group"):
    """Sub-section title with Font Awesome icon."""
    st.markdown(f"""
        <div style="margin-top: 25px; margin-bottom: 15px; display: flex; align-items: center; gap: 10px;">
            <i class="{icon}" style="color: #2563eb; font-size: 1.15rem;"></i>
            <h3 style="margin: 0; font-size: 1.25rem; font-weight: 700; color: #1e293b;">
                {title}
            </h3>
        </div>
    """, unsafe_allow_html=True)

def highlight_box(text: str, box_type: str = "info"):
    """Styled banner/callout for guidelines and key notices."""
    colors = {
        "info": ("#eff6ff", "#3b82f6", "#1e40af"),
        "success": ("#f0fdf4", "#22c55e", "#166534"),
        "warning": ("#fffbeb", "#f59e0b", "#92400e"),
        "danger": ("#fef2f2", "#ef4444", "#991b1b")
    }
    bg, border, text_c = colors.get(box_type, colors["info"])
    st.markdown(f"""
        <div style="
            background-color: {bg};
            border-left: 4px solid {border};
            padding: 12px 18px;
            border-radius: 0 8px 8px 0;
            color: {text_c};
            font-size: 0.95rem;
            margin: 12px 0 20px 0;
            line-height: 1.5;">
            {text}
        </div>
    """, unsafe_allow_html=True)

def style_sidebar():
    """Styles the Streamlit sidebar."""
    st.markdown("""
        <style>
            section[data-testid="stSidebar"] {
                background-color: #0f172a;
            }
            section[data-testid="stSidebar"] .stMarkdown, 
            section[data-testid="stSidebar"] p, 
            section[data-testid="stSidebar"] span {
                color: #cbd5e1 !important;
            }
            section[data-testid="stSidebar"] h1, 
            section[data-testid="stSidebar"] h2, 
            section[data-testid="stSidebar"] h3 {
                color: #ffffff !important;
            }
        </style>
    """, unsafe_allow_html=True)

def render_sidebar_progress(progress_val: int):
    """Renders progress in sidebar."""
    with st.sidebar:
        st.markdown("### Workflow Progress")
        st.progress(progress_val / 100.0)
        st.caption(f"Pipeline Completion: {progress_val}%")
        st.markdown("---")
