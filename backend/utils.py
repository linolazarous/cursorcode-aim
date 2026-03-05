"""
CursorCode AI - Utility Functions
"""

import os

def safe_mkdir(path: str):
    """Create a directory if it doesn't exist"""
    os.makedirs(path, exist_ok=True)

def truncate_text(text: str, length: int = 2000):
    """Return first N characters of a string"""
    if len(text) > length:
        return text[:length]
    return text
