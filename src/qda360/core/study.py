import uuid
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from .interview import Interview
from .models import ThemeList, TopicList, CoherenceAssessment
from .validated import Validated, ValidatedList
from .qindex import QIndex
# from .utils import print_mellea_validations, parse_coherence_rating
# from mellea import MelleaSession
# from mellea.stdlib.sampling import RejectionSamplingStrategy

logger = logging.getLogger(__name__)

class Study:
    """
    A collection of qualitative documents (for now only interviews are supported).
    """

    def __init__(self, files_or_docs=None, metadata=None, doc_cls=Interview, headers: Optional[list[dict]] = None, has_headers: Optional[list[bool]] = None, study_context=None, use_cache: bool = True, cache_dir: Optional[Path] = None):
        """
        Parameters
        ----------
        files : list[str | Path | Interview], optional
            Either a list of file paths OR a list of Interview objects.
        metadata : dict, optional
            Metadata to attach at corpus level.
        doc_cls : class, default=Interview
            Currently must be Interview
        headers: list of dict, optional
            Headers of columns for timestamp, speaker and statements in the documents
        has_headers: list of bool, optional
            Indicates if each file in files has headers or not. The matching with files is positional.
        study_context : str, optional
            Description of the overall study context (e.g., "Remote work experiences").
            Used as default for theme extraction if not overridden.
        use_cache : bool, default=True
            If True, attempts to load interviews from cache before parsing
        cache_dir : Path, optional
            Custom cache directory for interview states
        """
        logger.debug(f"Init Study")
        if doc_cls is not Interview:
            raise ValueError("Study currently only supports Interview documents.")

        self.id = f"study_{uuid.uuid4().hex[:8]}"
        self.doc_cls = doc_cls
        self.metadata = metadata or {}
        self.documents = []
        self.study_context = study_context
        self.themes_top_down = None
        self.use_cache = use_cache
        self.cache_dir = cache_dir
        logger.debug(f"Study ID: {self.id}")

        if files_or_docs:
            num_items = len(files_or_docs)
            if headers and len(headers) != num_items:
                raise ValueError(f"'headers' length ({len(headers)}) does not match number of documents ({num_items}).")

            if has_headers and len(has_headers) != num_items:
                raise ValueError(f"'has_headers' length ({len(has_headers)}) does not match number of documents ({num_items}).")
            
            for i, item in enumerate(files_or_docs):
                logger.debug(f"Processing item {item}")
                if headers:
                    self._add_checked(file_or_doc=item, headers=headers[i], has_headers=has_headers[i])
                elif has_headers:
                    self._add_checked(file_or_doc=item, has_headers=has_headers[i])
                else:
                    self._add_checked(file_or_doc=item)

    def _add_checked(self, file_or_doc, headers: Optional[dict] = None, has_headers: Optional[bool]= True):
        logger.debug(f"Add document {file_or_doc}| Study ID: {self.id}")
        if isinstance(file_or_doc, (str, Path)):
            self.documents.append(
                self.doc_cls(
                    file=file_or_doc,
                    metadata=self.metadata,
                    headers=headers,
                    has_headers=has_headers,
                    use_cache=self.use_cache,
                    cache_dir=self.cache_dir
                )
            )
        elif isinstance(file_or_doc, self.doc_cls):
            self.documents.append(file_or_doc)
        else:
            raise TypeError(
                f"Invalid type {type(file_or_doc)}. "
                f"Corpus only supports {self.doc_cls.__name__} objects or file paths."
            )
        
    def add(self, file_or_doc, headers: Optional[dict] = None, has_headers: Optional[bool]= True):
        """Add an Interview object or a file path."""
        logger.debug(f"Add document {file_or_doc} | Study ID: {self.id}")
        self._add_checked(file_or_doc=file_or_doc, headers=headers, has_headers=has_headers)


    def get_interview_by_id(self, interview_id: str):
        for doc in self.documents:
            if doc.id == interview_id:
                return doc
        return None

    def get_interviews_by_participant(self, participant_id: str):
        return [
            doc for doc in self.documents
            if doc.metadata.get("participant_id") == participant_id
        ]

    # Legacy methods removed to avoid mellea dependency
    # identify_interviewees(self, m=None)
    # suggest_topics_all(self, m: MelleaSession, ...)
    # suggest_themes(self, m: MelleaSession, ...)

    def anonymize_speakers(self):
        """
        Anonymize speakers for all interviews in the study.
        Calls Interview.anonymize_speakers_generic() on each interview.

        Returns
        -------
        dict
            Mapping of interview.id -> {original_speaker: anonymized_speaker}
        """
        logger.debug(f"Anonymize speakers - Study ID: {self.id}")
        all_mappings = {}

        for doc in self.documents:
            mapping = doc.anonymize_speakers_generic()
            all_mappings[doc.id] = mapping

        return all_mappings

    def __len__(self):
        return len(self.documents)

    def __iter__(self):
        return iter(self.documents)

    def __getitem__(self, idx):
        return self.documents[idx]
    
    def __repr__(self):
        context_str = f", context='{self.study_context}'" if self.study_context else ""
        return (
            f"<Study {self.id}: {len(self)} {self.doc_cls.__name__}(s){context_str}, "
            f"metadata={self.metadata}>"
        )