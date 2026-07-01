import os
from app.config import set_policy_override
from app.nodes.file_discovery_node import FolderScopePolicy
from app.mcp_tools.utils import is_path_allowed_by_policy

policy = FolderScopePolicy(
    allowed_paths=["C:/Users/divya/OneDrive/Desktop/Collection"],
    blocked_paths=[],
    safe_mode=True
)
set_policy_override(policy.model_dump())

path = "C:/Users/divya/OneDrive/Desktop/Collection/Authenticated_Secure/_data_/SSN.jpg"
print("is allowed?", is_path_allowed_by_policy(path))
