# Successful v1 of RepoPilot

## 1. Exact behaviors that must work (The "Happy Path")
*   The developer types `repopilot watch` in a project directory and forgets about it.
*   The developer writes code for 3 hours, switching between UI files and Database schemas.
*   The developer walks away to get lunch (5 minutes of inactivity).
*   RepoPilot instantly auto-staged, commits the working directory as `auto: inactive...`, analyzes the 3 hours of churn, recognizes a `feature_burst`, and generates an updated `CHANGELOG.md` file reflecting the new files added.
*   When the developer returns, their workspace is completely clean (`git status`), their work is safely backed up in the local `HEAD`, and `CHANGELOG.md` shows a summary of their morning.

## 2. Explicitly Out of Scope
*   **No Centralized Server / Multi-Player:** v1 does not coordinate across a team. It operates solely on the local machine's `.git` folder. No web app, no syncing, no SaaS dashboards.
*   **No Auto-Pushing:** The tool will *never* run `git push`. It handles the local staging and commit area exclusively.
*   **No Machine Learning / LLM Generation:** The v1 classification engine relies entirely on deterministic heuristics (churn ratios, file extensions, new file additions). Generating flowery summaries is not supported in the core engine.
*   **No Handling of Merge Conflicts:** If the active branch is in a conflict state, RepoPilot will halt operations and wait for the user to resolve it manually.

## 3. Demo Scenario that Proves Value
*   **The Setup:** A developer clone an old, massive open-source repository they've never seen before.
*   **The Action:** They run `repopilot docs --all` across the whole repo without the daemon running.
*   **The Value Prop:** In less than 3 seconds (deterministically traversing the local history), RepoPilot outputs an `ARCHITECTURE_CHURN.md` file that perfectly highlights the 3 modules that change the most often together over the last 5 years. The developer instantly understands the structural hotspots of the legacy codebase without running a single line of code or querying GitHub.
