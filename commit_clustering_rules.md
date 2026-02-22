# Deterministic Commit Clustering Specification

## 1. Definition

A **commit cluster** is an uninterrupted, chronological sequence of locally contiguous Git commits on a single branch that represent a cohesive session of work, bound together by proximity in time and an absence of explicit context switches (e.g., branching or tagging). It acts as the atomic unit of evaluation for downstream modules.

## 2. Default Clustering Strategy

*   **Primary Mechanism:** Inter-commit inactivity window (time elapsed between `commit[n]` and `commit[n+1]`).
*   **Default Inactivity Threshold:** `120` minutes (2 hours).
*   **Evaluation Mode:** Forward chronological (oldest to newest).

## 3. Cluster Boundary Rules (Hard Stops)

A cluster `C` currently containing commit `HEAD` MUST close immediately BEFORE adding a new `commit[x]` IF ANY of the following rules match:

*   **Rule A (Inactivity Timeout):** `IF (commit[x].timestamp - HEAD.timestamp) > 120_minutes`
*   **Rule B (Branch Change):** `IF commit[x].branch != HEAD.branch` (Note: in a linear history parse, this relies on merge nodes or reflogs if available locally. Otherwise, clustering is strictly partitioned per-branch).
*   **Rule C (Tag Creation):** `IF commit[x]` is the immediate parent of a Git Tag.
*   **Rule D (System Boundary):** `IF commit[x].author == "repopilot-daemon"` (Commits created by the tool itself immediately seal the previous cluster).

## 4. Overflow and Edge Cases

*   **Single Massive Commit:** Placed into a cluster of size `1`.
*   **Extremely Long-Running Active Development (e.g., 5 hours of commits every 10 mins):** The cluster grows indefinitely until the `120_minute` threshold or a different Hard Stop (Rule B, C, D) is hit. Time-boxing (e.g., forced splits every 4 hours) is NOT applied in v1 to preserve the "session" concept.
*   **Rebases and Force-Pushes:** Since RepoPilot reads the raw object database, overwritten history (dangling commits) is ignored. Clustering only operates on the currently reachable commit graph of the active branch.
*   **Generated or Vendor-only Commits:** Included blindly in the cluster sequence. Downstream classification rules (not the clustering engine) are responsible for ignoring vendor paths.

## 5. Determinism Guarantees

*   **Guarantee:** The identical `.git` object graph will always produce the exact same array of clusters, regardless of the host OS, runtime time of execution, or background daemon state.
*   **Allowed Inputs:**
    1.  Commit Hash (SHA-1)
    2.  Parent Hash(es)
    3.  Author Timestamp (Unix Epoch)
    4.  Git Branch/Tag references pointing to specific SHAs.
*   **Explicitly Forbidden Inputs:**
    1.  Absolute timestamps of the host machine running the analysis (e.g., `Date.now()`).
    2.  In-memory RAM state or previous daemon crash data.
    3.  User prompt input or configurations changed *after* the commits were originally authored (clustering assumes the `120_minute` threshold is a global constant constraint for historical parsing).

## 6. Output Contract

```json
{
  "cluster_id": "sha256(hash_of_first_commit + hash_of_last_commit)",
  "commits": [
    "a1b2c3d4",
    "e5f67g8h"
  ],
  "start_timestamp": 1678886400,
  "end_timestamp": 1678890000,
  "closure_reason": "INACTIVITY_TIMEOUT | TAG_CREATED | EXPLICIT_BOUNDARY | SYSTEM_COMMIT | HEAD"
}
```

## 7. Invariants

1.  A given commit SHA-1 MUST belong to exactly ONE cluster.
2.  A cluster MUST contain at least `1` valid commit.
3.  The `start_timestamp` of a cluster MUST be `<=` its `end_timestamp`.
4.  Commits within a single cluster MUST share a continuous parent-child lineage (ignoring merge commit complexities for a single-line branch).
5.  The clustering algorithm MUST NOT modify the `.git` directory under any circumstance (pure read-only).
6.  `cluster_id` generation MUST NOT rely on random sequence generators (UUIDv4); it must be derived from the bounding commit hashes.
