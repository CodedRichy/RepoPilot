# Agent Sandbox API Contract

This document defines the strict functions that an autonomous LLM agent is permitted to call when interacting with the RepoPilot engine. The goal is to enforce safety boundaries while allowing the agent enough access to analyze the repository history and regenerate documentation.

## 1. Allowed Tools (Functions)

### `get_repo_status`
*   **Purpose:** Retrieves the current file watch status and time until the next auto-commit.
*   **Input JSON:** `{ "repo_path": "string" }`
*   **Output JSON:** `{ "is_watching": boolean, "uncommitted_files": int, "next_commit_in_seconds": int }`

### `analyze_git_history`
*   **Purpose:** Fetches a purely read-only, structured view of the recent Git history.
*   **Input JSON:** `{ "repo_path": "string", "since_days_ago": int, "limit": int }`
*   **Output JSON:** `{ "commits": [ { "hash": "string", "message": "string", "classification": "string", "files_touched": ["string"] } ] }`

### `get_churn_metrics`
*   **Purpose:** Fetches the pre-calculated architectural churn data over a specific time window.
*   **Input JSON:** `{ "repo_path": "string", "time_window": "string (e.g., '7d', '1m')" }`
*   **Output JSON:** `{ "most_active_modules": [ { "path": "string", "commit_count": int } ] }`

### `trigger_doc_regeneration`
*   **Purpose:** Forces the engine to evaluate the current state and regenerate/commit documentation *if* the internal policy allows it.
*   **Input JSON:** `{ "repo_path": "string", "doc_types": ["string"] }`
*   **Output JSON:** `{ "success": boolean, "docs_regenerated": ["string"], "reason_skipped": "string (optional)" }`

## 2. Guardrails & Restrictions

1.  **No Arbitrary Git Execution:** The agent CANNOT run arbitrary commands like `git reset --hard`, `git push`, or `git rebase`. It can only read history or politely ask the engine to regenerate docs.
2.  **No File System Writes:** The agent NEVER writes to the file system directly. It cannot emit markdown strings to be written via standard I/O. It can only call `trigger_doc_regeneration`, and the *engine* (which has strict internal rules and memory-based diffing) handles the disk rewrite and squashing.
3.  **Path Traversal Protection:** Every API call requires a `repo_path`. The engine MUST validate that this path is within the explicitly configured allowed list of repositories in the `repopilot.toml` file. Any request for an unregistered path immediately returns an `AccessDenied` error.
4.  **Rate Limiting:** To prevent the LLM from getting stuck in an aggressive loop, API calls mapping to active computations (e.g., `trigger_doc_regeneration`, `analyze_git_history`) are rate-limited per minute.
