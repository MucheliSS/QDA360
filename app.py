"""
QDA360 - AI-Assisted Qualitative Analysis with Dual-Coder Verification

A Streamlit application for transparent, validated qualitative research analysis
using two LLMs (Gemini 3 Flash & Claude Sonnet 4.5) as independent coders.
"""

import streamlit as st

# Page configuration - must be first Streamlit command
st.set_page_config(
    page_title="QDA360 - AI Qualitative Analysis",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    /* Main header styling */
    .main-header {
        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
    }
    
    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }
    
    /* Card styling - dark mode compatible */
    .info-card {
        background: #1E293B;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
        color: #F1F5F9;
    }
    
    .info-card h4 {
        color: #E2E8F0;
        margin-top: 0;
    }
    
    .info-card p, .info-card li {
        color: #CBD5E1;
    }
    
    /* Status indicators */
    .status-ok {
        color: #059669;
        font-weight: 600;
    }
    
    .status-check {
        color: #D97706;
        font-weight: 600;
    }
    
    .status-iffy {
        color: #DC2626;
        font-weight: 600;
    }
    
    /* Dual coder badges */
    .gemini-badge {
        background: #DBEAFE;
        color: #1D4ED8;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.875rem;
        font-weight: 500;
    }
    
    .claude-badge {
        background: #EDE9FE;
        color: #7C3AED;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.875rem;
        font-weight: 500;
    }
    
    /* Agreement indicators */
    .agreement-high {
        background: #D1FAE5;
        border-left: 4px solid #059669;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
    }
    
    .agreement-medium {
        background: #FEF3C7;
        border-left: 4px solid #D97706;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
    }
    
    .agreement-low {
        background: #FEE2E2;
        border-left: 4px solid #DC2626;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        "api_key": None,
        "api_key_valid": False,
        "interviews": [],
        "study_context": "",
        "anonymization_enabled": False,
        "entity_detection_enabled": False,
        "speaker_mapping": {},
        "entity_replacements": {},
        "analysis_complete": False,
        "topics_results": {},
        "themes_results": None,
        "current_step": 1
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_sidebar():
    """Render the sidebar with API configuration and navigation."""
    with st.sidebar:
        st.markdown("### 🔑 OpenRouter API")
        
        # API Key input
        api_key = st.text_input(
            "API Key",
            type="password",
            value=st.session_state.api_key or "",
            help="Enter your OpenRouter API key to use the dual-coder analysis"
        )
        
        if api_key:
            st.session_state.api_key = api_key
            st.session_state.api_key_valid = True
            st.success("✓ API key configured")
        else:
            st.warning("⚠ API key required for analysis")
        
        st.divider()
        
        # Navigation status
        st.markdown("### 📋 Progress")
        
        steps = [
            ("1. Upload", st.session_state.current_step >= 1),
            ("2. Anonymize", st.session_state.current_step >= 2),
            ("3. Analyze", st.session_state.current_step >= 3),
            ("4. Results", st.session_state.current_step >= 4)
        ]
        
        for step_name, completed in steps:
            if completed:
                st.markdown(f"✅ {step_name}")
            else:
                st.markdown(f"⬜ {step_name}")
        
        st.divider()
        
        # Study info
        if st.session_state.interviews:
            st.markdown("### 📊 Study Info")
            st.markdown(f"**Interviews:** {len(st.session_state.interviews)}")
            if st.session_state.study_context:
                st.markdown(f"**Context:** {st.session_state.study_context[:50]}...")
        
        st.divider()
        
        # Dual-coder info
        st.markdown("### 🤖 Dual-Coder System")
        st.markdown("""
        <div style="font-size: 0.85rem;">
        <span class="gemini-badge">🔵 Gemini 3 Flash</span><br><br>
        <span class="claude-badge">🟣 Claude Sonnet 4.5</span>
        </div>
        """, unsafe_allow_html=True)
        st.caption("Two LLMs code independently, then corroborate results")


def render_home():
    """Render the home/welcome page."""
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🔬 QDA360</h1>
        <p>AI-Assisted Qualitative Analysis with Dual-Coder Verification</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Introduction
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### Welcome to QDA360
        
        QDA360 helps qualitative researchers analyze interview data using AI, 
        with a unique **dual-coder verification system** that mirrors traditional 
        inter-rater reliability practices.
        
        #### How It Works
        
        1. **Upload** your interview transcripts (DOCX, XLSX, or CSV)
        2. **Anonymize** speakers and sensitive entities (optional)
        3. **Analyze** - Two LLMs independently code your data
        4. **Review** - See agreement levels and resolve differences
        
        #### The Dual-Coder Advantage
        
        Unlike single-LLM tools, QDA360 uses **two independent AI coders**:
        
        - 🔵 **Gemini 3 Flash** (Google)
        - 🟣 **Claude Sonnet 4.5** (Anthropic)
        
        Each analyzes your data separately, then results are compared:
        
        - ✅ **Consensus** (>80% agreement) - High confidence
        - ⚠️ **Partial** (50-80%) - Review recommended  
        - 🔴 **Divergent** (<50%) - Human decision needed
        """)
    
    with col2:
        st.markdown("""
        <div class="info-card">
            <h4>🔒 Privacy First</h4>
            <p>Your data stays in your session only. Nothing is stored after you close the browser.</p>
        </div>
        
        <div class="info-card">
            <h4>💡 Getting Started</h4>
            <ol>
                <li>Enter your OpenRouter API key in the sidebar</li>
                <li>Navigate to <strong>📁 Upload</strong> page</li>
                <li>Follow the guided workflow</li>
            </ol>
        </div>
        
        <div class="info-card">
            <h4>📄 Supported Formats</h4>
            <ul>
                <li>DOCX (Word documents)</li>
                <li>XLSX (Excel spreadsheets)</li>
                <li>CSV (Comma-separated)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Quick start button
    st.markdown("---")
    
    if st.session_state.api_key_valid:
        if st.button("🚀 Start New Analysis", type="primary", use_container_width=True):
            st.switch_page("pages/1_📁_Upload.py")
    else:
        st.info("👈 Enter your OpenRouter API key in the sidebar to begin")


def main():
    """Main application entry point."""
    init_session_state()
    render_sidebar()
    render_home()


if __name__ == "__main__":
    main()
