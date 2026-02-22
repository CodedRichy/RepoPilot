# CLI Design

## Commands

### 1. `repopilot watch`
*   **Purpose:** Starts the background daemon to watch the current directory (or a specified path) and auto-commits on inactivity.
*   **Example Invocation:** `repopilot watch --path ./my-project --idle-timeout 5m`

### 2. `repopilot status`
*   **Purpose:** Prints the current status of the background daemon, including actively watched repositories and the time until the next scheduled auto-commit.
*   **Example Invocation:** `repopilot status`

### 3. `repopilot history`
*   **Purpose:** Analyzes the Git history and returns structured data (JSON or human-readable table) without modifying any files.
*   **Example Invocation:** `repopilot history --since "1 week ago" --format json`

### 4. `repopilot docs`
*   **Purpose:** Forces an immediate, synchronous regeneration of documentation (CHANGELOG, etc.) based on the latest `.git` state, bypassing the automated policy.
*   **Example Invocation:** `repopilot docs --all`

### 5. `repopilot config`
*   **Purpose:** Sets or retrieves global configuration values for the system (e.g., custom ignore patterns, default timeout).
*   **Example Invocation:** `repopilot config set default_idle_timeout 10m`
