"""
CursorCode AI - Context Pruning
Ranks project files by relevance to a prompt using TF-IDF-style scoring.
Prunes low-relevance files to fit within LLM token windows.
"""

import re
import math
import logging
from collections import Counter
from typing import Dict, List

logger = logging.getLogger("context_pruning")

# Approximate tokens per character for code
CHARS_PER_TOKEN = 4
DEFAULT_TOKEN_BUDGET = 12000  # Conservative token budget for context


def tokenize(text: str) -> List[str]:
    """Simple word tokenizer for code/text."""
    return re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', text.lower())


def compute_tf(tokens: List[str]) -> Dict[str, float]:
    """Term frequency."""
    counts = Counter(tokens)
    total = len(tokens) if tokens else 1
    return {t: c / total for t, c in counts.items()}


def compute_idf(documents: List[List[str]]) -> Dict[str, float]:
    """Inverse document frequency."""
    n_docs = len(documents)
    if n_docs == 0:
        return {}
    df = Counter()
    for doc_tokens in documents:
        unique = set(doc_tokens)
        for t in unique:
            df[t] += 1
    return {t: math.log(n_docs / (1 + count)) for t, count in df.items()}


def rank_files_by_relevance(
    files: Dict[str, str],
    prompt: str,
    max_files: int = 20,
) -> List[Dict]:
    """Rank project files by relevance to a prompt using TF-IDF similarity."""
    if not files or not prompt:
        return []

    prompt_tokens = tokenize(prompt)
    prompt_tf = compute_tf(prompt_tokens)

    # Build document collection
    file_entries = []
    all_doc_tokens = []
    for filename, content in files.items():
        if filename.startswith("_docs/"):
            continue
        tokens = tokenize(content) + tokenize(filename)
        file_entries.append({"filename": filename, "tokens": tokens, "length": len(content)})
        all_doc_tokens.append(tokens)

    if not file_entries:
        return []

    # Add prompt as a document for IDF
    all_doc_tokens.append(prompt_tokens)
    idf = compute_idf(all_doc_tokens)

    # Score each file
    scored = []
    for entry in file_entries:
        doc_tf = compute_tf(entry["tokens"])
        # Cosine-like similarity via shared terms
        score = 0.0
        for term in prompt_tf:
            if term in doc_tf:
                score += prompt_tf[term] * doc_tf[term] * idf.get(term, 1.0)

        # Boost for filename match
        filename_lower = entry["filename"].lower()
        for term in prompt_tokens:
            if term in filename_lower:
                score += 0.5

        scored.append({
            "filename": entry["filename"],
            "relevance_score": round(score, 4),
            "char_count": entry["length"],
            "estimated_tokens": entry["length"] // CHARS_PER_TOKEN,
        })

    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    return scored[:max_files]


def prune_context(
    files: Dict[str, str],
    prompt: str,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
) -> Dict:
    """Select files that fit within token budget, ranked by relevance."""
    ranked = rank_files_by_relevance(files, prompt, max_files=50)

    selected = []
    selected_files = {}
    tokens_used = 0

    for entry in ranked:
        if tokens_used + entry["estimated_tokens"] > token_budget:
            continue
        selected.append(entry)
        selected_files[entry["filename"]] = files[entry["filename"]]
        tokens_used += entry["estimated_tokens"]

    return {
        "selected_files": selected_files,
        "ranked_files": ranked,
        "files_selected": len(selected),
        "files_total": len(files),
        "tokens_used": tokens_used,
        "token_budget": token_budget,
    }
