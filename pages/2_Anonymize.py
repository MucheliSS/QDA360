"""
QDA360 - Anonymization Page

Optional speaker and entity anonymization.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

st.set_page_config(
    page_title="Anonymize - QDA360",
    page_icon="🔒",
    layout="wide"
)


def init_session_state():
    """Initialize session state."""
    defaults = {
        "api_key": None,
        "api_key_valid": False,
        "interviews": [],
        "anonymization_enabled": False,
        "entity_detection_enabled": False,
        "speaker_mappings": {},
        "entity_replacements": {},
        "anonymization_complete": False,
        "current_step": 2
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_sidebar():
    """Render sidebar."""
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
        
        st.divider()
        
        st.markdown("### 📋 Progress")
        st.markdown("✅ 1. Upload")
        st.markdown("✅ 2. Anonymize")
        st.markdown("⬜ 3. Analyze")
        st.markdown("⬜ 4. Results")
        
        if st.session_state.interviews:
            st.divider()
            st.markdown("### 📊 Study Info")
            st.markdown(f"**Interviews:** {len(st.session_state.interviews)}")


def anonymize_speakers(interview) -> dict:
    """Anonymize speakers in an interview."""
    try:
        mapping = interview.anonymize_speakers_generic()
        return mapping
    except Exception as e:
        st.error(f"Error anonymizing speakers: {e}")
        return {}


def detect_entities(interview, model: str = "en_core_web_sm") -> list:
    """Detect entities in interview."""
    try:
        entities = interview.detect_entities(model=model)
        return entities
    except Exception as e:
        st.error(f"Error detecting entities: {e}")
        return []


def main():
    """Main anonymization page."""
    init_session_state()
    render_sidebar()
    
    st.markdown("# 🔒 Anonymization")
    st.markdown("Optionally anonymize speakers and sensitive entities before analysis.")
    
    # Check if we have interviews
    if not st.session_state.interviews:
        st.warning("No interviews loaded. Please upload files first.")
        if st.button("← Go to Upload"):
            st.switch_page("pages/1_Upload.py")
        return
    
    st.info(f"📄 {len(st.session_state.interviews)} interview(s) loaded")
    
    st.divider()
    
    # Anonymization options
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Speaker Anonymization")
        st.markdown("""
        Replace speaker names with generic labels:
        - `Speaker 1` → `Participant`
        - `Interviewer` → `Researcher`
        """)
        
        st.session_state.anonymization_enabled = st.toggle(
            "Enable Speaker Anonymization",
            value=st.session_state.anonymization_enabled
        )
    
    with col2:
        st.markdown("### Entity Detection")
        st.markdown("""
        Detect and mask sensitive entities:
        - **PERSON**: Names of people
        - **ORG**: Organizations
        - **GPE**: Locations
        """)
        
        st.session_state.entity_detection_enabled = st.toggle(
            "Enable Entity Detection",
            value=st.session_state.entity_detection_enabled
        )
    
    st.divider()
    
    # Apply anonymization
    if st.session_state.anonymization_enabled or st.session_state.entity_detection_enabled:
        
        if st.button("🔄 Apply Anonymization", type="primary"):
            progress = st.progress(0, text="Processing...")
            
            total_steps = len(st.session_state.interviews)
            if st.session_state.entity_detection_enabled:
                total_steps *= 2  # Extra step for entity detection
            
            current_step = 0
            
            for i, interview in enumerate(st.session_state.interviews):
                interview_name = f"Interview {i+1}"
                
                # Speaker anonymization
                if st.session_state.anonymization_enabled:
                    progress.progress(
                        current_step / total_steps,
                        text=f"Anonymizing speakers in {interview_name}..."
                    )
                    mapping = anonymize_speakers(interview)
                    st.session_state.speaker_mappings[interview_name] = mapping
                    current_step += 1
                
                # Entity detection
                if st.session_state.entity_detection_enabled:
                    progress.progress(
                        current_step / total_steps,
                        text=f"Detecting entities in {interview_name}..."
                    )
                    entities = detect_entities(interview)
                    
                    if entities:
                        # Build replacement map
                        replacements = interview.build_replacement_map(entities)
                        interview.anonymize_statements(replacements)
                        st.session_state.entity_replacements[interview_name] = {
                            "entities": entities,
                            "replacements": replacements
                        }
                    current_step += 1
            
            progress.progress(1.0, text="Complete!")
            st.session_state.anonymization_complete = True
            st.success("✅ Anonymization complete!")
            st.rerun()
        
        # Show results if complete
        if st.session_state.anonymization_complete:
            st.markdown("### Anonymization Results")
            
            tabs = st.tabs([f"Interview {i+1}" for i in range(len(st.session_state.interviews))])
            
            for i, tab in enumerate(tabs):
                with tab:
                    interview = st.session_state.interviews[i]
                    interview_name = f"Interview {i+1}"
                    
                    # Speaker mapping
                    if interview_name in st.session_state.speaker_mappings:
                        mapping = st.session_state.speaker_mappings[interview_name]
                        if mapping:
                            st.markdown("**Speaker Mapping:**")
                            for orig, anon in mapping.items():
                                st.markdown(f"- `{orig}` → `{anon}`")
                    
                    # Entity replacements
                    if interview_name in st.session_state.entity_replacements:
                        data = st.session_state.entity_replacements[interview_name]
                        entities = data["entities"]
                        replacements = data["replacements"]
                        
                        st.markdown(f"**Entities Detected:** {len(entities)}")
                        
                        with st.expander("View entity replacements"):
                            for orig, repl in replacements.items():
                                st.markdown(f"- `{orig}` → `{repl}`")
                    
                    # Preview
                    st.markdown("**Preview (first 5 rows):**")
                    if interview.transcript is not None:
                        st.dataframe(
                            interview.transcript.head(5),
                            use_container_width=True,
                            hide_index=True
                        )
    
    else:
        st.info("👆 Enable anonymization options above, or skip to continue without anonymization.")
    
    # Navigation
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("← Back to Upload"):
            st.switch_page("pages/1_Upload.py")
    
    with col2:
        if st.session_state.api_key_valid:
            if st.button("Continue to Analysis →", type="primary"):
                st.session_state.current_step = 3
                st.switch_page("pages/3_Analyze.py")
        else:
            st.button("Continue →", disabled=True, help="API key required")


if __name__ == "__main__":
    main()
