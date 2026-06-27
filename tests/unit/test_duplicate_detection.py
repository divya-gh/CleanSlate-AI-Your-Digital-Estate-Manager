from app.nodes.classification_node import (
    ClassificationOutput,
    ClassifiedFile,
    FileCategory,
)
from app.nodes.duplicate_detection_node import duplicate_detection_node
from app.nodes.file_discovery_node import FileMetadata, FolderScopePolicy


def test_duplicate_detection_exact_and_near(tmp_path) -> None:
    # Set up folders
    allowed_dir = tmp_path / "allowed"
    blocked_dir = tmp_path / "blocked"
    allowed_dir.mkdir()
    blocked_dir.mkdir()

    # Create dummy files
    file1 = allowed_dir / "report_2026_v1.txt"
    file2 = allowed_dir / "report_2026_v2.txt"  # near duplicate of file1
    file3 = allowed_dir / "unique_doc.pdf"
    file4 = allowed_dir / "duplicate_copy1.log"
    file5 = allowed_dir / "duplicate_copy2.log"  # exact duplicate of file4
    file_blocked = blocked_dir / "duplicate_copy3.log"  # exact duplicate but blocked

    file1.write_text(
        "This is version one of the report for the capstone project. It contains some text."
    )
    # file2 has slightly different size and name, same extension, same parent folder
    file2.write_text(
        "This is version two of the report for the capstone project. It contains more text."
    )
    file3.write_text("Entirely different content and type.")
    file4.write_text("EXACT_HASH_CONTENT")
    file5.write_text("EXACT_HASH_CONTENT")
    file_blocked.write_text("EXACT_HASH_CONTENT")

    # Define metadata
    meta1 = FileMetadata(
        path=str(file1),
        size=file1.stat().st_size,
        extension=".txt",
        last_modified=file1.stat().st_mtime,
        last_accessed=file1.stat().st_atime,
    )
    meta2 = FileMetadata(
        path=str(file2),
        size=file2.stat().st_size,
        extension=".txt",
        last_modified=file2.stat().st_mtime,
        last_accessed=file2.stat().st_atime,
    )
    meta3 = FileMetadata(
        path=str(file3),
        size=file3.stat().st_size,
        extension=".pdf",
        last_modified=file3.stat().st_mtime,
        last_accessed=file3.stat().st_atime,
    )
    meta4 = FileMetadata(
        path=str(file4),
        size=file4.stat().st_size,
        extension=".log",
        last_modified=file4.stat().st_mtime,
        last_accessed=file4.stat().st_atime,
    )
    meta5 = FileMetadata(
        path=str(file5),
        size=file5.stat().st_size,
        extension=".log",
        last_modified=file5.stat().st_mtime,
        last_accessed=file5.stat().st_atime,
    )
    meta_blocked = FileMetadata(
        path=str(file_blocked),
        size=file_blocked.stat().st_size,
        extension=".log",
        last_modified=file_blocked.stat().st_mtime,
        last_accessed=file_blocked.stat().st_atime,
    )

    policy = FolderScopePolicy(
        allowed_paths=[str(allowed_dir)],
        blocked_paths=[str(blocked_dir)],
    )

    classified = [
        ClassifiedFile(
            path=meta1.path, category=FileCategory.MISC, confidence=0.8, reasoning=""
        ),
        ClassifiedFile(
            path=meta2.path, category=FileCategory.MISC, confidence=0.8, reasoning=""
        ),
        ClassifiedFile(
            path=meta3.path, category=FileCategory.MISC, confidence=0.8, reasoning=""
        ),
        ClassifiedFile(
            path=meta4.path, category=FileCategory.MISC, confidence=0.8, reasoning=""
        ),
        ClassifiedFile(
            path=meta5.path, category=FileCategory.MISC, confidence=0.8, reasoning=""
        ),
        ClassifiedFile(
            path=meta_blocked.path,
            category=FileCategory.MISC,
            confidence=0.8,
            reasoning="",
        ),
    ]

    node_input = ClassificationOutput(
        classified_files=classified,
        file_inventory=[meta1, meta2, meta3, meta4, meta5, meta_blocked],
        folder_scope_policy=policy,
        reasoning="Predecessor classification nodes run.",
    )

    event = duplicate_detection_node(node_input)
    output = event.output

    # Verify that:
    # 1. Exact duplicate group contains file4 and file5 (similarity 1.0)
    # 2. Near duplicate group contains file1 and file2 (similarity between 0.8 and 1.0)
    # 3. file_blocked is completely ignored and not included in any group because of policy
    assert len(output.duplicate_groups) >= 2

    exact_groups = [g for g in output.duplicate_groups if "Exact" in g.reasoning]
    near_groups = [g for g in output.duplicate_groups if "Near" in g.reasoning]

    assert len(exact_groups) == 1
    assert len(near_groups) == 1

    # Exact group check
    exact_paths = {entry.path for entry in exact_groups[0].files}
    assert str(file4) in exact_paths
    assert str(file5) in exact_paths
    assert str(file_blocked) not in exact_paths
    assert all(entry.similarity_score == 1.0 for entry in exact_groups[0].files)

    # Near group check
    near_paths = {entry.path for entry in near_groups[0].files}
    assert str(file1) in near_paths
    assert str(file2) in near_paths
    assert all(
        0.8 <= entry.similarity_score < 1.0
        for entry in near_groups[0].files
        if entry.path != str(file1)
    )
