# Documentation Regeneration Policy

## 1. Default Regeneration Triggers
**Regenerate `CHANGELOG.md` IF:**
*   `time_since_last_regen >= 24h` AND `new_commits > 0`
*   OR `commit_type == 'release'` (tag created or version bumped)
*   OR `cluster_classification == 'feature_burst'`
*   OR `cluster_classification == 'structural_change'`

**Regenerate `ARCHITECTURE_CHURN.md` IF:**
*   `cluster_classification == 'structural_change'`
*   OR `time_since_last_regen >= 7d` AND `files_changed_in_src > 50`

**Regenerate `DEVELOPMENT_METRICS.md` IF:**
*   `time_since_last_regen >= 48h` AND `commits_analyzed > 10`

## 2. Explicit Skip Conditions (NO-OP)
**DO NOT Regenerate Any Docs IF:**
*   `cluster_classification == 'noise_only'`
*   OR `active_repo_branch != 'main'` (and `!= 'master'`)
*   OR `.repopilotignore` contains the currently active directory.
*   OR `commit_author == 'repopilot-daemon'` (Prevents infinite loops).
*   OR `system_idle_time < 5m` (Wait for the user to step away).

## 3. Anti-Churn Rules
**To prevent git history pollution with doc updates:**
*   **Rule A (Batching):** If multiple triggers fire within a `60m` window, coalesce them into a single regeneration event.
*   **Rule B (Diff Verification):** Before committing regenerated docs, run a purely memory-based diff. IF `new_doc_hash == old_doc_hash`, ABORT commit.
*   **Rule C (Squashing):** If the previous commit in the tree was ALSO an automated doc regeneration (`author == 'repopilot-daemon'`), use `git commit --amend` instead of creating a new commit node.
