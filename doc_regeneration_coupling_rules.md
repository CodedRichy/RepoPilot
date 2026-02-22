# Documentation Regeneration Policy: Coupling Rules

The Documentation Regeneration Policy serves as an independent rule engine that ingests the output of the Change Classification Engine.

## Dependency Principles

The Policy is **strictly downstream** of the Classification Engine. It is forbidden from recalculating Git metrics.

### 1. Allowed Inputs
The policy MAY ONLY base its regeneration decisions on the following top-level event fields:
*   `primary_classification` (e.g., `"feature_burst"`, `"refactor_cluster"`)
*   `confidence_score` (Float `0.0` - `1.0`)
*   Environmental State (e.g., `time_since_last_regen`, `is_active_branch_main`)

### 2. Forbidden Inputs
The policy MUST NOT access or base decisions on:
*   The `raw_signals` object.
*   Specific file paths, file extensions, or Git metadata (e.g., it cannot ask "Was `.md` changed?").

### 3. Examples
*   **Correct Dependency:**
    `IF primary_classification == 'structural_change' AND confidence_score > 0.8 THEN Regenerate_Architecture()`
    *(Valid because it trusts the classification engine implicitly).*
*   **Invalid Dependency:**
    `IF primary_classification == 'refactor_cluster' AND raw_signals.files_renamed > 2 THEN Regenerate_Architecture()`
    *(Invalid because the policy is attempting to reinterpret the raw `files_renamed` signal to second-guess the classification engine. If renames were important, the engine should have classified it as structural).*
