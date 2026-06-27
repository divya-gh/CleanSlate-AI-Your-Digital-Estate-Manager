import os


def get_heading_from_filename(path: str) -> str:
    """Derive a clean title-cased heading from a file path without opening the file."""
    name = os.path.basename(path)
    name = os.path.splitext(name)[0]
    return name.replace("_", " ").replace("-", " ").title()
