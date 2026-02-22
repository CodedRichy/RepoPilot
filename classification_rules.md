# Deterministic Change Classification Engine

This document defines the heuristic rules for classifying Git commit clusters into discrete categories without relying on Machine Learning or LLMs.

## 1. Structural Change (`structural_change`)

**Definition:** Significant architectural shifts, dependency updates, or repository reorganizations.

*   **Signals Used:**
    *   File rename/move operations extracted from Git diff statuses (`R` status).
    *   Modifications to root-level configuration files (e.g., `package.json`, `Cargo.toml`, `docker-compose.yml`, `tsconfig.json`).
    *   Ratio of total files touched to total lines changed (many files, few lines per file often indicates a structural renaming).
*   **Thresholds:**
    *   `> 5` files renamed or moved in a single cluster.
    *   **OR** modifications detected in known configuration files.
    *   **OR** `> 20` files touched where `(insertions + deletions) / files < 10` lines per file.
*   **False Positives to Watch Out For:** 
    *   Running an automated code formatter (e.g., Prettier, Black) across the repository, which touches many files with low lines-per-file churn. (Mitigation: check for pure whitespace diffs if possible).
    *   Mass automated Find & Replace of a single variable name.

## 2. Refactor Cluster (`refactor_cluster`)

**Definition:** Improvements to existing code structure without adding significant net-new functionality.

*   **Signals Used:**
    *   Insertion-to-Deletion ratio.
    *   Absence of new file creations (`A` status).
    *   Conventional Commit prefixes (if present: `refactor:`, `chore:`, `cleanup:`).
*   **Thresholds:**
    *   `Lines Deleted >= Lines Inserted * 0.8` (high deletion ratio or near 1:1 replacement).
    *   **AND** `New Files Created == 0`.
    *   **AND** `Total Files Touched <= 15` (to differentiate from a repository-wide structural change).
*   **False Positives to Watch Out For:**
    *   Completely deleting a deprecated feature (technically a feature removal, not a refactor, though the impact is similar).
    *   Swapping out a major library dependency where the new implementation requires roughly the same amount of code as the old one.

## 3. Feature Burst (`feature_burst`)

**Definition:** Active development of new capabilities, marked by new files and net-positive code growth.

*   **Signals Used:**
    *   Creation of net-new source files (`A` status in `src/`, `lib/`, `app/` directories).
    *   Net-positive line churn (significantly more insertions than deletions).
    *   Presence of test files added alongside source files (e.g., `*_test.py` or `*.spec.ts`).
*   **Thresholds:**
    *   `Insertions > Deletions * 3` (substantial code growth).
    *   **AND** `> 0` new source files created.
    *   **AND** `Total Insertions > 50` (filters out trivial additions).
*   **False Positives to Watch Out For:**
    *   Checking in auto-generated build artifacts (e.g., `dist/bundle.js`) or bulk vendor files. (Mitigation: strictly ignore known build/vendor directories).
    *   Updating massive machine-generated lockfiles (e.g., `package-lock.json`, `Cargo.lock`).

## 4. Noise Only (`noise_only`)

**Definition:** Trivial modifications that do not impact the execution logic of the software.

*   **Signals Used:**
    *   File extensions (e.g., `.md`, `.txt`).
    *   Directory paths (e.g., `docs/`, `.github/workflows/` depending on context, `.husky/`).
    *   Total absolute churn (very low line counts).
*   **Thresholds:**
    *   `100%` of modified files have matching extensions (`.md`, `.txt`) or are in documentation directories.
    *   **OR** `(Insertions + Deletions) < 5` lines overall in the entire cluster.
*   **False Positives to Watch Out For:**
    *   A critical 1-line bug fix (e.g., changing a `<` to a `<=`). (Mitigation: Do not classify low churn as noise if the commit message contains `fix`, `bug`, or `hotfix`).
    *   A 1-line version bump in a package registry file, which triggers deployment pipelines.
