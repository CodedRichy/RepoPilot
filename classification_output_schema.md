# Change Classification Engine: Output Contract

## JSON Schema Example

The engine produces the following strict JSON schema for every analyzed commit cluster:

```json
{
  "cluster_id": "a1b2c3d4-e5f6-7g8h",
  "commits_analyzed": 5,
  "primary_classification": "feature_burst",
  "confidence_score": 0.85,
  "raw_signals": {
    "total_insertions": 420,
    "total_deletions": 15,
    "files_added": 3,
    "files_renamed": 0,
    "files_touched": 7,
    "config_modified": false
  }
}
```

## Confidence Computation (v1)

In v1, the `confidence_score` is a deterministic threshold-distance calculation, strictly bounded between `0.0` and `1.0`.

*   **Logic:** For rules triggered by numeric thresholds (e.g., `feature_burst` requires `Insertions > Deletions * 3` and `Insertions > 50`), confidence scales linearly above the minimum threshold up to a defined saturation point.
*   **Example:** If `feature_burst` triggers at `50` insertions, a cluster with exactly `51` insertions gets a confidence of `0.51`. A cluster with `500+` insertions hits the saturation cap and gets `1.0`.
*   **Absolute Matches:** Rules with boolean triggers (e.g., `noise_only` where 100% of files are `.md`, or `structural_change` where `package.json` was edited) immediately receive a hardcoded confidence of `1.0`.
