# backend/ai_security.py

import re
from logs import logger


class AISecurity:

    BLOCKED_PATTERNS = [
        r"rm -rf",
        r"shutdown",
        r"format c:",
        r"drop database",
        r"delete from",
        r"sudo",
    ]

    @staticmethod
    def validate_prompt(prompt: str) -> bool:
        """
        Detect malicious prompts.
        """

        for pattern in AISecurity.BLOCKED_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                logger.warning(f"Blocked malicious prompt: {prompt}")
                return False

        return True


    @staticmethod
    def sanitize_code(code: str) -> str:
        """
        Remove dangerous commands.
        """

        for pattern in AISecurity.BLOCKED_PATTERNS:
            code = re.sub(pattern, "", code, flags=re.IGNORECASE)

        return code
