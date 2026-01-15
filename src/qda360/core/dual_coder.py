"""
QDA360: Dual-Coder LLM Orchestration System

This module provides the infrastructure for running two LLMs independently
and corroborating their results, mimicking the traditional qualitative research
practice of multiple human coders.
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import difflib

logger = logging.getLogger(__name__)


class AgreementLevel(Enum):
    """Classification of agreement between two coders."""
    CONSENSUS = "consensus"      # >80% overlap - auto-accept
    PARTIAL = "partial"          # 50-80% overlap - review suggested
    DIVERGENT = "divergent"      # <50% overlap - requires decision


@dataclass
class CoderResult:
    """Result from a single LLM coder."""
    coder_name: str
    model_id: str
    result: Any
    raw_response: Optional[str] = None
    processing_time: float = 0.0
    error: Optional[str] = None


@dataclass 
class CorroboratedResult:
    """Result of comparing and merging two coder results."""
    result_a: CoderResult
    result_b: CoderResult
    agreement_level: AgreementLevel
    agreement_score: float  # 0.0 to 1.0
    consensus_result: Any = None
    differences: List[Dict[str, Any]] = field(default_factory=list)
    human_review_needed: bool = False
    merge_notes: str = ""


class DualCoder:
    """
    Orchestrates two LLMs for independent coding with corroboration.
    
    This class manages the dual-coder workflow:
    1. Send the same prompt to both LLMs independently
    2. Collect and parse results from each
    3. Compare results and calculate agreement
    4. Generate consensus or flag for human review
    """
    
    GEMINI_MODEL = "openrouter/google/gemini-3-flash-preview"
    CLAUDE_MODEL = "openrouter/anthropic/claude-sonnet-4.5"
    
    def __init__(self, api_key: str):
        """
        Initialize dual-coder with OpenRouter API key.
        
        Args:
            api_key: OpenRouter API key for authentication
        """
        self.api_key = api_key
        self._setup_backends()
    
    def _setup_backends(self):
        """Configure LiteLLM backends for both models."""
        import litellm
        
        # Set OpenRouter API key
        litellm.api_key = self.api_key
        litellm.api_base = "https://openrouter.ai/api/v1"
        
        # Store model configs
        self.coder_a_config = {
            "name": "Gemini",
            "model": self.GEMINI_MODEL,
            "color": "🔵"
        }
        self.coder_b_config = {
            "name": "Claude", 
            "model": self.CLAUDE_MODEL,
            "color": "🟣"
        }
    
    async def _call_model(self, model_config: dict, messages: List[dict], 
                          temperature: float = 0.3) -> CoderResult:
        """
        Call a single model and return structured result.
        
        Args:
            model_config: Configuration dict with model details
            messages: Chat messages to send
            temperature: Sampling temperature
            
        Returns:
            CoderResult with response or error
        """
        import litellm
        import time
        
        start_time = time.time()
        
        try:
            response = await litellm.acompletion(
                model=model_config["model"],
                messages=messages,
                temperature=temperature,
                api_key=self.api_key,
                api_base="https://openrouter.ai/api/v1",
                custom_llm_provider="openrouter"
            )
            
            content = response.choices[0].message.content
            
            return CoderResult(
                coder_name=model_config["name"],
                model_id=model_config["model"],
                result=content,
                raw_response=content,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Error calling {model_config['name']}: {e}")
            return CoderResult(
                coder_name=model_config["name"],
                model_id=model_config["model"],
                result=None,
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    async def dual_call(self, messages: List[dict], 
                        temperature: float = 0.3) -> Tuple[CoderResult, CoderResult]:
        """
        Send the same prompt to both coders in parallel.
        
        Args:
            messages: Chat messages to send to both models
            temperature: Sampling temperature
            
        Returns:
            Tuple of (gemini_result, claude_result)
        """
        # Run both models in parallel
        results = await asyncio.gather(
            self._call_model(self.coder_a_config, messages, temperature),
            self._call_model(self.coder_b_config, messages, temperature),
            return_exceptions=True
        )
        
        # Handle any exceptions
        result_a = results[0] if not isinstance(results[0], Exception) else CoderResult(
            coder_name="Gemini",
            model_id=self.GEMINI_MODEL,
            result=None,
            error=str(results[0])
        )
        result_b = results[1] if not isinstance(results[1], Exception) else CoderResult(
            coder_name="Claude",
            model_id=self.CLAUDE_MODEL,
            result=None,
            error=str(results[1])
        )
        
        return result_a, result_b
    
    def calculate_text_similarity(self, text_a: str, text_b: str) -> float:
        """
        Calculate similarity between two text strings.
        
        Uses SequenceMatcher for a simple but effective comparison.
        
        Args:
            text_a: First text
            text_b: Second text
            
        Returns:
            Similarity score from 0.0 to 1.0
        """
        if not text_a or not text_b:
            return 0.0
        
        # Normalize texts
        text_a = text_a.lower().strip()
        text_b = text_b.lower().strip()
        
        return difflib.SequenceMatcher(None, text_a, text_b).ratio()
    
    def calculate_list_overlap(self, list_a: List[str], list_b: List[str], 
                               similarity_threshold: float = 0.7) -> float:
        """
        Calculate overlap between two lists of items (e.g., topics).
        
        Uses fuzzy matching to identify similar items.
        
        Args:
            list_a: First list of items
            list_b: Second list of items
            similarity_threshold: Minimum similarity to consider a match
            
        Returns:
            Overlap score from 0.0 to 1.0
        """
        if not list_a or not list_b:
            return 0.0
        
        matches = 0
        matched_b = set()
        
        for item_a in list_a:
            best_match = None
            best_score = 0
            
            for i, item_b in enumerate(list_b):
                if i in matched_b:
                    continue
                    
                score = self.calculate_text_similarity(item_a, item_b)
                if score > best_score and score >= similarity_threshold:
                    best_score = score
                    best_match = i
            
            if best_match is not None:
                matches += 1
                matched_b.add(best_match)
        
        # Calculate overlap as proportion of average list length
        avg_length = (len(list_a) + len(list_b)) / 2
        return matches / avg_length if avg_length > 0 else 0.0
    
    def classify_agreement(self, score: float) -> AgreementLevel:
        """
        Classify agreement level based on score.
        
        Args:
            score: Agreement score from 0.0 to 1.0
            
        Returns:
            AgreementLevel classification
        """
        if score >= 0.8:
            return AgreementLevel.CONSENSUS
        elif score >= 0.5:
            return AgreementLevel.PARTIAL
        else:
            return AgreementLevel.DIVERGENT
    
    def corroborate_topics(self, result_a: CoderResult, result_b: CoderResult,
                           topics_a: List[dict], topics_b: List[dict]) -> CorroboratedResult:
        """
        Corroborate topic extraction results from two coders.
        
        Args:
            result_a: Raw result from coder A
            result_b: Raw result from coder B
            topics_a: Parsed topics from coder A
            topics_b: Parsed topics from coder B
            
        Returns:
            CorroboratedResult with agreement analysis
        """
        # Extract topic titles for comparison
        titles_a = [t.get("topic", "") for t in topics_a]
        titles_b = [t.get("topic", "") for t in topics_b]
        
        # Calculate overlap score
        overlap_score = self.calculate_list_overlap(titles_a, titles_b)
        agreement_level = self.classify_agreement(overlap_score)
        
        # Find differences
        differences = []
        
        # Topics unique to A
        for topic in topics_a:
            title = topic.get("topic", "")
            if not any(self.calculate_text_similarity(title, t) >= 0.7 for t in titles_b):
                differences.append({
                    "type": "unique_to_gemini",
                    "topic": title,
                    "explanation": topic.get("explanation", "")
                })
        
        # Topics unique to B
        for topic in topics_b:
            title = topic.get("topic", "")
            if not any(self.calculate_text_similarity(title, t) >= 0.7 for t in titles_a):
                differences.append({
                    "type": "unique_to_claude",
                    "topic": title,
                    "explanation": topic.get("explanation", "")
                })
        
        # Merge consensus topics
        consensus_topics = []
        matched_b = set()
        
        for topic_a in topics_a:
            title_a = topic_a.get("topic", "")
            best_match = None
            best_score = 0
            
            for i, topic_b in enumerate(topics_b):
                if i in matched_b:
                    continue
                title_b = topic_b.get("topic", "")
                score = self.calculate_text_similarity(title_a, title_b)
                if score > best_score and score >= 0.7:
                    best_score = score
                    best_match = (i, topic_b)
            
            if best_match:
                matched_b.add(best_match[0])
                # Create merged topic
                merged = {
                    "topic": topic_a.get("topic"),  # Keep A's title
                    "explanation": topic_a.get("explanation"),
                    "quotes": topic_a.get("quotes", []),
                    "gemini_version": topic_a,
                    "claude_version": best_match[1],
                    "agreement_score": best_score
                }
                consensus_topics.append(merged)
        
        return CorroboratedResult(
            result_a=result_a,
            result_b=result_b,
            agreement_level=agreement_level,
            agreement_score=overlap_score,
            consensus_result=consensus_topics,
            differences=differences,
            human_review_needed=(agreement_level != AgreementLevel.CONSENSUS),
            merge_notes=f"Found {len(consensus_topics)} consensus topics, {len(differences)} differences"
        )
    
    def corroborate_themes(self, result_a: CoderResult, result_b: CoderResult,
                           themes_a: List[dict], themes_b: List[dict]) -> CorroboratedResult:
        """
        Corroborate theme extraction results from two coders.
        
        Similar to topic corroboration but for cross-interview themes.
        """
        # Extract theme titles
        titles_a = [t.get("title", t.get("theme", "")) for t in themes_a]
        titles_b = [t.get("title", t.get("theme", "")) for t in themes_b]
        
        overlap_score = self.calculate_list_overlap(titles_a, titles_b)
        agreement_level = self.classify_agreement(overlap_score)
        
        differences = []
        
        # Themes unique to each coder
        for theme in themes_a:
            title = theme.get("title", theme.get("theme", ""))
            if not any(self.calculate_text_similarity(title, t) >= 0.7 for t in titles_b):
                differences.append({
                    "type": "unique_to_gemini",
                    "theme": title,
                    "explanation": theme.get("explanation", "")
                })
        
        for theme in themes_b:
            title = theme.get("title", theme.get("theme", ""))
            if not any(self.calculate_text_similarity(title, t) >= 0.7 for t in titles_a):
                differences.append({
                    "type": "unique_to_claude",
                    "theme": title,
                    "explanation": theme.get("explanation", "")
                })
        
        # Merge consensus themes
        consensus_themes = []
        matched_b = set()
        
        for theme_a in themes_a:
            title_a = theme_a.get("title", theme_a.get("theme", ""))
            best_match = None
            best_score = 0
            
            for i, theme_b in enumerate(themes_b):
                if i in matched_b:
                    continue
                title_b = theme_b.get("title", theme_b.get("theme", ""))
                score = self.calculate_text_similarity(title_a, title_b)
                if score > best_score and score >= 0.7:
                    best_score = score
                    best_match = (i, theme_b)
            
            if best_match:
                matched_b.add(best_match[0])
                merged = {
                    "theme": title_a,
                    "explanation": theme_a.get("explanation"),
                    "topics": theme_a.get("topics", []),
                    "gemini_version": theme_a,
                    "claude_version": best_match[1],
                    "agreement_score": best_score
                }
                consensus_themes.append(merged)
        
        return CorroboratedResult(
            result_a=result_a,
            result_b=result_b,
            agreement_level=agreement_level,
            agreement_score=overlap_score,
            consensus_result=consensus_themes,
            differences=differences,
            human_review_needed=(agreement_level != AgreementLevel.CONSENSUS),
            merge_notes=f"Found {len(consensus_themes)} consensus themes, {len(differences)} differences"
        )
