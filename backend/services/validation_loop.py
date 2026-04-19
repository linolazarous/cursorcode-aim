"""
CursorCode AI - AI Validation Loop
Orchestrates: test generation -> execution -> debugging -> repeat until passing.
Max iterations to prevent infinite loops.
"""

import logging
from typing import Dict
from services.sandbox import run_sandboxed
from services.guardrails import validate_output
from services.ai import call_xai_api, parse_files_from_response
from core.config import XAI_API_KEY, FAST_REASONING_MODEL

logger = logging.getLogger("validation_loop")

MAX_ITERATIONS = 3

TEST_GEN_SYSTEM = """You are a QA engineer. Given application code, generate focused test code.
Output ONLY executable test code (no markdown, no explanations).
For Python: use pytest. For JavaScript: use simple assert statements.
The test file must be self-contained and runnable."""

DEBUG_SYSTEM = """You are an expert debugger. Given code and its test failure output,
fix the code so tests pass. Output ONLY the corrected code (no explanations).
Preserve the same filename format: ```filename:name.ext"""


async def run_validation_loop(
    code: str,
    filename: str,
    language: str = "python",
    max_iterations: int = MAX_ITERATIONS,
) -> Dict:
    """
    1. Validate code with guardrails
    2. Generate tests
    3. Execute tests
    4. If tests fail, debug and fix
    5. Repeat until pass or max iterations
    """
    iterations = []
    current_code = code

    # Step 0: Guardrails
    guardrail_result = validate_output(current_code, language)
    if not guardrail_result["passed"]:
        iterations.append({
            "step": "guardrails",
            "passed": False,
            "issues": guardrail_result["issues"],
        })
        # Use sanitized code
        current_code = guardrail_result["sanitized_code"]

    for i in range(max_iterations):
        iteration = {"iteration": i + 1, "steps": []}

        # Step 1: Generate tests
        test_prompt = f"Generate tests for this {language} code:\n\n```{filename}\n{current_code}\n```"
        test_code = await call_xai_api(test_prompt, FAST_REASONING_MODEL, TEST_GEN_SYSTEM)

        # Extract just the code from the response
        test_files = parse_files_from_response(test_code)
        if test_files:
            test_source = list(test_files.values())[0]
        else:
            # Try to extract raw code
            test_source = test_code.strip()
            if test_source.startswith("```"):
                lines = test_source.split('\n')
                test_source = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])

        iteration["steps"].append({"name": "test_generation", "generated": len(test_source) > 0})

        # Step 2: Execute tests
        exec_result = run_sandboxed(test_source, language)
        iteration["steps"].append({
            "name": "test_execution",
            "success": exec_result["success"],
            "output": exec_result.get("output", "")[:500],
            "error": exec_result.get("error", "")[:500],
        })

        if exec_result["success"]:
            iteration["passed"] = True
            iterations.append(iteration)
            return {
                "passed": True,
                "iterations": len(iterations),
                "final_code": current_code,
                "test_code": test_source,
                "details": iterations,
            }

        # Step 3: Debug and fix
        debug_prompt = (
            f"The following {language} code failed tests.\n\n"
            f"Code:\n```{filename}\n{current_code}\n```\n\n"
            f"Test code:\n```\n{test_source}\n```\n\n"
            f"Error output:\n{exec_result.get('error', '')}\n{exec_result.get('output', '')}\n\n"
            f"Fix the application code so the tests pass."
        )
        fixed_response = await call_xai_api(debug_prompt, FAST_REASONING_MODEL, DEBUG_SYSTEM)
        fixed_files = parse_files_from_response(fixed_response)

        if fixed_files:
            current_code = list(fixed_files.values())[0]
            iteration["steps"].append({"name": "debug_fix", "code_changed": True})
        else:
            iteration["steps"].append({"name": "debug_fix", "code_changed": False})

        iteration["passed"] = False
        iterations.append(iteration)

    return {
        "passed": False,
        "iterations": len(iterations),
        "final_code": current_code,
        "test_code": test_source if 'test_source' in dir() else "",
        "details": iterations,
        "message": f"Validation did not pass after {max_iterations} iterations",
    }
