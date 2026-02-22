import dataclasses
from typing import Sequence

from repopilot.core.models import ClassificationPayload

"""
RepoPilot Core: Document Regeneration Policy

### Policy Layer Contract
- **Responsibility:** Deterministically decides WHICH documentation files to regenerate based purely on classification signals and explicit temporal state.
- **NOT** Responsible For: Formatting Markdown strings, rewriting disk files, evaluating raw Git commits, or interpreting system boundaries.
- **Allowed Inputs:** `ClassificationPayload` structures, elapsed time thresholds, active branch context.
- **Output Guarantee:** Outputs a Boolean array determining precisely which doc types should be regenerated. These decisions are definitive and final for the current evaluation cycle.
"""

@dataclasses.dataclass(frozen=True)
class PolicyDecision:
    """The final deterministic outcome dictating downstream generation workflows."""
    regenerate_changelog: bool
    regenerate_architecture_churn: bool
    regenerate_development_metrics: bool
    reason_skipped: str  # For debugging / metrics if regeneration was skipped

def evaluate_regeneration_policy(
    classification_result: ClassificationPayload,
    seconds_since_last_changelog_regen: int,
    seconds_since_last_architecture_regen: int,
    seconds_since_last_metrics_regen: int,
    active_branch: str,
    allowed_branches: Sequence[str],
    is_system_commit: bool,
    changelog_threshold_seconds: int,
    architecture_threshold_seconds: int,
    metrics_threshold_seconds: int
) -> PolicyDecision:
    """
    Evaluates system state against the strict Documentation Regeneration logic gates,
    short-circuiting early if anti-churn or branch protection safeguards are tripped.

    Args:
        classification_result: The exact payload produced by the `classify_cluster` engine.
        seconds_since_last_X_regen: Temporal state relative to the moment of evaluation.
        active_branch: The current linear branch being parsed.
        allowed_branches: Branches authorized for automated documentation writes (e.g. main).
        is_system_commit: Whether the triggering commit was authored by RepoPilot itself.
        *_threshold_seconds: Configured limits for temporal triggers (injected, no defaults).

    Returns:
        PolicyDecision: The definitive flags indicating which generators to invoke.
    """
    
    # ==========================================================================
    # PHASE 1: ANTI-CHURN SAFEGUARDS (Short-Circuit Evaluation)
    # ==========================================================================
    # These checks form an ordered cascade of hard blockers. If ANY condition
    # is tripped, we immediately return a fully-blocked PolicyDecision.
    # Order matters: we check the most critical invariants first.
    
    # -------------------------------------------------------------------------
    # Rule A: SYSTEM LOOP PREVENTION
    # -------------------------------------------------------------------------
    # WHY BLOCKED: If the triggering commit was authored by RepoPilot itself
    # (e.g., a previous doc regeneration commit), allowing regeneration would
    # create an infinite feedback loop: regen -> commit -> trigger -> regen.
    # This is the most critical anti-churn safeguard and must be checked first.
    if is_system_commit:
        return PolicyDecision(
            regenerate_changelog=False,
            regenerate_architecture_churn=False,
            regenerate_development_metrics=False,
            reason_skipped="SYSTEM_AUTHOR"
        )
    
    # -------------------------------------------------------------------------
    # Rule B: BRANCH AUTHORIZATION ENFORCEMENT
    # -------------------------------------------------------------------------
    # WHY BLOCKED: Documentation regeneration is only permitted on explicitly
    # allowed branches (typically 'main' or 'master'). Regenerating docs on
    # feature branches would pollute branch history and create merge conflicts.
    # This check ensures docs are only updated on stable, canonical branches.
    if active_branch not in allowed_branches:
        return PolicyDecision(
            regenerate_changelog=False,
            regenerate_architecture_churn=False,
            regenerate_development_metrics=False,
            reason_skipped="UNAUTHORIZED_BRANCH"
        )
    
    # -------------------------------------------------------------------------
    # Rule C: NOISE SUPPRESSION
    # -------------------------------------------------------------------------
    # WHY BLOCKED: If the classification engine determined that ALL changes in
    # the cluster are noise (lock files, IDE configs, generated assets, etc.),
    # regenerating documentation would add no semantic value. This prevents
    # doc churn from non-meaningful repository activity.
    if classification_result.primary_classification == "noise_only":
        return PolicyDecision(
            regenerate_changelog=False,
            regenerate_architecture_churn=False,
            regenerate_development_metrics=False,
            reason_skipped="NOISE_SUPPRESSION"
        )
    
    # ==========================================================================
    # PHASE 2: DOCUMENT-SPECIFIC TRIGGER EVALUATION
    # ==========================================================================
    # Each document type has independent triggers. A document regenerates if
    # EITHER a semantic trigger (classification-based) OR a temporal trigger
    # (time-based threshold) is satisfied. These are evaluated independently
    # to allow granular control over which docs are updated.
    
    regen_changelog = False
    regen_arch = False
    regen_metrics = False
    
    # Extract classification for repeated use (no mutation, purely referential)
    classification = classification_result.primary_classification
    
    # -------------------------------------------------------------------------
    # CHANGELOG.md Logic Gate
    # -------------------------------------------------------------------------
    # SEMANTIC TRIGGERS:
    #   - "feature_burst": New features warrant changelog entries to document
    #     user-facing changes and maintain release notes accuracy.
    #   - "structural_change": Architectural shifts (renames, config changes)
    #     should be reflected in the changelog for visibility.
    # TEMPORAL TRIGGER:
    #   - If sufficient time has elapsed since last regeneration, refresh the
    #     changelog to capture any accumulated changes regardless of type.
    
    semantic_changelog_trigger = classification in ("feature_burst", "structural_change")
    temporal_changelog_trigger = seconds_since_last_changelog_regen >= changelog_threshold_seconds
    
    if semantic_changelog_trigger or temporal_changelog_trigger:
        regen_changelog = True
    
    # -------------------------------------------------------------------------
    # ARCHITECTURE_CHURN.md Logic Gate
    # -------------------------------------------------------------------------
    # SEMANTIC TRIGGER:
    #   - "structural_change": Only structural changes (file renames, config
    #     modifications) warrant architecture documentation updates. Feature
    #     additions or refactors don't affect architectural documentation.
    # TEMPORAL TRIGGER:
    #   - Periodic refresh ensures architecture docs don't become stale even
    #     if no single cluster triggered the semantic condition.
    
    semantic_arch_trigger = classification == "structural_change"
    temporal_arch_trigger = seconds_since_last_architecture_regen >= architecture_threshold_seconds
    
    if semantic_arch_trigger or temporal_arch_trigger:
        regen_arch = True
    
    # -------------------------------------------------------------------------
    # DEVELOPMENT_METRICS.md Logic Gate
    # -------------------------------------------------------------------------
    # NO SEMANTIC TRIGGER:
    #   - Metrics documentation is classification-agnostic. It aggregates
    #     quantitative data (commit counts, churn rates, contributor stats)
    #     regardless of the semantic nature of the changes.
    # TEMPORAL TRIGGER ONLY:
    #   - Metrics are regenerated purely on a time-based schedule to provide
    #     periodic snapshots of development velocity and patterns.
    
    temporal_metrics_trigger = seconds_since_last_metrics_regen >= metrics_threshold_seconds
    
    if temporal_metrics_trigger:
        regen_metrics = True
    
    # ==========================================================================
    # PHASE 3: DECISION CONSOLIDATION
    # ==========================================================================
    # Compile all evaluated flags into the final PolicyDecision. If no document
    # types were triggered, emit a diagnostic reason for observability/debugging.
    
    # Determine skip reason if all regenerations are blocked at the trigger level
    # (as opposed to being blocked by anti-churn safeguards in Phase 1).
    if not regen_changelog and not regen_arch and not regen_metrics:
        # No triggers fired. Construct a diagnostic reason based on the
        # classification that passed anti-churn but didn't match any trigger.
        # This aids debugging by distinguishing "blocked by safeguard" from
        # "no trigger condition met".
        reason = f"NO_TRIGGERS_FIRED:classification={classification}"
    else:
        # At least one document will be regenerated; no skip reason needed.
        reason = ""
    
    return PolicyDecision(
        regenerate_changelog=regen_changelog,
        regenerate_architecture_churn=regen_arch,
        regenerate_development_metrics=regen_metrics,
        reason_skipped=reason
    )
