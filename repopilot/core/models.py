import dataclasses
from datetime import datetime
from typing import List, Dict, Optional, Any

"""
RepoPilot Core Models

This module defines the internal, pure Python dataclasses that act as the
currency of the RepoPilot engine. These structures represent Git primitives
(commits, clusters) and analysis results (classifications, churn metrics).

Rules:
- All models must be strictly decoupled from any specific serialization framework (no Pydantic).
- Models must be immutable (frozen) where possible to guarantee referential transparency.
- This module MUST NOT import any Git execution or reading logic.
"""

@dataclasses.dataclass(frozen=True)
class CommitNode:
    """Represents a single parsed commit from the local Git history."""
    hash: str
    author: str
    timestamp: datetime
    message: str
    branch: str
    insertions: int
    deletions: int
    files_added: List[str]
    files_modified: List[str]
    files_deleted: List[str]
    files_renamed: Dict[str, str]  # Map of old_path -> new_path

@dataclasses.dataclass(frozen=True)
class ClusterGroup:
    """Represents a cohesive run of commits strictly bounded by clustering rules."""
    cluster_id: str
    commits: List[CommitNode]
    start_timestamp: datetime
    end_timestamp: datetime
    closure_reason: str

@dataclasses.dataclass(frozen=True)
class ClassificationPayload:
    """Holds the deterministic outcome of the classification heuristic engine."""
    primary_classification: str
    confidence_score: float
    raw_signals: Dict[str, Any]
