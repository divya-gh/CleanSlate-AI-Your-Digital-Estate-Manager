from datetime import datetime

from app.nodes.classification_node import ClassifiedFile, FileCategory
from app.nodes.duplicate_detection_node import DuplicateFileEntry, DuplicateGroup
from app.nodes.execution_node import execution_node
from app.nodes.file_discovery_node import FileMetadata, FolderScopePolicy
from app.nodes.hitl_approval_node import CleanupAction
from app.nodes.optimization_planner_node import (
    ActionPlan,
    OptimizationPlannerOutput,
    optimization_planner_node,
)
from app.nodes.sensitive_detection_node import (
    SensitiveDetectionOutput,
    SensitiveFileEntry,
)
from app.nodes.weekly_organizer_node import (
    WeeklyOrganizerInput,
    WeeklySummary,
    weekly_organizer_node,
)


def test_weekly_organizer_disabled() -> None:
    policy = FolderScopePolicy(allowed_paths=["/allowed"])
    node_input = WeeklyOrganizerInput(
        pubsub_event={"event": "weekly_trigger"},
        weekly_automation_enabled=False,
        folder_scope_policy=policy,
        dry_run=False,
    )
    event = weekly_organizer_node(node_input)
    assert event.actions.route is None

    summary = event.output
    assert isinstance(summary, WeeklySummary)
    assert summary.automation_ran is False
    assert (
        "Weekly automation disabled. No actions performed."
        in summary.human_readable_report
    )


def test_weekly_organizer_enabled_propagation() -> None:
    policy = FolderScopePolicy(allowed_paths=["/allowed"])
    node_input = WeeklyOrganizerInput(
        pubsub_event={"event": "weekly_trigger"},
        weekly_automation_enabled=True,
        folder_scope_policy=policy,
        dry_run=True,
        timestamp=datetime.utcnow(),
    )
    event = weekly_organizer_node(node_input)
    assert event.actions.route == "run"

    disc_input = event.output
    assert disc_input.folder_scope_policy.safe_mode is True
    assert disc_input.folder_scope_policy.allow_deletes is False
    assert disc_input.folder_scope_policy.allow_compress is False


def test_safe_mode_planning_and_execution(tmp_path) -> None:
    # Set up test directories
    allowed_dir = tmp_path / "allowed"
    blocked_dir = tmp_path / "blocked"
    allowed_dir.mkdir()
    blocked_dir.mkdir()

    # Create dummy files
    file_sensitive = allowed_dir / "sensitive.txt"
    file_sensitive.write_text("sensitive info")

    file_dup_primary = allowed_dir / "dup1.txt"
    file_dup_primary.write_text("duplicate content")

    file_dup_sec = allowed_dir / "dup2.txt"
    file_dup_sec.write_text("duplicate content")

    file_misc = allowed_dir / "misc.txt"
    file_misc.write_text("misc content")

    policy = FolderScopePolicy(
        allowed_paths=[str(allowed_dir)],
        blocked_paths=[str(blocked_dir)],
        safe_mode=True,
        allow_deletes=False,
        allow_compress=False,
        allow_archives=True,
        allow_moves=True,
    )

    # 1. Test OptimizationPlanner Safe Mode
    sensitive_entry = SensitiveFileEntry(
        path=str(file_sensitive),
        sensitive=True,
        sensitivity_type="SSN",
        confidence=1.0,
        reasoning="Contains SSN",
    )

    inventory = [
        FileMetadata(
            path=str(file_sensitive),
            size=len("sensitive info"),
            extension=".txt",
            last_modified=123.45,
            last_accessed=123.45,
        ),
        FileMetadata(
            path=str(file_dup_primary),
            size=len("duplicate content"),
            extension=".txt",
            last_modified=123.45,
            last_accessed=123.45,
        ),
        FileMetadata(
            path=str(file_dup_sec),
            size=len("duplicate content"),
            extension=".txt",
            last_modified=123.45,
            last_accessed=123.45,
        ),
        FileMetadata(
            path=str(file_misc),
            size=len("misc content"),
            extension=".txt",
            last_modified=123.45,
            last_accessed=123.45,
        ),
    ]

    classified_files = [
        ClassifiedFile(
            path=str(file_sensitive),
            category=FileCategory.MISC,
            confidence=1.0,
            reasoning="misc",
        ),
        ClassifiedFile(
            path=str(file_dup_primary),
            category=FileCategory.MISC,
            confidence=1.0,
            reasoning="misc",
        ),
        ClassifiedFile(
            path=str(file_dup_sec),
            category=FileCategory.MISC,
            confidence=1.0,
            reasoning="misc",
        ),
        ClassifiedFile(
            path=str(file_misc),
            category=FileCategory.MISC,
            confidence=1.0,
            reasoning="misc",
        ),
    ]

    duplicate_groups = [
        DuplicateGroup(
            group_id="group1",
            files=[
                DuplicateFileEntry(
                    path=str(file_dup_primary),
                    size=100,
                    hash="hash1",
                    similarity_score=1.0,
                ),
                DuplicateFileEntry(
                    path=str(file_dup_sec), size=100, hash="hash1", similarity_score=1.0
                ),
            ],
            reasoning="Exact hash match",
        )
    ]

    planner_input = SensitiveDetectionOutput(
        sensitive_files=[sensitive_entry],
        classified_files=classified_files,
        duplicate_groups=duplicate_groups,
        file_inventory=inventory,
        folder_scope_policy=policy,
        reasoning="sensitive checks done",
    )

    planner_event = optimization_planner_node(planner_input)
    assert planner_event.actions.route == "execute"

    plan_output = planner_event.output
    # Only 2 actions planned: sensitive -> Authenticated and non-primary duplicate -> WeeklyReview
    # No deletes, no archive of misc, no compress should be suggested
    assert len(plan_output.action_plan.actions) == 2
    actions_lookup = {act.path: act for act in plan_output.action_plan.actions}

    assert str(file_sensitive) in actions_lookup
    assert actions_lookup[str(file_sensitive)].action_type == "move"
    assert (
        "Sensitive file moved to Authenticated"
        in actions_lookup[str(file_sensitive)].reasoning
    )

    assert str(file_dup_sec) in actions_lookup
    assert actions_lookup[str(file_dup_sec)].action_type == "move"
    assert (
        "Duplicate file moved to WeeklyReview"
        in actions_lookup[str(file_dup_sec)].reasoning
    )

    # The primary duplicate (file_dup_primary) and misc file are untouched
    assert str(file_dup_primary) not in actions_lookup
    assert str(file_misc) not in actions_lookup

    # 2. Test ExecutionNode Safe Mode Guards
    exec_event = execution_node(plan_output)
    # Weekly Organizer is isolated and never connects to RollbackNode, so route should be None
    assert exec_event.actions.route is None

    exec_output = exec_event.output
    assert len(exec_output.execution_log) == 2

    # Verify destinations
    assert not file_sensitive.exists()
    assert (allowed_dir / "Authenticated" / "sensitive.txt").exists()

    assert not file_dup_sec.exists()
    assert (allowed_dir / "WeeklyReview" / "dup2.txt").exists()

    # Verify primary dup is still intact
    assert file_dup_primary.exists()


