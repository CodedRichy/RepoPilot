# RepoPilot Architecture v1

## 1. CLI & Daemon Controller
*   **Responsibility:** Acts as the entrypoint. Parses user commands (`add <path>`, `watch`, `docs`), manages the lifecycle of the background daemon, and orchestrates the initialization of the other modules.
*   **Critical Failure Mode:** Daemon initialization races resulting in multiple overlapping background processes, leading to duplicate simultaneous commit attempts on the same repo.

## 2. Registry & State Manager
*   **Responsibility:** Maintains the local SQLite or JSON configuration file detailing which repositories are being watched, their specific inactivity thresholds, and global ignore patterns.
*   **Critical Failure Mode:** State file corruption due to an ungraceful shutdown during a write operation, causing the daemon to "forget" all tracked repositories upon restart.

## 3. File System Event Watcher
*   **Responsibility:** Hooks into OS-level APIs (e.g., `inotify`, FSEvents) to recursively monitor filesystem activity across all registered repositories, filtering out noise (like `.git/` internal changes).
*   **Critical Failure Mode:** Operating system file descriptor exhaustion (e.g., `ENOSPC`) when attempting to watch massive monorepos or un-ignored `node_modules` folders.

## 4. Inactivity Scheduler
*   **Responsibility:** Consumes raw events from the FS Watcher, maintains distinct debounce timers for each repository, and dispatches a "ready to commit" signal when a repo hits the configured idle threshold.
*   **Critical Failure Mode:** Timer race conditions where IDE auto-saves align perfectly with the debounce reset, causing an auto-commit to trigger mid-refactor while the user is actively typing.

## 5. Git Operator
*   **Responsibility:** Executes raw, local Git commands (`status`, `add`, `commit`) idempotently. It generates deterministic commit messages (e.g., `auto: inactive since [timestamp]`) and handles staging.
*   **Critical Failure Mode:** Fatal crashes or corrupted partial commits caused by `.git/index.lock` collisions if the user manually runs a Git command at the exact millisecond the automation fires.

## 6. History Analyzer
*   **Responsibility:** Parses the raw `.git` object database locally to extract chronological commit graphs, file churn metrics, and diffs without relying on any external APIs.
*   **Critical Failure Mode:** Unbounded memory allocation (OOM errors) when attempting to traverse and hold the AST/graph of massive legacy repositories with hundreds of thousands of commits in memory.

## 7. Documentation Synthesizer
*   **Responsibility:** Takes the structured data from the History Analyzer and projects it into formatted Markdown documentation files (e.g., `ACTIVITY.md`, `ARCHITECTURE_CHURN.md`).
*   **Critical Failure Mode:** Non-deterministic output (e.g., generating slightly different Markdown diffs based on random hash-map iteration orders), which violates the determinism constraint and litters the repo with redundant documentation commits.
