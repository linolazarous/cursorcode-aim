"""
CursorCode AI - AI Security
Prompt validation and code sanitization.
"""

import re
import logging

logger = logging.getLogger("ai_security")

class AISecurity:
    BLOCKED_PATTERNS = [
        r"rm -rf", r"shutdown", r"format c:", r"drop database",
        r"delete from", r"sudo",
    ]

    @staticmethod
    def validate_prompt(prompt: str) -> bool:
        for pattern in AISecurity.BLOCKED_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                logger.warning(f"Blocked malicious prompt pattern: {pattern}")
                return False
        return True

    @staticmethod
    def sanitize_code(code: str) -> str:
        for pattern in AISecurity.BLOCKED_PATTERNS:
            code = re.sub(pattern, "", code, flags=re.IGNORECASE)
        return code
