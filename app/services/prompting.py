"""
Prompt templates and helpers for the QA pipeline.
Designed for extractive, source-grounded answers with inline citations.
"""

SYSTEM = (
    "You are a careful assistant for Australian cotton R&D. "
    "Answer ONLY from the provided source passages. "
    "Rules:\n"
    "1) If a claim comes from a passage, cite it inline using [S#] (e.g., [S1]).\n"
    "2) If multiple passages support a sentence, stack citations like [S1][S3].\n"
    "3) If a page is shown in the passage header, you may add it: [S2 p.14].\n"
    "4) Prefer concrete numbers, units, and years. Avoid vague language.\n"
    "5) If the sources are insufficient to answer, say: "
    "\"I don't know based on the provided sources.\" Do NOT guess.\n"
    "6) Keep the answer concise: one short paragraph or 3–6 bullets."
)

# The sources block should look like:
# [S1] <title> (<doc_id>, <year>, p.<page>): <snippet>
# [S2] ...
USER_TPL = (
    "Question:\n{question}\n\n"
    "Source Passages:\n{sources}\n"
    "\n"
    "Write the answer now. Follow the Rules and include inline [S#] citations."
)

def build_user_prompt(question: str, sources_block: str) -> str:
    """Render the user message with the question and a preformatted sources list."""
    return USER_TPL.format(question=question.strip(), sources=sources_block.strip())
