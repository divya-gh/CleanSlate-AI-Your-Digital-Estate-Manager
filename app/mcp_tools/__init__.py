from app.mcp_tools.compress_files import compress_files
from app.mcp_tools.compute_hash import compute_hash
from app.mcp_tools.create_folder import create_folder
from app.mcp_tools.delete_file import delete_file
from app.mcp_tools.list_files import list_files
from app.mcp_tools.move_file import move_file
from app.mcp_tools.move_to_authenticated_folder import move_to_authenticated_folder
from app.mcp_tools.read_file_metadata import read_file_metadata
from app.mcp_tools.read_log import read_log
from app.mcp_tools.write_log import write_log

TOOLS = {
    "list_files": list_files,
    "read_file_metadata": read_file_metadata,
    "compute_hash": compute_hash,
    "move_file": move_file,
    "delete_file": delete_file,
    "create_folder": create_folder,
    "compress_files": compress_files,
    "write_log": write_log,
    "read_log": read_log,
    "move_to_authenticated_folder": move_to_authenticated_folder,
}
