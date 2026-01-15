"""
QDA360 - Analysis Page

Core dual-coder analysis workflow.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import asyncio
import json
import re

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Lazy import to avoid spaCy compatibility issues
DualCoder = None
AgreementLevel = None

def get_dual_coder_class():
    global DualCoder, AgreementLevel
    if DualCoder is None:
        try:
            from qda360.core.dual_coder import DualCoder as _DualCoder, AgreementLevel as _AgreementLevel
            DualCoder = _DualCoder
            AgreementLevel = _AgreementLevel
        except Exception as e:
            st.error(f"Failed to import DualCoder: {e}")
            return None, None
    return DualCoder, AgreementLevel

st.set_page_config(
    page_title="Analyze - QDA360",
    page_icon="🔍",
    layout="wide"
)


# Prompts for analysis
TOPIC_EXTRACTION_PROMPT = """You are a qualitative research analyst. Analyze this interview transcript and identify the main topics discussed by the interviewee.

For EACH topic, provide:
1. A concise topic title (3-5 words)
2. A brief explanation of the topic (1-2 sentences)
3. 2-3 representative quotes from the transcript (with row numbers if available)

Interview Context: {context}

Transcript:
{transcript}

Respond in valid JSON format:
{{
    "topics": [
        {{
            "topic": "Topic Title",
            "explanation": "Brief explanation of what this topic covers",
            "quotes": [
                {{"index": 5, "quote": "Exact quote from transcript"}},
                {{"index": 12, "quote": "Another quote"}}
            ]
        }}
    ]
}}

Identify 4-8 distinct topics. Focus on what the interviewee discusses, not the interviewer's questions."""


THEME_EXTRACTION_PROMPT = """You are a qualitative research analyst conducting thematic analysis across multiple interviews.

Given the topics extracted from {n_interviews} interviews, identify overarching THEMES that appear across multiple interviews.

A theme is a pattern of meaning that recurs across the data. Good themes:
- Appear in multiple interviews (not just one)
- Have clear conceptual coherence
- Are supported by multiple topics

Study Context: {context}

Topics from all interviews:
{topics_text}

Respond in valid JSON format:
{{
    "themes": [
        {{
            "theme": "Theme Title",
            "explanation": "What this theme represents across interviews",
            "supporting_topics": [
                {{"interview": "Interview 1", "topic": "Related Topic Title"}},
                {{"interview": "Interview 2", "topic": "Another Related Topic"}}
            ]
        }}
    ]
}}

Identify 3-6 major themes. Each theme should be supported by topics from at least 2 different interviews."""


