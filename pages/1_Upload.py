"""
QDA360 - Upload Page

Handles file upload and study configuration.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import tempfile
import io

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Lazy import to avoid spaCy compatibility issues
Interview = None
def get_interview_class():
    global Interview
    if Interview is None:
        try:
            from qda360.core.interview import Interview as _Interview
            Interview = _Interview
        except Exception as e:
            st.error(f"Failed to import Interview: {e}")
            return None
    return Interview

st.set_page_config(
    page_title="Upload - QDA360",
    page_icon="📁",
    layout="wide"
)


def init_session_state():
    """Initialize session state if needed."""
    defaults = {
        "api_key": None,
        "api_key_valid": False,
        "interviews": [],
        "study_context": "",
        "uploaded_files_info": [],
        "current_step": 1
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def parse_uploaded_file(uploaded_file) -> dict:
    """
    Parse an uploaded file and return interview info.
    
    Returns dict with:
        - name: filename
        - interview: Interview object
        - speakers: list of speakers
        - turn_count: number of turns
        - error: error message if parsing failed
    """
    try:
        # Get Interview class (lazy import)
        InterviewClass = get_interview_class()
        if InterviewClass is None:
            return {
                "name": uploaded_file.name,
                "interview": None,
                "speakers": [],
                "turn_count": 0,
                "error": "Interview class not available (spaCy compatibility issue)"
            }
        
        # Get file extension
        suffix = Path(uploaded_file.name).suffix.lower()
        
        # Create temp file to pass to Interview
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = Path(tmp.name)
        
        # Parse with Interview class
        interview = InterviewClass(tmp_path, use_cache=False)
        
        # Get info
        speakers = interview.get_speakers()
        turn_count = len(interview.transcript) if interview.transcript is not None else 0
        
        # Clean up temp file
        tmp_path.unlink()
        
        return {
            "name": uploaded_file.name,
            "interview": interview,
            "speakers": speakers,
            "turn_count": turn_count,
            "error": None
        }
        
    except Exception as e:
        return {
            "name": uploaded_file.name,
            "interview": None,
            "speakers": [],
            "turn_count": 0,
            "error": str(e)
        }


def render_sidebar():
    """Render sidebar with API key and progress."""
    with st.sidebar:
        st.markdown("### 🔑 OpenRouter API")
        
        api_key = st.text_input(
            "API Key",
            type="password",
            value=st.session_state.api_key or "",
        )
        
        if api_key:
            st.session_state.api_key = api_key
            st.session_state.api_key_valid = True
            st.success("✓ API key configured")
        else:
            st.warning("⚠ API key required")
        
        st.divider()
        
        st.markdown("### 📋 Progress")
        st.markdown("✅ 1. Upload")
        st.markdown("⬜ 2. Anonymize")
        st.markdown("⬜ 3. Analyze")
        st.markdown("⬜ 4. Results")


def main():
    """Main upload page."""
    init_session_state()
    render_sidebar()
    
    st.markdown("# 📁 Upload Interviews")
    st.markdown("Upload your interview transcripts to begin analysis.")
    
    # Study context
    st.markdown("### Study Context")
    st.session_state.study_context = st.text_area(
        "Describe your study (optional but recommended)",
        value=st.session_state.study_context,
        placeholder="e.g., A qualitative study exploring remote work experiences among software developers...",
        help="Providing context helps the AI generate more relevant topics and themes"
    )
    
    st.divider()
    
    # File upload
    st.markdown("### Upload Files")
    
    uploaded_files = st.file_uploader(
        "Drag and drop or browse files",
        type=["docx", "xlsx", "csv"],
        accept_multiple_files=True,
        help="Supported formats: DOCX, XLSX, CSV"
    )
    
    if uploaded_files:
        st.markdown("---")
        st.markdown("### Uploaded Interviews")
        
        # Process each file
        interviews_info = []
        
        with st.spinner("Parsing files..."):
            for file in uploaded_files:
                # Check if already processed
                existing = next(
                    (i for i in st.session_state.uploaded_files_info 
                     if i["name"] == file.name), 
                    None
                )
                
                if existing:
                    interviews_info.append(existing)
                else:
                    info = parse_uploaded_file(file)
                    interviews_info.append(info)
        
        # Store in session
        st.session_state.uploaded_files_info = interviews_info
        st.session_state.interviews = [
            i["interview"] for i in interviews_info if i["interview"] is not None
        ]
        
        # Display table
        for info in interviews_info:
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            with col1:
                if info["error"]:
                    st.markdown(f"❌ **{info['name']}**")
                else:
                    st.markdown(f"✅ **{info['name']}**")
            
            with col2:
                st.markdown(f"{info['turn_count']} turns")
            
            with col3:
                st.markdown(f"{len(info['speakers'])} speakers")
            
            with col4:
                if info["error"]:
                    st.error("Parse error")
        
        # Show errors if any
        errors = [i for i in interviews_info if i["error"]]
        if errors:
            with st.expander(f"⚠️ {len(errors)} file(s) failed to parse"):
                for e in errors:
                    st.error(f"**{e['name']}**: {e['error']}")
        
        # Preview section
        st.markdown("---")
        st.markdown("### Preview")
        
        valid_interviews = [i for i in interviews_info if i["interview"]]
        if valid_interviews:
            selected = st.selectbox(
                "Select interview to preview",
                options=[i["name"] for i in valid_interviews]
            )
            
            selected_info = next(i for i in valid_interviews if i["name"] == selected)
            interview = selected_info["interview"]
            
            if interview.transcript is not None:
                # Show first few rows
                preview_df = interview.transcript.head(10).copy()
                st.dataframe(
                    preview_df,
                    use_container_width=True,
                    hide_index=True
                )
                
                if len(interview.transcript) > 10:
                    st.caption(f"Showing 10 of {len(interview.transcript)} rows")
    
    # Navigation
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("← Back to Home"):
            st.switch_page("app.py")
    
    with col2:
        valid_count = len([i for i in st.session_state.uploaded_files_info if i.get("interview")])
        
        if valid_count > 0:
            if st.button("Continue to Anonymization →", type="primary"):
                st.session_state.current_step = 2
                st.switch_page("pages/2_Anonymize.py")
        else:
            st.button("Continue →", disabled=True, help="Upload at least one valid file")


if __name__ == "__main__":
    main()
