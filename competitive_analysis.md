# Competitive Analysis

## 1. gitwatch
*   **What they do better:** Utter simplicity. It's a lightweight bash script hooking directly into `inotifywait`. It's battle-tested for syncing personal dotfiles.
*   **What they cannot do at all:** Semantic grouping or intelligence. It creates a massive, noisy log of every single save (`CTRL+S`) with meaningless commit messages, destroying the usefulness of the branch history.
*   **Reason to switch:** A developer wants to maintain a readable, bisectable Git history while still getting the safety net of automated backups.

## 2. git-cliff (and similar changelog generators)
*   **What they do better:** Highly customizable templating. They excel at parsing Conventional Commits (`feat:`, `fix:`) into beautiful, release-ready Markdown files using regex and external configuration.
*   **What they cannot do at all:** Auto-commit or run continuously in the background. They are purely post-processing tools triggered manually or in CI. Furthermore, they fail completely if developers don't strictly adhere to their expected commit message conventions.
*   **Reason to switch:** A developer wants documentation generated *without* being forced to manually write structural/conventional commit messages locally.

## 3. GitHub Actions (Cloud Changelog Generators)
*   **What they do better:** Integration with the ecosystem. They can seamlessly link Pull Requests, Issues, and author profiles into the generated changelog because they have full access to the GitHub API.
*   **What they cannot do at all:** Local-first, private development. They require pushing code to Microsoft servers. They cannot analyze or profile the purely local, pre-pushed iteration cycles of a developer working offline or on a highly restricted corporate network.
*   **Reason to switch:** A developer works in a restricted environment (or on an airplane), refuses to rely on cloud vendor lock-in, and wants architectural churn insights generated instantly on their local machine before pushing.
