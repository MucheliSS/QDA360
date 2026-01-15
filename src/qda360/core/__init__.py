import logging

# Configure logging defaults for the library
# Libraries should be quiet by default - users control verbosity in their code
logging.getLogger('qda360').setLevel(logging.WARNING)

# Suppress verbose logging from dependencies
logging.getLogger('fancy_logger').setLevel(logging.WARNING)
logging.getLogger('litellm').setLevel(logging.WARNING)

from .qindex import QIndex
from .validated import Validated, ValidatedList
from .interview import Interview
from .study import Study
from .models import Topic, TopicList, Quote
from .dual_coder import DualCoder, AgreementLevel, CorroboratedResult

__all__ = [
    "QIndex",
    "Validated",
    "ValidatedList",
    "Interview",
    "Study",
    "Topic",
    "TopicList",
    "Quote",
    "DualCoder",
    "AgreementLevel",
    "CorroboratedResult",
]

