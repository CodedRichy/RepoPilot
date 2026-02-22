from typing import Sequence, Set

from repopilot.core.models import ClusterGroup, ClassificationPayload

"""
RepoPilot Core: Deterministic Change Classification Engine

This module evaluates an aggregated ClusterGroup against strict deterministic heuristics
to assign exactly ONE primary classification and an associated confidence score.

Guarantees & Constraints:
- Side-effect free: Operates purely on immutable, in-memory ClusterGroup data.
- Deterministic: Identical ClusterGroups evaluate to identical ClassificationPayloads.
- Idempotent: Evaluation can be repeated infinitely yielding the exact same output.
- Isolated: This module NEVER accesses the filesystem or executes Git subprocesses.
- Singular Output: Every cluster translates to exactly ONE primary classification.

### Classification Layer Contract
- **Responsibility:** Deterministically mapping grouped commits to a single categorization.
- **NOT** Responsible For: Forming clusters, creating docs, querying Git, or executing shell paths.
- **Allowed Inputs:** `ClusterGroup` sequences and injected heuristic thresholds.
- **Output Guarantee:** Downstream layers may rely perfectly upon a single `primary_classification` string and `0.0 - 1.0` confidence score per cluster without recalculating original Git churn.
"""

def classify_cluster(
    cluster: ClusterGroup,
    noise_extensions: Sequence[str],
    noise_directories: Sequence[str],
    structural_rename_threshold: int,
    structural_config_filenames: Sequence[str],
    feature_burst_insertion_threshold: int,
    feature_burst_min_commits: int,
    vendor_directories: Sequence[str],
    refactor_deletion_ratio: float
) -> ClassificationPayload:
    """
    Evaluates a ClusterGroup to emit a single primary classification and confidence score.
    
    Rule evaluation prioritizes top-down constraints and short-circuits on the first
    matching signature. Time boundaries and Git queries must be resolved upstream.
    
    Args:
        cluster: The aggregated sequence of commits forming the atomic unit of work.
        noise_extensions: Explicit extensions signifying noise (e.g., .md, .txt).
        noise_directories: Explicit paths signifying noise (e.g., docs/).
        structural_rename_threshold: Minimum renames ('R' status) for a structural shift.
        structural_config_filenames: Exact filenames identifying structural root configs.
        feature_burst_insertion_threshold: Minimum total insertions for a feature burst.
        feature_burst_min_commits: Minimum distinct commits required in the cluster.
        vendor_directories: Paths excluded from feature burst logic (e.g., node_modules/).
        refactor_deletion_ratio: Deletion-to-insertion threshold to qualify as a refactor.

    Returns:
        ClassificationPayload: Contains exactly ONE primary_classification and a 0.0-1.0 confidence.
    """
    # 1. PRE-COMPUTATION
    # We aggregate signals across the entire cluster to avoid redundant iterations.
    
    total_insertions = 0
    total_deletions = 0
    total_renames = 0
    
    all_files_touched: Set[str] = set()
    all_files_added: Set[str] = set()
    
    for commit in cluster.commits:
        total_insertions += commit.insertions
        total_deletions += commit.deletions
        total_renames += len(commit.files_renamed)
        
        all_files_touched.update(commit.files_added)
        all_files_touched.update(commit.files_modified)
        all_files_touched.update(commit.files_deleted)
        all_files_touched.update(commit.files_renamed.values()) # new paths
        
        all_files_added.update(commit.files_added)
        
    raw_signals = {
        "commits_count": len(cluster.commits),
        "total_insertions": total_insertions,
        "total_deletions": total_deletions,
        "total_renames": total_renames,
        "total_files_touched": len(all_files_touched)
    }

    # Helper function for deterministic list checks
    def _is_noise_file(filepath: str) -> bool:
        """Determines if a single file matches noise parameters."""
        for ext in noise_extensions:
            if filepath.endswith(ext):
                return True
        for directory in noise_directories:
            if filepath.startswith(directory) or filepath.startswith(f"/{directory}"):
                return True
        return False

    def _is_config_file(filepath: str) -> bool:
        """Determines if a file matches structural configuration targets by exact filename."""
        filename = filepath.split('/')[-1]
        return filename in structural_config_filenames
        
    def _is_in_vendor(filepath: str) -> bool:
        """Determines if a file path is nested inside a vendor directory."""
        for vendor in vendor_directories:
            if filepath.startswith(vendor) or filepath.startswith(f"/{vendor}"):
                return True
        return False

    # 2. EVALUATION PIPELINE (Strict Priority Order & Short-Circuiting)

    # ---------------------------------------------------------
    # Rule 1: NOISE ONLY (`noise_only`)
    # Evaluates FIRST because if everything is noise, we don't care about structural shifts.
    # ALL touched files must match either an extension or a directory threshold.
    # ---------------------------------------------------------
    if all_files_touched and all(_is_noise_file(f) for f in all_files_touched):
        return ClassificationPayload(
            primary_classification="noise_only",
            confidence_score=1.0,  # Absolute certainty if rule is met
            raw_signals=raw_signals
        )

    # ---------------------------------------------------------
    # Rule 2: STRUCTURAL CHANGE (`structural_change`)
    # Evaluates SECOND. Structural shifts via mass renames or config tweaks override features.
    # ---------------------------------------------------------
    if total_renames >= structural_rename_threshold or any(_is_config_file(f) for f in all_files_touched):
        # Confidence scales based on how many renames occurred beyond the threshold, capped at 1.0.
        # If it fired via config file match, confidence is automatically 1.0.
        config_match = any(_is_config_file(f) for f in all_files_touched)
        score = 1.0 if config_match else min(1.0, total_renames / max(1, structural_rename_threshold))
        
        return ClassificationPayload(
            primary_classification="structural_change",
            confidence_score=score,
            raw_signals=raw_signals
        )

    # ---------------------------------------------------------
    # Rule 3: FEATURE BURST (`feature_burst`)
    # Evaluates THIRD. Requires sustained development effort (multiple commits, net positive code).
    # ---------------------------------------------------------
    added_non_vendor_files = len([f for f in all_files_added if not _is_in_vendor(f)])
    
    if (len(cluster.commits) >= feature_burst_min_commits and
        added_non_vendor_files > 0 and
        total_insertions > total_deletions and
        total_insertions >= feature_burst_insertion_threshold):
        
        # Confidence derived from how much the insertions exceed the threshold.
        # E.g., if threshold is 100 insertions, 100 = 0.5 confidence, 200 = 1.0.
        scaled_score = 0.5 + (0.5 * min(1.0, (total_insertions - feature_burst_insertion_threshold) / feature_burst_insertion_threshold))
        
        return ClassificationPayload(
            primary_classification="feature_burst",
            confidence_score=scaled_score,
            raw_signals=raw_signals
        )

    # ---------------------------------------------------------
    # Rule 4: REFACTOR CLUSTER (`refactor_cluster`)
    # Evaluates FOURTH as a specific fallback to detect restructuring without distinct feature additions.
    # We detect this if deletions are a significant portion of insertions, but not a pure delete.
    # ---------------------------------------------------------
    # Avoid zero division.
    if total_insertions > 0:
        actual_deletion_ratio = total_deletions / total_insertions
        if actual_deletion_ratio >= refactor_deletion_ratio:
            # Confidence scales up as the deletion ratio increases.
            clamped_ratio = min(1.0, actual_deletion_ratio)
            score = 0.7 + (0.3 * (clamped_ratio - refactor_deletion_ratio) / (1.0 - refactor_deletion_ratio + 0.001))
            
            return ClassificationPayload(
                primary_classification="refactor_cluster",
                confidence_score=min(1.0, score),
                raw_signals=raw_signals
            )

    # ---------------------------------------------------------
    # FALLBACK: UNKNOWN
    # If no criteria definitively match an intent, we fallback gracefully.
    # ---------------------------------------------------------
    return ClassificationPayload(
        primary_classification="unknown",
        confidence_score=0.1,  # Low confidence because it missed all heuristics
        raw_signals=raw_signals
    )
