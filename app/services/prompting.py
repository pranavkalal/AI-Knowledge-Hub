"""
Prompt templates and helpers for the QA pipeline.
Keeps system/user strings in one place so different LLM providers can share them.
"""

SYSTEM = (
    "You are an assistant for Australian cotton R&D. "
    "Answer concisely using only the provided sources. "
    "Cite with [S#] where # matches the source id. If unsure, say you don't know. "
    "Prefer specific years, figures, and units."
)

USER_TPL = "Question:\n{question}\n\nSources:\n{sources}\n"

def build_user_prompt(question: str, sources_block: str) -> str:
    """Render the user message with the question and a preformatted sources list."""
    return USER_TPL.format(question=question.strip(), sources=sources_block)
