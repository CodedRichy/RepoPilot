# Execution Pipeline

## 1. Event Flow (Step-by-Step)

1.  **File System Event:** A file modification, creation, or deletion occurs in a watched repository.
2.  **Debounce Reset:** The `File System Event Watcher` receives the raw OS event, filters out ignored paths (e.g., `.git/`, `node_modules/`), and resets the `Inactivity Timer` for that specific repository.
3.  **Inactivity Timeout:** The `Inactivity Timer` for a repository reaches `0` (e.g., after 5 minutes of no filtered events).
4.  **Lock Acquisition:** The `Git Operator` attempts to acquire a virtual application-level mutex for the repository to prevent concurrent operations.
5.  **Git Status Check:** `Git Operator` runs `git status --porcelain`.
    *   If no changes are staged or working directory clean: Release lock, exit pipeline.
    *   If changes exist: Proceed to commit.
6.  **Auto-Commit:** `Git Operator` stages all tracked/untracked valid files (`git add -A`) and creates a deterministic commit (`git commit -m "auto: inactive since [timestamp]"`).
7.  **History Analysis Analysis:** The `History Analyzer` reads the updated `.git` object database to classify the newly added commit(s) (e.g., `feature_burst`, `noise_only`).
8.  **Policy Evaluation:** The state and classification are passed to the `Documentation Regeneration Policy` (Memory-only rule evaluation).
9.  **Doc Regeneration:** If the policy triggers doc regeneration, the `Documentation Synthesizer` writes the new markdown files to disk.
10. **Doc Auto-Commit:** If documentation was generated, `Git Operator` commits the docs immediately using squashing or a separate commit (based on Anti-Churn rules).
11. **Lock Release:** Mutex is released. Pipeline awaits next FS event.

## 2. State Storage

*   **Ephemeral State (In-Memory of Daemon):**
    *   `Inactivity Timers`: Per-repository countdowns dictating when to trigger auto-commits.
    *   `Active Mutexes`: Locks preventing overlapping Git operations on the same repo.
    *   `Recent Commit Classifications`: Cached classifications of the latest few commits to evaluate doc regeneration rules quickly.
*   **Persistent State (Disk - SQLite/JSON):**
    *   `Tracked Repositories`: List of absolute paths currently being watched.
    *   `Last Doc Regeneration Timestamps`: When each documentation file (e.g., `CHANGELOG.md`) was last generated for a given repo.
*   **Source of Truth (Disk - `.git` Directory):**
    *   The raw commits, file churn stats, and actual source code diffs. The system derives its intelligence purely from the `git` object database.

## 3. Failure Isolation Per Repo

*   **Process Architecture:** The daemon runs a core event loop that dispatches work to isolated thread pools or child processes (workers) per repository logic path.
*   **Exception Catching:** If a repository throws an exception (e.g., OOM during history analysis, or an unexpected `.git/index.lock` collision), the worker thread catches it, logs the error, and gracefully exits. 
*   **State Reset:** Upon a caught exception, the specific repository's `Inactivity Timer` is paused, and its `Mutex` is forcibly released.
*   **Containment:** Because each repository has its own independent debouncer, mutex, and subprocess/thread, a panic in `Repo A` (e.g., parsing a malformed commit) has absolutely zero impact on the event stream or timeout pipeline of `Repo B`.
