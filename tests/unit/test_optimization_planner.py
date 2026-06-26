from app.nodes.classification_node import ClassifiedFile, FileCategory
from app.nodes.duplicate_detection_node import DuplicateFileEntry, DuplicateGroup
from app.nodes.file_discovery_node import FileMetadata, FolderScopePolicy
from app.nodes.optimization_planner_node import optimization_planner_node
from app.nodes.sensitive_detection_node import (
    SensitiveDetectionOutput,
    SensitiveFileEntry,
)


def test_optimization_planner() -> None:
    # 1. Setup metadata
    policy = FolderScopePolicy(
        allowed_paths=["/allowed"],
        blocked_paths=["/allowed/blocked"],
    )

    file_dup1 = FileMetadata(
        path="/allowed/dup1.txt",
        size=1000,
        extension=".txt",
        last_modified=0.0,
        last_accessed=0.0,
    )
    file_dup2 = FileMetadata(
        path="/allowed/dup2.txt",  # duplicate of dup1, safe to delete
        size=1000,
        extension=".txt",
        last_modified=0.0,
        last_accessed=0.0,
    )
    file_sensitive = FileMetadata(
        path="/allowed/sensitive.pdf",  # sensitive duplicate copy, NOT safe to delete
        size=2000,
        extension=".pdf",
        last_modified=0.0,
        last_accessed=0.0,
    )
    file_sensitive_dup = FileMetadata(
        path="/allowed/sensitive_copy.pdf",  # sensitive duplicate copy, NOT safe to delete
        size=2000,
        extension=".pdf",
        last_modified=0.0,
        last_accessed=0.0,
    )
    file_compress = FileMetadata(
        path="/allowed/compress.log",  # large log, older than 14 days, compress
        size=2 * 1024 * 1024,
        extension=".log",
        last_modified=0.0,
        last_accessed=0.0,
    )
    file_blocked = FileMetadata(
        path="/allowed/blocked/file.txt",  # blocked path
        size=5000,
        extension=".txt",
        last_modified=0.0,
        last_accessed=0.0,
    )

    # Classifications
    classified = [
        ClassifiedFile(
            path=file_dup1.path,
            category=FileCategory.MISC,
            confidence=0.9,
            reasoning="",
        ),
        ClassifiedFile(
            path=file_dup2.path,
            category=FileCategory.MISC,
            confidence=0.9,
            reasoning="",
        ),
        ClassifiedFile(
            path=file_sensitive.path,
            category=FileCategory.TAX,
            confidence=0.9,
            reasoning="",
        ),
        ClassifiedFile(
            path=file_sensitive_dup.path,
            category=FileCategory.TAX,
            confidence=0.9,
            reasoning="",
        ),
        ClassifiedFile(
            path=file_compress.path,
            category=FileCategory.MISC,
            confidence=0.9,
            reasoning="",
        ),
        ClassifiedFile(
            path=file_blocked.path,
            category=FileCategory.MISC,
            confidence=0.9,
            reasoning="",
        ),
    ]

    # Duplicate Groups
    dup_groups = [
        DuplicateGroup(
            group_id="group_1",
            files=[
                DuplicateFileEntry(
                    path=file_dup1.path, size=1000, hash="h1", similarity_score=1.0
                ),
                DuplicateFileEntry(
                    path=file_dup2.path, size=1000, hash="h1", similarity_score=1.0
                ),
            ],
            reasoning="Exact hash match",
        ),
        DuplicateGroup(
            group_id="group_2",
            files=[
                DuplicateFileEntry(
                    path=file_sensitive.path, size=2000, hash="h2", similarity_score=1.0
                ),
                DuplicateFileEntry(
                    path=file_sensitive_dup.path,
                    size=2000,
                    hash="h2",
                    similarity_score=1.0,
                ),
            ],
            reasoning="Exact hash match",
        ),
    ]

    # Sensitivity Check Results
    sensitive_results = [
        SensitiveFileEntry(
            path=file_dup1.path,
            sensitive=False,
            sensitivity_type="none",
            confidence=1.0,
            reasoning="",
        ),
        SensitiveFileEntry(
            path=file_dup2.path,
            sensitive=False,
            sensitivity_type="none",
            confidence=1.0,
            reasoning="",
        ),
        SensitiveFileEntry(
            path=file_sensitive.path,
            sensitive=True,
            sensitivity_type="tax",
            confidence=0.95,
            reasoning="",
        ),
        SensitiveFileEntry(
            path=file_sensitive_dup.path,
            sensitive=True,
            sensitivity_type="tax",
            confidence=0.95,
            reasoning="",
        ),
        SensitiveFileEntry(
            path=file_compress.path,
            sensitive=False,
            sensitivity_type="none",
            confidence=1.0,
            reasoning="",
        ),
        SensitiveFileEntry(
            path=file_blocked.path,
            sensitive=False,
            sensitivity_type="none",
            confidence=1.0,
            reasoning="",
        ),
    ]

    node_input = SensitiveDetectionOutput(
        sensitive_files=sensitive_results,
        classified_files=classified,
        duplicate_groups=dup_groups,
        file_inventory=[
            file_dup1,
            file_dup2,
            file_sensitive,
            file_sensitive_dup,
            file_compress,
            file_blocked,
        ],
        folder_scope_policy=policy,
        reasoning="",
    )

    # Execute Node
    output = optimization_planner_node(node_input).output

    # Assertions
    plan = output.action_plan
    assert plan.dry_run is True

    # Check proposed actions
    actions_lookup = {action.path: action for action in plan.actions}

    # file_dup2 must be scheduled for delete (it is safe to delete)
    assert file_dup2.path in actions_lookup
    assert actions_lookup[file_dup2.path].action_type == "delete"
    assert actions_lookup[file_dup2.path].safe_to_delete is True
    assert actions_lookup[file_dup2.path].confidence == 0.95

    # sensitive duplicates must NOT be scheduled for delete (they are sensitive)
    assert file_sensitive_dup.path not in actions_lookup

    # file_compress must be scheduled for compress
    assert file_compress.path in actions_lookup
    assert actions_lookup[file_compress.path].action_type == "compress"
    assert actions_lookup[file_compress.path].safe_to_delete is False
    assert actions_lookup[file_compress.path].estimated_space_recovered > 0

    # file_blocked must NOT be scheduled for any action
    assert file_blocked.path not in actions_lookup