def init_session_state():
    """Initialize session state."""
    defaults = {
        "api_key": None,
        "api_key_valid": False,
        "interviews": [],
        "study_context": "",
        "analysis_started": False,
        "analysis_complete": False,
        "current_analysis_step": 0,
        "topics_results": {},
        "themes_result": None,
        "current_step": 3
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
        st.markdown("✅ 3. Analyze")
        st.markdown("⬜ 4. Results")
        
        if st.session_state.interviews:
            st.divider()
            st.markdown("### 📊 Study Info")
            st.markdown(f"**Interviews:** {len(st.session_state.interviews)}")
        
        st.divider()
        st.markdown("### 🤖 Dual-Coder System")
        st.markdown("🔵 Gemini 3 Flash")
        st.markdown("🟣 Claude Sonnet 4.5")


def get_transcript_text(interview, max_rows: int = 100) -> str:
    """Convert interview transcript to text for LLM."""
    if interview.transcript is None:
        return ""
    
    df = interview.transcript.head(max_rows)
    lines = []
    
    for idx, row in df.iterrows():
        speaker = row.get("speaker", "Unknown")
        statement = row.get("statement", "")
        lines.append(f"[{idx}] {speaker}: {statement}")
    
    return "\n".join(lines)


def parse_json_response(text: str) -> dict:
    """Parse JSON from LLM response, handling markdown code blocks."""
    # Try to extract JSON from markdown code blocks
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if json_match:
        text = json_match.group(1)
    
    # Try to find JSON object
    try:
        # Find first { and last }
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            json_str = text[start:end+1]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    
    return {"error": "Failed to parse JSON", "raw": text}


async def run_dual_topic_extraction(dual_coder: DualCoder, interview, 
                                     context: str, interview_name: str) -> dict:
    """Run topic extraction with both coders."""
    transcript_text = get_transcript_text(interview)
    
    prompt = TOPIC_EXTRACTION_PROMPT.format(
        context=context or "General qualitative interview",
        transcript=transcript_text
    )
    
    messages = [{"role": "user", "content": prompt}]
    
    # Run dual call
    result_a, result_b = await dual_coder.dual_call(messages)
    
    # Parse results
    topics_a = []
    topics_b = []
    
    if result_a.result and not result_a.error:
        parsed = parse_json_response(result_a.result)
        topics_a = parsed.get("topics", [])
    
    if result_b.result and not result_b.error:
        parsed = parse_json_response(result_b.result)
        topics_b = parsed.get("topics", [])
    
    # Corroborate
    corroborated = dual_coder.corroborate_topics(result_a, result_b, topics_a, topics_b)
    
    return {
        "interview": interview_name,
        "gemini_topics": topics_a,
        "claude_topics": topics_b,
        "corroborated": corroborated,
        "gemini_raw": result_a,
        "claude_raw": result_b
    }


async def run_dual_theme_extraction(dual_coder: DualCoder, topics_results: dict,
                                     context: str) -> dict:
    """Run theme extraction with both coders."""
    # Build topics text from all interviews
    topics_lines = []
    for interview_name, result in topics_results.items():
        topics_lines.append(f"\n### {interview_name}")
        
        # Use consensus topics if available, else gemini
        topics = result.get("corroborated", {})
        if hasattr(topics, "consensus_result") and topics.consensus_result:
            for t in topics.consensus_result:
                topics_lines.append(f"- {t.get('topic', 'Unknown')}: {t.get('explanation', '')}")
        elif result.get("gemini_topics"):
            for t in result["gemini_topics"]:
                topics_lines.append(f"- {t.get('topic', 'Unknown')}: {t.get('explanation', '')}")
    
    topics_text = "\n".join(topics_lines)
    
    prompt = THEME_EXTRACTION_PROMPT.format(
        n_interviews=len(topics_results),
        context=context or "General qualitative study",
        topics_text=topics_text
    )
    
    messages = [{"role": "user", "content": prompt}]
    
    # Run dual call
    result_a, result_b = await dual_coder.dual_call(messages)
    
    # Parse results
    themes_a = []
    themes_b = []
    
    if result_a.result and not result_a.error:
        parsed = parse_json_response(result_a.result)
        themes_a = parsed.get("themes", [])
    
    if result_b.result and not result_b.error:
        parsed = parse_json_response(result_b.result)
        themes_b = parsed.get("themes", [])
    
    # Corroborate
    corroborated = dual_coder.corroborate_themes(result_a, result_b, themes_a, themes_b)
    
    return {
        "gemini_themes": themes_a,
        "claude_themes": themes_b,
        "corroborated": corroborated,
        "gemini_raw": result_a,
        "claude_raw": result_b
    }


def run_analysis():
    """Run the full dual-coder analysis."""
    st.session_state.analysis_started = True
    
    # Get DualCoder class (lazy import)
    DualCoderClass, _ = get_dual_coder_class()
    if DualCoderClass is None:
        st.error("Cannot run analysis - DualCoder not available")
        return
    
    # Create dual coder
    dual_coder = DualCoderClass(st.session_state.api_key)
    
    # Progress display
    progress_container = st.container()
    
    with progress_container:
        st.markdown("### 🔄 Analysis in Progress")
        
        # Create progress columns for dual coders
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🔵 Gemini 3 Flash")
            gemini_status = st.empty()
        
        with col2:
            st.markdown("#### 🟣 Claude Sonnet 4.5")
            claude_status = st.empty()
        
        overall_progress = st.progress(0)
        status_text = st.empty()
    
    # Run async analysis
    async def run_all():
        total_steps = len(st.session_state.interviews) + 1  # topics + themes
        current = 0
        
        # Extract topics from each interview
        for i, interview in enumerate(st.session_state.interviews):
            interview_name = f"Interview {i+1}"
            status_text.text(f"Extracting topics from {interview_name}...")
            gemini_status.info("Processing...")
            claude_status.info("Processing...")
            
            result = await run_dual_topic_extraction(
                dual_coder, 
                interview,
                st.session_state.study_context,
                interview_name
            )
            
            st.session_state.topics_results[interview_name] = result
            
            # Update status
            gemini_status.success(f"✓ {len(result['gemini_topics'])} topics")
            claude_status.success(f"✓ {len(result['claude_topics'])} topics")
            
            current += 1
            overall_progress.progress(current / total_steps)
        
        # Extract themes across all interviews
        status_text.text("Identifying themes across interviews...")
        gemini_status.info("Processing themes...")
        claude_status.info("Processing themes...")
        
        themes_result = await run_dual_theme_extraction(
            dual_coder,
            st.session_state.topics_results,
            st.session_state.study_context
        )
        
        st.session_state.themes_result = themes_result
        
        gemini_status.success(f"✓ {len(themes_result['gemini_themes'])} themes")
        claude_status.success(f"✓ {len(themes_result['claude_themes'])} themes")
        
        overall_progress.progress(1.0)
        status_text.text("Analysis complete!")
        
        st.session_state.analysis_complete = True
    
    # Run the async function
    asyncio.run(run_all())


def main():
    """Main analysis page."""
    init_session_state()
    render_sidebar()
    
    st.markdown("# 🔍 Dual-Coder Analysis")
    st.markdown("Run AI-assisted qualitative analysis with two independent LLM coders.")
    
    # Check prerequisites
    if not st.session_state.interviews:
        st.warning("No interviews loaded. Please upload files first.")
        if st.button("← Go to Upload"):
            st.switch_page("pages/1_Upload.py")
        return
    
    if not st.session_state.api_key_valid:
        st.error("⚠️ OpenRouter API key required. Enter it in the sidebar.")
        return
    
    # Show study info
    st.info(f"""
    **Ready to analyze:**
    - 📄 {len(st.session_state.interviews)} interview(s)
    - 📝 Context: {st.session_state.study_context[:100] if st.session_state.study_context else 'None provided'}
    """)
    
    st.divider()
    
    # Analysis workflow explanation
    st.markdown("""
    ### Analysis Workflow
    
    The dual-coder analysis will:
    
    1. **Topic Extraction** - Each interview is analyzed independently by both Gemini and Claude
    2. **Corroboration** - Topics are compared and agreement levels calculated
    3. **Theme Identification** - Cross-cutting themes are identified across all interviews
    4. **Final Corroboration** - Themes are compared between coders
    """)
    
    st.divider()
    
    # Run analysis button
    if not st.session_state.analysis_started:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Start Dual-Coder Analysis", type="primary", use_container_width=True):
                run_analysis()
    
    elif st.session_state.analysis_complete:
        st.success("✅ Analysis complete!")
        
        # Show summary
        st.markdown("### Summary")
        
        # Topics summary
        topics_count = sum(
            len(r.get("corroborated", {}).consensus_result or r.get("gemini_topics", []))
            for r in st.session_state.topics_results.values()
        )
        
        themes_count = 0
        if st.session_state.themes_result:
            corr = st.session_state.themes_result.get("corroborated")
            if corr and corr.consensus_result:
                themes_count = len(corr.consensus_result)
            else:
                themes_count = len(st.session_state.themes_result.get("gemini_themes", []))
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Interviews Analyzed", len(st.session_state.interviews))
        
        with col2:
            st.metric("Topics Identified", topics_count)
        
        with col3:
            st.metric("Themes Found", themes_count)
        
        # Navigation
        st.markdown("---")
        if st.button("View Results →", type="primary"):
            st.session_state.current_step = 4
            st.switch_page("pages/4_Results.py")
    
    # Navigation
    st.markdown("---")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("← Back to Anonymization"):
            st.switch_page("pages/2_Anonymize.py")


if __name__ == "__main__":
    main()
