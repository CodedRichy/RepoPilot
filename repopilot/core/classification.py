from typing import Sequence, Set

from repopilot.core.models import ClusterGroup, ClassificationPayload

"""
RepoPilot Core: Deterministic Change Classification Engine

This module evaluates an aggregated ClusterGroup against strict deterministic heuristics
to assign exactly ONE primary classification and an associated confidence score.

Guarantees & Constraints:
- Side-effect free: Operates purely on immutable, in-memory ClusterGroup data.
- Deterministic: Identical ClusterGroups evaluate to identical ClassificationPayloads. Set iterations are sorted.
- Idempotent: Evaluation can be repeated infinitely yielding the exact same output.
- Isolated: This module NEVER accesses the filesystem or executes Git subprocesses.
- Singular Output: Every cluster translates to exactly ONE primary classification.

### Classification Layer Contract
- **Responsibility:** Deterministically mapping grouped commits to a single categorization.
- **NOT** Responsible For: Forming clusters, creating docs, querying Git, or executing shell paths.
- **Allowed Inputs:** `ClusterGroup` sequences and injected heuristic thresholds.
- **Output Guarantee:** Downstream layers may rely perfectly upon a single `primary_classification` 
  string and `0.0 - 1.0` confidence score per cluster without recalculating original Git churn.
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
    """
    # 1. PRE-COMPUTATION
    total_insertions = 0
    total_deletions = 0
    total_renames = 0
    
    all_files_touched: Set[str] = set()
    all_files_added: Set[str] = set()
    
    for commit in cluster.commits:
        # Note: commit order is strictly preserved by the clustering engine input
        total_insertions += commit.insertions
        total_deletions += commit.deletions
        total_renames += len(commit.files_renamed)
        
        all_files_touched.update(commit.files_added)
        all_files_touched.update(commit.files_modified)
        all_files_touched.update(commit.files_deleted)
        all_files_touched.update(commit.files_renamed.values())
        
        all_files_added.update(commit.files_added)

    # Deterministic sorting of sets before iteration is mandatory for Python hash stability
    sorted_files_touched = sorted(list(all_files_touched))
    sorted_files_added = sorted(list(all_files_added))

    # Helper function for deterministic evaluations
    def _is_noise_file(filepath: str) -> bool:
        for ext in noise_extensions:
            if filepath.endswith(ext):
                return True
        for directory in noise_directories:
            if filepath.startswith(directory) or filepath.startswith(f"/{directory}"):
                return True
        return False

    def _is_config_file(filepath: str) -> bool:
        filename = filepath.split('/')[-1]
        return filename in structural_config_filenames
        
    def _is_in_vendor(filepath: str) -> bool:
        for vendor in vendor_directories:
            if filepath.startswith(vendor) or filepath.startswith(f"/{vendor}"):
                return True
        return False

    added_non_vendor_files = len([f for f in sorted_files_added if not _is_in_vendor(f)])
    actual_deletion_ratio = (total_deletions / total_insertions) if total_insertions > 0 else 0.0

    # Surface ALL evaluated inputs and configurations for complete transparency
    raw_signals = {
        "commits_count": len(cluster.commits),
        "total_insertions": total_insertions,
        "total_deletions": total_deletions,
        "total_renames": total_renames,
        "total_files_touched": len(sorted_files_touched),
        "added_non_vendor_files": added_non_vendor_files,
        "actual_deletion_ratio": actual_deletion_ratio,
        # Configurations injected for this run
        "cfg_feature_burst_insertion_threshold": feature_burst_insertion_threshold,
        "cfg_feature_burst_min_commits": feature_burst_min_commits,
        "cfg_structural_rename_threshold": structural_rename_threshold,
        "cfg_refactor_deletion_ratio": refactor_deletion_ratio
    }

    # 2. EVALUATION PIPELINE (Strict Priority Order & Short-Circuiting)

    # ---------------------------------------------------------
    # Rule 1: NOISE ONLY (`noise_only`)
    # ---------------------------------------------------------
    if sorted_files_touched and all(_is_noise_file(f) for f in sorted_files_touched):
        return ClassificationPayload(
            primary_classification="noise_only",
            confidence_score=1.0,  # Absolute certainty if all files perfectly match noise paths
            raw_signals=raw_signals
        )

    # ---------------------------------------------------------
    # Rule 2: STRUCTURAL CHANGE (`structural_change`)
    # ---------------------------------------------------------
    if total_renames >= structural_rename_threshold or any(_is_config_file(f) for f in sorted_files_touched):
        config_match = any(_is_config_file(f) for f in sorted_files_touched)
        
        # Scaling constant: 1.0 (100%) if explicit config file matched.
        # Otherwise scales from [0.0 - 1.0] linearly based on (actual_renames / threshold).
        score = 1.0 if config_match else min(1.0, total_renames / max(1, structural_rename_threshold))
        
        return ClassificationPayload(
            primary_classification="structural_change",
            confidence_score=score,
            raw_signals=raw_signals
        )

    # ---------------------------------------------------------
    # Rule 3: FEATURE BURST (`feature_burst`)
    # ---------------------------------------------------------
    if (len(cluster.commits) >= feature_burst_min_commits and
        added_non_vendor_files > 0 and
        total_insertions > total_deletions and
        total_insertions >= feature_burst_insertion_threshold):
        
        # Scaling constant: Base of 0.5 for crossing threshold, + 0.5 linearly scaling 
        # up to exactly double the threshold. e.g. Threshold 100 -> 100 insertions = 0.5, 200 insertions = 1.0.
        overage_ratio = (total_insertions - feature_burst_insertion_threshold) / max(1, feature_burst_insertion_threshold)
        scaled_score = 0.5 + (0.5 * min(1.0, overage_ratio))
        
        return ClassificationPayload(
            primary_classification="feature_burst",
            confidence_score=scaled_score,
            raw_signals=raw_signals
        )

    # ---------------------------------------------------------
    # Rule 4: REFACTOR CLUSTER (`refactor_cluster`)
    # ---------------------------------------------------------
    if total_insertions > 0 and actual_deletion_ratio >= refactor_deletion_ratio:
        # Scaling constant: Base of 0.7 for crossing the refactor threshold, + 0.3 scaling up to a 1.0 deletion ratio.
        # Ex: Threshold 0.5 -> 0.5 ratio = 0.7, 1.0 ratio = 1.0.
        clamped_ratio = min(1.0, actual_deletion_ratio)
        ratio_span = 1.0 - refactor_deletion_ratio + 0.001
        score = 0.7 + (0.3 * (clamped_ratio - refactor_deletion_ratio) / ratio_span)
        
        return ClassificationPayload(
            primary_classification="refactor_cluster",
            confidence_score=min(1.0, score),
            raw_signals=raw_signals
        )

    # ---------------------------------------------------------
    # FALLBACK: UNKNOWN
    # ---------------------------------------------------------
    return ClassificationPayload(
        primary_classification="unknown",
        confidence_score=0.1,  # Baseline 0.1 for missing all specific heuristics
        raw_signals=raw_signals
    )
