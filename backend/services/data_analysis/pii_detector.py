"""Lightweight PII column name detector for data analysis privacy awareness.

This module detects potentially sensitive column names using regex patterns.
It is warning-only — column names are NOT aliased or redacted because the LLM
needs real column names to generate correct pandas code. The warning informs
users that column names (not data values) will be transmitted to the cloud LLM.
"""

import re
from typing import List

# Patterns that suggest a column may contain personally identifiable information.
# Matches whole words or common abbreviations (case-insensitive).
_PII_PATTERNS: List[re.Pattern[str]] = [
    re.compile(r"(?:^|[_\s])ssn(?:$|[_\s])", re.IGNORECASE),
    re.compile(r"social.?security", re.IGNORECASE),
    re.compile(r"email", re.IGNORECASE),
    re.compile(r"phone", re.IGNORECASE),
    re.compile(r"credit.?card", re.IGNORECASE),
    re.compile(r"passport", re.IGNORECASE),
    re.compile(r"drivers?.?licen[sc]e", re.IGNORECASE),
    re.compile(r"(?:date.?of.?birth|(?:^|[_\s])dob(?:$|[_\s]))", re.IGNORECASE),
    re.compile(r"address", re.IGNORECASE),
    re.compile(r"(?:salary|income|wage)", re.IGNORECASE),
    re.compile(r"patient.?id", re.IGNORECASE),
    re.compile(r"(?:^|[_\s])sin(?:$|[_\s])", re.IGNORECASE),  # Social Insurance Number (Canada)
]


def detect_pii_columns(column_names: List[str]) -> List[str]:
    """Return column names that match known PII patterns.

    Args:
        column_names: List of column name strings from a dataset.

    Returns:
        List of column names flagged as potentially sensitive.
        Empty list if no PII-like names detected.
    """
    flagged: List[str] = []
    for col_name in column_names:
        for pattern in _PII_PATTERNS:
            if pattern.search(col_name):
                flagged.append(col_name)
                break
    return flagged
