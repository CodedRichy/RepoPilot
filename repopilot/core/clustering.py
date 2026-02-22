import hashlib
from typing import Sequence, List

from repopilot.core.models import CommitNode, ClusterGroup

"""
RepoPilot Core: Deterministic Commit Clustering Engine

This module guarantees deterministic parsing of a sequence of contiguous CommitNodes
into distinct, non-overlapping ClusterGroups based on predefined heuristic boundaries.

Guarantees & Constraints:
- Side-effect free: Operates strictly on in-memory sequences of CommitNodes.
- Deterministic: An identical sequence of CommitNodes will always yield identical ClusterGroups.
- Idempotent: Can be run an infinite number of times yielding the exact same clusters.
- Time-agnostic: Absolute time constraints are provided via injection, never `time.now()`.
- Isolated: This module NEVER accesses the filesystem or reads from Git via subprocesses.
- Linear: Branch boundaries must be resolved upstream. This engine evaluates a strictly linear sequence.
"""

# Stable Closure Reasons
CLOSURE_REASON_SYSTEM_COMMIT = "SYSTEM_COMMIT"
CLOSURE_REASON_INACTIVITY_TIMEOUT = "INACTIVITY_TIMEOUT"
CLOSURE_REASON_HEAD = "HEAD"

def _generate_cluster_id(first_commit_hash: str, last_commit_hash: str) -> str:
    """
    Deterministically calculates a cluster ID based solely on bounding hashes.
    
    Formula: sha256(first_hash + last_hash)
    """
    hash_input = f"{first_commit_hash}{last_commit_hash}".encode('utf-8')
    return hashlib.sha256(hash_input).hexdigest()

def cluster_commits(
    commits: Sequence[CommitNode],
    inactivity_threshold_seconds: int,
    system_authors: Sequence[str]
) -> List[ClusterGroup]:
    """
    Iterates sequentially through a time-sorted sequence of CommitNodes and partitions 
    them into ClusterGroups bounded by hard-stop inactivity limits and explicit system boundaries.
    
    Args:
        commits: A chronologically ordered, linear sequence of raw CommitNodes.
        inactivity_threshold_seconds: The allowable time gap between consecutive 
                                      commits before a new cluster is forced. REQUIRED.
        system_authors: List of author names that represent system actions (e.g., daemon commits) 
                        that force an immediate and independent cluster boundary. REQUIRED.
                                      
    Returns:
        List[ClusterGroup]: A sequence of distinct, non-overlapping clusters.
    """
    if not commits:
        return []

    # Enforce or verify input ordering (oldest to newest)
    sorted_commits = sorted(commits, key=lambda c: c.timestamp)

    clusters: List[ClusterGroup] = []
    current_cluster_commits: List[CommitNode] = []
    
    previous_commit = None
    
    for current_commit in sorted_commits:
        if previous_commit is None:
            # First commit of the entire array initializes the first cluster
            current_cluster_commits.append(current_commit)
            previous_commit = current_commit
            continue
            
        # --- Rule Evaluations (Hard Stops) ---
        seal_cluster = False
        closure_reason = ""
        
        # Rule D: System Boundary
        # IF previous_commit author matches any injected system author, it forces a boundary.
        # This prevents clustering user commits together with system auto-commits.
        if previous_commit.author in system_authors:
            seal_cluster = True
            closure_reason = CLOSURE_REASON_SYSTEM_COMMIT
            
        # Rule A: Inactivity Timeout
        # Evaluated if no higher-priority boundary matched.
        # IF the time gap between the previous commit and the current one exceeds the threshold.
        elif not seal_cluster:
            time_delta = current_commit.timestamp - previous_commit.timestamp
            if time_delta.total_seconds() > inactivity_threshold_seconds:
                seal_cluster = True
                closure_reason = CLOSURE_REASON_INACTIVITY_TIMEOUT
        
        if seal_cluster:
            # A boundary condition was met. We must seal the accumulated cluster.
            first_hash = current_cluster_commits[0].hash
            last_hash = current_cluster_commits[-1].hash
            
            clusters.append(
                ClusterGroup(
                    cluster_id=_generate_cluster_id(first_hash, last_hash),
                    commits=current_cluster_commits,
                    start_timestamp=current_cluster_commits[0].timestamp,
                    end_timestamp=current_cluster_commits[-1].timestamp,
                    closure_reason=closure_reason
                )
            )
            
            # Start a new cluster with the current commit
            current_cluster_commits = [current_commit]
        else:
            # No boundary met. Accumulate the current commit into the ongoing cluster.
            current_cluster_commits.append(current_commit)
            
        previous_commit = current_commit
        
    # Flush the final open cluster segment
    if current_cluster_commits:
        first_hash = current_cluster_commits[0].hash
        last_hash = current_cluster_commits[-1].hash
        
        clusters.append(
            ClusterGroup(
                cluster_id=_generate_cluster_id(first_hash, last_hash),
                commits=current_cluster_commits,
                start_timestamp=current_cluster_commits[0].timestamp,
                end_timestamp=current_cluster_commits[-1].timestamp,
                closure_reason=CLOSURE_REASON_HEAD  # The final open cluster is inherently capped by HEAD
            )
        )
        
    return clusters
