import os
import logging

logger = logging.getLogger("utils")

def safe_mkdir(path: str) -> None:
    try:
        os.makedirs(path, exist_ok=True)
    except Exception as e:
        logger.exception(f"Failed to create directory {path}: {e}")

def truncate_text(text: str, length: int = 2000) -> str:
    if not isinstance(text, str):
        text = str(text)
    return text[:length] if len(text) > length else text
