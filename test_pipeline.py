import asyncio
import time
from app.nodes.file_discovery_node import FileMetadata, FolderScopePolicy
from app.nodes.classification_node import ClassifiedFile, FileCategory
from app.nodes.duplicate_detection_node import DuplicateDetectionOutput
from app.nodes.sensitive_detection_node import sensitive_detection_node
from app.nodes.optimization_planner_node import optimization_planner_node
from app.nodes.hitl_approval_node import HITLApprovalOutput
from app.nodes.execution_node import execution_node
from google.adk.agents.context import Context

async def test_pipeline():
    policy = FolderScopePolicy(
        allowed_paths=["C:/Users/divya/OneDrive/Desktop/Collection"],
        blocked_paths=[],
        safe_mode=True
    )
    
    file_metadata = FileMetadata(
        path="C:/Users/divya/OneDrive/Desktop/Collection/documents/SSN.jpg",
        size=67599,
        created_at=0,
        modified_at=0,
        last_modified=0,
        last_accessed=0,
        extension=".jpg",
        mime_type="image/jpeg",
        is_dir=False
    )
    
    input_data = DuplicateDetectionOutput(
        file_inventory=[file_metadata],
        folder_scope_policy=policy,
        classified_files=[
            ClassifiedFile(path=file_metadata.path, category=FileCategory.MISC, confidence=1.0, reasoning="")
        ],
        duplicate_groups=[],
        reasoning="",
        safe_mode=True,
        search_mode=False
    )
    
    class DummySession:
        id = "test_session_123"
        def __init__(self):
            self.id = "test_session_123"
            
    class DummyContext:
        def __init__(self):
            self.session = DummySession()
            self.resume_inputs = None
            
    ctx = DummyContext()
    
    # 1. Sensitive Detection
    sens_event = sensitive_detection_node(input_data, ctx)
    
    # 2. Planner
    plan_event = optimization_planner_node(sens_event.output, ctx)
    
    # 3. Execution Node
    exec_input = HITLApprovalOutput(
        action_plan=plan_event.output.action_plan,
        approved_actions=plan_event.output.action_plan.actions,
        is_approved=True,
        reasoning="",
        folder_scope_policy=policy,
        sensitive_files=sens_event.output.sensitive_files,
        dry_run=False
    )
    try:
        exec_event = execution_node(exec_input)
        print("Execution Logs:")
        for log in exec_event.output.execution_log:
            print(f"  {log.action_type} - {log.path}: {log.status} - {log.reasoning} - new_path={log.new_path}")
    except Exception as e:
        print("Execution failed:", e)
    
if __name__ == "__main__":
    asyncio.run(test_pipeline())
