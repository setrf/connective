def build_scan_prompt(content: str, chunks: list[dict]) -> list[dict]:
    """Build prompt for scan overlap analysis."""
    context_parts = []
    for i, chunk in enumerate(chunks):
        meta = chunk.get("metadata", {})
        source = f"[{meta.get('provider', 'unknown')}] {meta.get('title', 'Untitled')}"
        if meta.get("author_name"):
            source += f" by {meta['author_name']}"
        context_parts.append(f"- {source}: {chunk['content'][:200]}")

    context = "\n".join(context_parts)

    return [
        {
            "role": "system",
            "content": (
                "You are Connective, a work overlap detection assistant. "
                "Given a user's current work description and related evidence from their team's "
                "connected tools, you:\n"
                "1. Summarize the overlaps found\n"
                "2. Draft a friendly check-in message to the relevant people\n\n"
                "Format your response exactly as:\n"
                "SUMMARY: <1-3 sentence summary of overlaps found>\n"
                "DRAFT: <a friendly, casual message the user can send to their team, "
                "mentioning specific people and topics>"
            ),
        },
        {
            "role": "user",
            "content": (
                f"My current work:\n{content}\n\n"
                f"Related evidence from connected tools:\n{context}"
            ),
        },
    ]
