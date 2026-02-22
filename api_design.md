# RepoPilot Library API Design

## 1. Public Function Signatures

The library exposes pure functions that take a repository path (and optional constraints) and return structured data. All file IO (except reading `.git`) and standard output are delegated to the caller.

```python
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

class RepoPilot:
    def __init__(self, repo_path: Path):
        """Initializes the analyzer for a specific local repository."""
        self.repo_path = repo_path

    def get_commit_history(self, since: Optional[datetime] = None, until: Optional[datetime] = None) -> List['CommitData']:
        """Extracts the chronological commit history."""
        pass

    def analyze_architecture_churn(self) -> Dict[str, 'ModuleChurnData']:
        """Analyzes which modules change together and their modification frequency."""
        pass

    def generate_changelog_data(self, from_tag: str, to_tag: str = "HEAD") -> 'ChangelogData':
        """Structures commit data into features, fixes, and breaking changes."""
        pass

    def extract_development_metrics(self) -> 'DevelopmentMetrics':
        """Calculates metrics like code velocity, active days, and contributor stats."""
        pass
```

## 2. Returned Data Schema

All data returned by the library uses strongly-typed Pydantic models, or standard Python `dataclasses`.

```python
from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime

@dataclass
class CommitData:
    hash: str
    author: str
    timestamp: datetime
    message_subject: str
    message_body: str
    files_changed: List[str]
    insertions: int
    deletions: int

@dataclass
class ModuleChurnData:
    module_path: str
    total_commits: int
    last_modified: datetime
    complexity_score: float # e.g., based on churn vs LOC

@dataclass
class ChangelogCategory:
    features: List[CommitData]
    fixes: List[CommitData]
    breaking_changes: List[CommitData]
    others: List[CommitData]

@dataclass
class ChangelogData:
    version_range: str
    categories: ChangelogCategory

@dataclass
class DevelopmentMetrics:
    total_commits: int
    most_active_day: str
    average_commits_per_week: float
    top_modified_files: List[str]
```

## 3. CLI Layer vs Library Responsibilities

### The Library (`repopilot.core`):
*   **Pure Data Processing:** Parses `.git` binary objects, calculates metrics, and structures the commit graph.
*   **Zero Side Effects:** Never calls `print()`, `sys.exit()`, or `open(..., 'w')`.
*   **Agnostic:** Does not know about Markdown formatting, GitHub, or terminal constraints.
*   **Error Handling:** Raises specific, catchable exceptions (e.g., `InvalidRepoError`, `GitHistoryError`).

### The CLI Layer (`repopilot.cli`):
*   **User Interaction:** Parses `sys.argv` (using `click`, `typer`, or `argparse`).
*   **Configuration:** Reads `repopilot.toml` or environment variables and passes them to the library.
*   **Formatting:** Takes the structured `dataclasses` from the library and renders them into Markdown templates.
*   **Side Effects:** Handles all `print()` statements (spinners, progress bars, success messages) and executes the actual disk writes (e.g., `with open("CHANGELOG.md", "w") as f:`).
*   **Graceful Exit:** Catches library exceptions and translates them into user-friendly terminal error messages with non-zero exit codes.
