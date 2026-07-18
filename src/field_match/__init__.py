"""field-match: compare datasets by column names and contents."""

from .compare import (
    Candidate,
    ComparisonReport,
    Suspect,
    align_to_model,
    compare,
    generate_column_rename,
)
from .io import list_sheets, read_table
from .matching import FieldMatch, match_fields, similarity_scores
from .similarity import (
    boolean_similarity,
    datetime_similarity,
    name_similarity,
    numeric_similarity,
    text_similarity,
)

__version__ = "0.4.0"

__all__ = [
    # the entry point
    "compare",
    "ComparisonReport",
    "Suspect",
    "Candidate",
    # conveniences
    "align_to_model",
    "generate_column_rename",
    "read_table",
    "list_sheets",
    # machinery
    "FieldMatch",
    "match_fields",
    "similarity_scores",
    "name_similarity",
    "numeric_similarity",
    "datetime_similarity",
    "boolean_similarity",
    "text_similarity",
    "__version__",
]
