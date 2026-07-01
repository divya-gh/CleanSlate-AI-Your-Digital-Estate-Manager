import asyncio
from pydantic import BaseModel
from app.nodes.execution_node import execution_node, ExecutionInput, ExecutionAction
from app.nodes.file_discovery_node import FolderScopePolicy
from google.adk.agents.context import Context
from unittest.mock import MagicMock
import os
import shutil

async def main():
    os.makedirs("test_sensitive", exist_ok=True)
    with open("test_sensitive/ssn.txt", "w") as f:
        f.write("sensitive data")
        
    policy = FolderScopePolicy(
        allowed_paths=[os.path.abspath("test_sensitive")],
        blocked_paths=[],
        safe_mode=False,
        dry_run=False,
        pin_hash="a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3" # hash for "1234"
    )
    
    node_input = ExecutionInput(
        policy=policy,
        approved_actions=[ExecutionAction(path=os.path.abspath("test_sensitive/ssn.txt"), action_type="move")],
        sensitive_files=[os.path.abspath("test_sensitive/ssn.txt")],
        all_discovered_files=[os.path.abspath("test_sensitive/ssn.txt")]
    )
    
    ctx = MagicMock(spec=Context)
    
    try:
        async for result in execution_node(ctx, node_input):
            print("Execution node completed")
            break
    except Exception as e:
        print(f"Error: {e}")
        
if __name__ == "__main__":
    asyncio.run(main())
