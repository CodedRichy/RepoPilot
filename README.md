# RepoPilot

## Overview

RepoPilot is a professional, local-first Git companion designed to automate the tedious aspects of repository management. It follows a "set and forget" philosophy, running as a background daemon that monitors your project for inactivity and automatically handles staging, committing, and documentation regeneration.

Unlike centralized services, RepoPilot operates exclusively on your local `.git` directory, requiring no external APIs or cloud dependencies. It uses a deterministic heuristic engine to classify your work (e.g., distinguishing between a "noise" change and a "feature burst") and ensures your project's `CHANGELOG.md` and architectural metrics are always up-to-date.

## Features

*   **Zero-Config Automated Commits:** Automatically stages and commits your working directory after a configurable idle threshold (e.g., 5 minutes of inactivity).
*   **Deterministic Change Classification:** Categorizes commits into `noise_only`, `structural_change`, `feature_burst`, or `refactor_cluster` using computable heuristics rather than brittle prefixes or LLMs.
*   **Intelligent Documentation Synthesis:** Automatically updates `CHANGELOG.md` and generates architectural hotspot analysis (`ARCHITECTURE_CHURN.md`) based on historical file churn.
*   **Local History Analysis:** Analyzes the Git object database locally to identify code hotspots and module coupling without hitting GitHub/GitLab APIs.
*   **Failsafe Git Operations:** Uses a lock-based mutex system to prevent collisions between the automation engine and manual `git` commands.
*   **Daemon Architecture:** Runs as a lightweight background process with per-repository isolation, ensuring a failure in one watched repo doesn't impact others.

## Architecture

RepoPilot is built as a modular pipeline with strict separation between data retrieval and logical decision-making:

*   **CLI & Daemon Controller:** The user entry point for managing the background process and orchestrating module initialization.
*   **File System Event Watcher:** Monitors OS-level events (inotify/FSEvents) to track repository activity while filtering noise.
*   **Inactivity Scheduler:** Manages debounce timers and dispatches "ready to commit" signals.
*   **History Analyzer:** Performs read-only traversal of the local Git graph to extract churn metrics.
*   **Deterministic Classification Engine:** Evaluates the nature of change clusters based on file extensions, rename counts, and insertion/deletion ratios.
*   **Documentation Synthesizer:** Projects structured history data into formatted Markdown files.
*   **Git Operator:** Executes atomic, idempotent Git commands (`add`, `commit`) with collision protection.

## Tech Stack

*   **Core Language:** Python 3.x
*   **System Interface:** OS-level Filesystem APIs (inotify, FSEvents)
*   **Data Source:** Local `.git` Object Database
*   **Persistence:** SQLite/JSON (State & Registry Management)
*   **Documentation:** Semantic Markdown

## Repository Structure

```
/repopilot
  /core
    /classification.py  → Deterministic heuristic engine logic
    /clustering.py      → Logic for grouping commits by time/topic
    /engine.py          → Central execution pipeline orchestrator
    /git_reader.py      → Read-only Git history traversal boundary
    /git_writer.py      → Mutative Git command execution layer
    /models.py          → Core domain entities (CommitNodes, Clusters)
    /policy.py          → Documentation regeneration rules
/docs                   → Specification and design documents (Root .md files)
```

## Installation

> [!NOTE]
> RepoPilot is currently in the **Architecture & Skeleton** phase. The core logic handles are defined, and implementation of the functional TODOs is ongoing.

### Prerequisites
*   Python 3.10+
*   Git CLI installed and in your PATH

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/CodedRichy/RepoPilot.git
   cd RepoPilot
   ```
2. Create a virtual environment and install in editable mode:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Or `venv\Scripts\activate` on Windows
   pip install -e .
   ```

## Usage

### Start Watching a Repository
Run the daemon to monitor the current directory for inactivity:
```bash
repopilot watch --path . --idle-timeout 5m
```

### Check Daemon Status
View all currently tracked repositories and pending commit timers:
```bash
repopilot status
```

### Force Documentation Regeneration
Manually trigger a full analysis and documentation update:
```bash
repopilot docs --all
```

## Configuration

RepoPilot can be configured via a global config file or CLI flags:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `DEFAULT_IDLE_TIMEOUT` | Time of silence before an auto-commit triggers | `5m` |
| `NOISE_EXTENSIONS` | File types ignored by the classification engine | `.md, .txt, .gitignore` |
| `VENDOR_DIRECTORIES` | Directories excluded from feature-burst analysis | `node_modules/, vendor/` |

## Development

Developers can contribute by implementing the functional "TODO" markers found within the `repopilot/core/` modules.

### Development Mode
Ensure you have installed the package in editable mode (`pip install -e .`) so changes to the source code are reflected immediately in the `repopilot` command.

## Testing

The project uses a specification-first approach. Test suites (planned for `pytest`) will focus on:
*   Deterministic classification accuracy against synthetic Git logs.
*   Mutex collision handling during concurrent Git operations.
*   Timer accuracy under high FS event churn.

To run future tests:
```bash
pytest
```

## Roadmap

*   [ ] **Phase 1 (Skeleton):** Finalize component contracts and domain models (Current).
*   [ ] **Phase 2 (Logic Implementation):** Implement Git object database traversal and inactivity debouncers.
*   [ ] **Phase 3 (Stability):** Refine mutex locks and handle complex Git states (merge conflicts, detached HEAD).
*   [ ] **Phase 4 (Docs+):** Expand documentation synthesis to include `DEPENDENCY_DRIFT.md`.

## Contributing

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/amazing-feature`).
3. Commit your changes following the [Commit Rules](commit_clustering_rules.md).
4. Push to the branch.
5. Open a Pull Request.

## License

No license specified. Please contact the repository owner for usage permissions.