def test_safe_mode_execution_guards(tmp_path) -> None:
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()

    # Pre-existing occupier to trigger overwrite prevention
    occupied_dest = allowed_dir / "WeeklyReview" / "dup.txt"
    occupied_dest.parent.mkdir(parents=True, exist_ok=True)
    occupied_dest.write_text("pre-existing occupier")

    file_dup = allowed_dir / "dup.txt"
    file_dup.write_text("new duplicate content")

    policy = FolderScopePolicy(
        allowed_paths=[str(allowed_dir)],
        blocked_paths=[],
        safe_mode=True,
        allow_deletes=False,
        allow_compress=False,
    )

    # Propose delete action and move action that overwrites
    planner_output = OptimizationPlannerOutput(
        action_plan=ActionPlan(
            actions=[
                # Unsafe delete action that should be rejected by Executor Safe Mode
                CleanupAction(
                    path=str(file_dup),
                    action_type="delete",
                    reasoning="accidentally planned delete",
                    estimated_space_recovered=100,
                    safe_to_delete=True,
                    confidence=0.9,
                ),
                # Move action that lands on occupied path
                CleanupAction(
                    path=str(file_dup),
                    action_type="move",
                    reasoning="move duplicate",
                    estimated_space_recovered=0,
                    safe_to_delete=False,
                    confidence=0.9,
                ),
            ],
            estimated_recovery=100,
            dry_run=False,
        ),
        reasoning="",
        classified_files=[],
        duplicate_groups=[],
        file_inventory=[],
        folder_scope_policy=policy,
        sensitive_files=[],
    )

    exec_event = execution_node(planner_output)
    exec_output = exec_event.output

    assert len(exec_output.execution_log) == 2
    log_lookup = {entry.action_type: entry for entry in exec_output.execution_log}

    # Delete is rejected
    assert log_lookup["delete"].status == "failure"
    assert "prohibited in safe mode" in log_lookup["delete"].reasoning

    # Move is rejected due to overwrite prevention
    assert log_lookup["move"].status == "failure"
    assert "Overwrite prevention" in log_lookup["move"].reasoning
    assert file_dup.exists()
    assert occupied_dest.read_text() == "pre-existing occupier"
