# Deterministic Change Classification Engine

This document defines the heuristic rules for classifying Git commit clusters into discrete categories without relying on Machine Learning or LLMs.

## Classification Semantics

1.  **Exclusivity:** A commit cluster is assigned exactly ONE primary classification.
2.  **Strict Evaluation Order:** Rules are evaluated from highest priority to lowest priority.
3.  **Short-Circuiting:** The evaluation immediately halts upon the first rule that triggers a match.
4.  **Secondary Signals:** Metrics not triggering the primary classification (e.g., a documentation file touched during a massive refactor) may be recorded in the output schema but MUST NOT alter the primary classification decision.

## Priority Order

The engine evaluates commit clusters in the following top-down sequence:

1.  `noise_only`
2.  `structural_change`
3.  `feature_burst`
4.  `refactor_cluster`

**Why this order exists:**
*   **Noise First:** Trivial changes (like formatting or single-character typos in READMEs) should never be accidentally flagged as "Features" or "Refactors" just because they mathematically match a deletion ratio. They are immediately filtered out.
*   **Structure Before Features:** Large configuration shifts (like renaming the root `src/` directory to `app/`) will contain massive file churn and technically look like new code additions. We must catch configuration/renaming events before they are misclassified as `feature_bursts`.
*   **Features Before Refactors:** "Net-new code" (adding new capabilities) is prioritized over "Optimized code". If a developer adds a new module and cleans up an old one in the same cluster, the introduction of totally new capabilities is deemed more significant to the project's evolution.

## 1. Noise Only (`noise_only`)

**Definition:** Evaluated FIRST. Trivial or metadata-only modifications that do not impact the execution logic of the software. Excludes potential bug fixes.

*   **Executable Conditions:**
    *   `IF` ALL modified files match extensions: `[.md, .txt, .gitignore, .dockerignore]`
    *   `OR` ALL modified files exist strictly within directories: `[docs/, .github/, .vscode/]`
    *   `THEN` classify as `noise_only` AND short-circuit evaluation.

*   **Correct Classification Example:** A cluster that modifies `docs/api.md` and updates a typo in `README.md`.
*   **Deliberately Avoided Example:** A single-line change to `src/utils.js` changing `<` to `<=`. (Because the file extension `.js` and path `src/` are not in the approved noise lists, it fails the `noise_only` condition and falls through to the next rule).

## 2. Structural Change (`structural_change`)

**Definition:** Computable architectural shifts or repository reorganizations. Formatter noise is strictly mitigated.

*   **Signals Used (Computable Only):**
    *   Git status `R` (Renames).
    *   Absolute paths of configuration files.
*   **Threshold Constants:**
    *   `MIN_RENAMES = 5`
*   **Executable Conditions:**
    *   `IF` count of files with Git status `R` >= `MIN_RENAMES`
    *   `OR` ANY modified file exactly matches: `package.json`, `Cargo.toml`, `go.mod`, `docker-compose.yml`, `tsconfig.json`
    *   `THEN` classify as `structural_change` AND short-circuit.

*   **v1 Limitations:**
    *   Cannot detect "mass Find & Replace" operations reliably without AST parsing (removed from v1).
    *   Cannot definitively distinguish an automated formatter (Prettier/Black) touching 100 files from a human touching 100 files based purely on `git log` stats without calculating per-hunk whitespace diffs (removed from v1).

## 3. Feature Burst (`feature_burst`)

**Definition:** Sustained development of new capabilities extending over time or a sequence of commits, strictly ignoring generated/vendor artifacts.

*   **Signals Used:**
    *   Commit count within the cluster.
    *   Git status `A` (Added files).
    *   File path exclusion lists.
*   **Minimum Conditions:**
    *   `IF` cluster contains >= `3` distinct commits within a `24h` window
    *   `AND` count of files with Git status `A` > `0` (excluding paths matching `vendor/`, `node_modules/`, `dist/`, `build/`, `.min.js`)
    *   `AND` total insertions > total deletions in the cluster
    *   `THEN` classify as `feature_burst` AND short-circuit.

*   **False-Positive Avoided:** A single massive commit dumping 500 files into `vendor/`. Because the path matches the exclusion list, the `A` status count evaluates to 0, failing the condition and falling through to refactor/fallback.

## 4. Refactor Cluster (`refactor_cluster`)

**Definition:** The final fallback classification for a cluster that alters code but does not meet the strict thresholds for noise, structural shifts, or sustained feature bursts.

*   **Executable Conditions (Fallback):**
    *   `IF` execution reaches this rule (meaning it is NOT noise, NOT structural, and NOT a feature burst)
    *   `AND` total file deletions < total file modifications (to ensure it isn't purely a deprecation/deletion event)
    *   `THEN` classify as `refactor_cluster`.

*   **Why this rule must be last:**
    Refactoring is the "dark matter" of development—it is the modification of existing logic. Because a feature burst or a structural renaming *also* modifies existing logic, `refactor_cluster` must act as the default bucket for code churn that failed to trigger the highly specific, strictly threshold-driven signatures of the primary classifications. It explicitly ignores commit prefixes (e.g., `refactor:`) as developers frequently mislabel or omit them.
