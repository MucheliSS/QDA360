"""
QDA360 - Results Page

Display and export analysis results with dual-coder comparison.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import json
import io

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Lazy import to avoid spaCy compatibility issues
AgreementLevel = None

def get_agreement_level_class():
    global AgreementLevel
    if AgreementLevel is None:
        try:
            from qda360.core.dual_coder import AgreementLevel as _AgreementLevel
            AgreementLevel = _AgreementLevel
        except Exception as e:
            # Create a fallback enum-like class
            class FallbackAgreementLevel:
                CONSENSUS = "consensus"
                PARTIAL = "partial"
                DIVERGENT = "divergent"
            AgreementLevel = FallbackAgreementLevel
    return AgreementLevel

st.set_page_config(
    page_title="Results - QDA360",
    page_icon="📊",
    layout="wide"
)


def init_session_state():
    """Initialize session state."""
    defaults = {
        "api_key": None,
        "interviews": [],
        "topics_results": {},
        "themes_result": None,
        "current_step": 4
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_sidebar():
    """Render sidebar."""
    with st.sidebar:
        st.markdown("### 📋 Progress")
        st.markdown("✅ 1. Upload")
        st.markdown("✅ 2. Anonymize")
        st.markdown("✅ 3. Analyze")
        st.markdown("✅ 4. Results")
        
        if st.session_state.interviews:
            st.divider()
            st.markdown("### 📊 Study Info")
            st.markdown(f"**Interviews:** {len(st.session_state.interviews)}")
        
        st.divider()
        st.markdown("### 🤖 Dual-Coder System")
        st.markdown("🔵 Gemini 3 Flash")
        st.markdown("🟣 Claude Sonnet 4.5")


def get_agreement_badge(level) -> str:
    """Get HTML badge for agreement level."""
    AgreementLevelClass = get_agreement_level_class()
    
    # Handle both enum and string values
    level_value = level.value if hasattr(level, 'value') else str(level)
    
    if level_value == "consensus" or level == AgreementLevelClass.CONSENSUS:
        return '<span style="background: #D1FAE5; color: #059669; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem;">✓ Consensus</span>'
    elif level_value == "partial" or level == AgreementLevelClass.PARTIAL:
        return '<span style="background: #FEF3C7; color: #D97706; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem;">⚠ Partial</span>'
    else:
        return '<span style="background: #FEE2E2; color: #DC2626; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem;">! Divergent</span>'


def render_topic_card(topic: dict, source: str = "consensus"):
    """Render a single topic card."""
    title = topic.get("topic", "Unknown Topic")
    explanation = topic.get("explanation", "")
    quotes = topic.get("quotes", [])
    agreement = topic.get("agreement_score", 0)
    
    with st.container():
        # Header
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"**{title}**")
        with col2:
            if source == "consensus" and agreement:
                st.markdown(f"_{agreement:.0%} agreement_")
        
        # Explanation
        st.markdown(explanation)
        
        # Quotes
        if quotes:
            with st.expander(f"📝 {len(quotes)} supporting quotes"):
                for q in quotes:
                    idx = q.get("index", "?")
                    quote = q.get("quote", "")
                    st.markdown(f"> [{idx}] {quote}")
        
        st.divider()


def render_theme_card(theme: dict, show_comparison: bool = False):
    """Render a single theme card with comparison view."""
    title = theme.get("theme", theme.get("title", "Unknown Theme"))
    explanation = theme.get("explanation", "")
    topics = theme.get("topics", theme.get("supporting_topics", []))
    agreement = theme.get("agreement_score", 0)
    gemini_version = theme.get("gemini_version")
    claude_version = theme.get("claude_version")
    
    # Determine agreement level styling
    if agreement >= 0.8:
        border_color = "#059669"
        bg_color = "#F0FDF4"
    elif agreement >= 0.5:
        border_color = "#D97706"
        bg_color = "#FFFBEB"
    else:
        border_color = "#DC2626"
        bg_color = "#FEF2F2"
    
    st.markdown(f"""
    <div style="border-left: 4px solid {border_color}; background: {bg_color}; padding: 1rem; border-radius: 0 8px 8px 0; margin-bottom: 1rem;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <strong style="font-size: 1.1rem;">{title}</strong>
            <span style="font-size: 0.85rem; color: #6B7280;">{agreement:.0%} agreement</span>
        </div>
        <p style="margin: 0.5rem 0; color: #374151;">{explanation}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Comparison view
    if show_comparison and (gemini_version or claude_version):
        with st.expander("🔍 Compare coder interpretations"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🔵 Gemini's version:**")
                if gemini_version:
                    st.markdown(f"*{gemini_version.get('explanation', 'N/A')}*")
            
            with col2:
                st.markdown("**🟣 Claude's version:**")
                if claude_version:
                    st.markdown(f"*{claude_version.get('explanation', 'N/A')}*")
    
    # Supporting topics
    if topics:
        with st.expander(f"📋 {len(topics)} supporting topics"):
            for t in topics:
                if isinstance(t, dict):
                    interview = t.get("interview", "Unknown")
                    topic_name = t.get("topic", "Unknown")
                    st.markdown(f"- **{interview}**: {topic_name}")
                else:
                    st.markdown(f"- {t}")


def export_to_json() -> str:
    """Export all results to JSON."""
    export_data = {
        "study_context": st.session_state.get("study_context", ""),
        "interviews_count": len(st.session_state.interviews),
        "topics": {},
        "themes": {}
    }
    
    # Export topics
    for interview_name, result in st.session_state.topics_results.items():
        corr = result.get("corroborated")
        export_data["topics"][interview_name] = {
            "gemini_topics": result.get("gemini_topics", []),
            "claude_topics": result.get("claude_topics", []),
            "consensus_topics": corr.consensus_result if corr else [],
            "agreement_score": corr.agreement_score if corr else 0,
            "agreement_level": corr.agreement_level.value if corr else "unknown"
        }
    
    # Export themes
    if st.session_state.themes_result:
        corr = st.session_state.themes_result.get("corroborated")
        export_data["themes"] = {
            "gemini_themes": st.session_state.themes_result.get("gemini_themes", []),
            "claude_themes": st.session_state.themes_result.get("claude_themes", []),
            "consensus_themes": corr.consensus_result if corr else [],
            "agreement_score": corr.agreement_score if corr else 0,
            "agreement_level": corr.agreement_level.value if corr else "unknown"
        }
    
    return json.dumps(export_data, indent=2, default=str)


def export_to_excel() -> bytes:
    """Export results to Excel."""
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Topics sheet
        topics_data = []
        for interview_name, result in st.session_state.topics_results.items():
            corr = result.get("corroborated")
            topics = corr.consensus_result if corr and corr.consensus_result else result.get("gemini_topics", [])
            
            for topic in topics:
                topics_data.append({
                    "Interview": interview_name,
                    "Topic": topic.get("topic", ""),
                    "Explanation": topic.get("explanation", ""),
                    "Agreement": topic.get("agreement_score", "N/A"),
                    "Quotes": "; ".join([q.get("quote", "") for q in topic.get("quotes", [])])
                })
        
        if topics_data:
            pd.DataFrame(topics_data).to_excel(writer, sheet_name="Topics", index=False)
        
        # Themes sheet
        if st.session_state.themes_result:
            corr = st.session_state.themes_result.get("corroborated")
            themes = corr.consensus_result if corr and corr.consensus_result else st.session_state.themes_result.get("gemini_themes", [])
            
            themes_data = []
            for theme in themes:
                supporting = theme.get("topics", theme.get("supporting_topics", []))
                supporting_text = "; ".join([
                    f"{t.get('interview', '')}: {t.get('topic', '')}" 
                    if isinstance(t, dict) else str(t)
                    for t in supporting
                ])
                
                themes_data.append({
                    "Theme": theme.get("theme", theme.get("title", "")),
                    "Explanation": theme.get("explanation", ""),
                    "Agreement": theme.get("agreement_score", "N/A"),
                    "Supporting Topics": supporting_text
                })
            
            if themes_data:
                pd.DataFrame(themes_data).to_excel(writer, sheet_name="Themes", index=False)
        
        # Summary sheet
        summary_data = [{
            "Metric": "Interviews Analyzed",
            "Value": len(st.session_state.interviews)
        }, {
            "Metric": "Total Topics",
            "Value": sum(len(r.get("gemini_topics", [])) for r in st.session_state.topics_results.values())
        }]
        
        if st.session_state.themes_result:
            summary_data.append({
                "Metric": "Themes Identified",
                "Value": len(st.session_state.themes_result.get("gemini_themes", []))
            })
        
        pd.DataFrame(summary_data).to_excel(writer, sheet_name="Summary", index=False)
    
    return output.getvalue()


def main():
    """Main results page."""
    init_session_state()
    render_sidebar()
    
    st.markdown("# 📊 Analysis Results")
    st.markdown("View and export your dual-coder analysis results.")
    
    # Check if we have results
    if not st.session_state.topics_results:
        st.warning("No analysis results available. Please run the analysis first.")
        if st.button("← Go to Analysis"):
            st.switch_page("pages/3_Analyze.py")
        return
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Topics", "🎯 Themes", "📈 Validation", "💾 Export"])
    
    # Topics tab
    with tab1:
        st.markdown("### Topics by Interview")
        st.markdown("Topics extracted from each interview with dual-coder agreement.")
        
        for interview_name, result in st.session_state.topics_results.items():
            with st.expander(f"**{interview_name}**", expanded=True):
                corr = result.get("corroborated")
                
                if corr:
                    # Show agreement summary
                    badge = get_agreement_badge(corr.agreement_level)
                    st.markdown(f"Agreement: {badge} ({corr.agreement_score:.0%})", unsafe_allow_html=True)
                    st.markdown(f"*{corr.merge_notes}*")
                    st.divider()
                    
                    # Show consensus topics
                    if corr.consensus_result:
                        for topic in corr.consensus_result:
                            render_topic_card(topic, "consensus")
                    
                    # Show differences
                    if corr.differences:
                        st.markdown("#### ⚠️ Coder Differences")
                        for diff in corr.differences:
                            diff_type = diff.get("type", "")
                            if "gemini" in diff_type:
                                st.markdown(f"🔵 *Unique to Gemini:* **{diff.get('topic', '')}**")
                            else:
                                st.markdown(f"🟣 *Unique to Claude:* **{diff.get('topic', '')}**")
                else:
                    # Fallback to gemini topics
                    for topic in result.get("gemini_topics", []):
                        render_topic_card(topic, "gemini")
    
    # Themes tab
    with tab2:
        st.markdown("### Cross-Interview Themes")
        st.markdown("Themes identified across all interviews with dual-coder comparison.")
        
        if st.session_state.themes_result:
            corr = st.session_state.themes_result.get("corroborated")
            
            if corr:
                # Show agreement summary
                badge = get_agreement_badge(corr.agreement_level)
                st.markdown(f"Overall Agreement: {badge} ({corr.agreement_score:.0%})", unsafe_allow_html=True)
                st.markdown(f"*{corr.merge_notes}*")
                st.divider()
                
                # Show consensus themes
                if corr.consensus_result:
                    for theme in corr.consensus_result:
                        render_theme_card(theme, show_comparison=True)
                
                # Show differences
                if corr.differences:
                    st.markdown("### ⚠️ Coder Differences")
                    for diff in corr.differences:
                        diff_type = diff.get("type", "")
                        theme_name = diff.get("theme", "")
                        explanation = diff.get("explanation", "")
                        
                        if "gemini" in diff_type:
                            st.markdown(f"🔵 **Unique to Gemini:** {theme_name}")
                        else:
                            st.markdown(f"🟣 **Unique to Claude:** {theme_name}")
                        st.markdown(f"  _{explanation}_")
            else:
                # Fallback
                for theme in st.session_state.themes_result.get("gemini_themes", []):
                    render_theme_card(theme)
        else:
            st.info("No themes available. Run analysis with multiple interviews to identify themes.")
    
    # Validation tab
    with tab3:
        st.markdown("### Validation Report")
        st.markdown("Summary of dual-coder agreement across your analysis.")
        
        # Agreement metrics
        col1, col2, col3 = st.columns(3)
        
        # Calculate averages
        topic_agreements = []
        for result in st.session_state.topics_results.values():
            if result.get("corroborated"):
                topic_agreements.append(result["corroborated"].agreement_score)
        
        avg_topic_agreement = sum(topic_agreements) / len(topic_agreements) if topic_agreements else 0
        
        theme_agreement = 0
        if st.session_state.themes_result and st.session_state.themes_result.get("corroborated"):
            theme_agreement = st.session_state.themes_result["corroborated"].agreement_score
        
        with col1:
            st.metric("Average Topic Agreement", f"{avg_topic_agreement:.0%}")
        
        with col2:
            st.metric("Theme Agreement", f"{theme_agreement:.0%}")
        
        with col3:
            overall = (avg_topic_agreement + theme_agreement) / 2 if theme_agreement else avg_topic_agreement
            st.metric("Overall Agreement", f"{overall:.0%}")
        
        st.divider()
        
        # Detailed breakdown
        st.markdown("#### Agreement by Interview")
        
        agreement_data = []
        for interview_name, result in st.session_state.topics_results.items():
            corr = result.get("corroborated")
            if corr:
                agreement_data.append({
                    "Interview": interview_name,
                    "Agreement Score": f"{corr.agreement_score:.0%}",
                    "Level": corr.agreement_level.value.title(),
                    "Gemini Topics": len(result.get("gemini_topics", [])),
                    "Claude Topics": len(result.get("claude_topics", [])),
                    "Consensus Topics": len(corr.consensus_result) if corr.consensus_result else 0
                })
        
        if agreement_data:
            st.dataframe(pd.DataFrame(agreement_data), use_container_width=True, hide_index=True)
        
        # Interpretation guide
        st.markdown("---")
        st.markdown("""
        #### Interpreting Agreement Levels
        
        - ✅ **Consensus (>80%)**: Both coders identified similar findings. High confidence in results.
        - ⚠️ **Partial (50-80%)**: Some overlap but differences exist. Review recommended to resolve discrepancies.
        - 🔴 **Divergent (<50%)**: Significant disagreement. Requires human judgment to select or merge findings.
        
        *Note: Lower agreement doesn't mean poor quality - it may indicate genuinely ambiguous data that benefits from multiple perspectives.*
        """)
    
    # Export tab
    with tab4:
        st.markdown("### Export Results")
        st.markdown("Download your analysis results in various formats.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📄 JSON Export")
            st.markdown("Complete data including both coder results and comparisons.")
            
            json_data = export_to_json()
            st.download_button(
                "Download JSON",
                data=json_data,
                file_name="qda360_results.json",
                mime="application/json",
                use_container_width=True
            )
        
        with col2:
            st.markdown("#### 📊 Excel Export")
            st.markdown("Formatted spreadsheet with Topics, Themes, and Summary sheets.")
            
            excel_data = export_to_excel()
            st.download_button(
                "Download Excel",
                data=excel_data,
                file_name="qda360_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        # Preview
        st.markdown("---")
        st.markdown("#### 👁️ JSON Preview")
        with st.expander("View JSON data"):
            st.code(json_data, language="json")
    
    # Navigation
    st.markdown("---")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("← Back to Analysis"):
            st.switch_page("pages/3_Analyze.py")
    
    with col2:
        if st.button("🔄 Start New Analysis"):
            # Clear session state
            for key in ["topics_results", "themes_result", "analysis_complete", "analysis_started"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.switch_page("pages/1_Upload.py")


if __name__ == "__main__":
    main()
