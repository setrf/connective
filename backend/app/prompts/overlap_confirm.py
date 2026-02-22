def build_overlap_confirm_prompt(
    source_title: str | None,
    source_provider: str | None,
    source_author: str | None,
    source_preview: str,
    target_title: str | None,
    target_provider: str | None,
    target_author: str | None,
    target_preview: str,
) -> list[dict]:
    """Build prompt for LLM to confirm whether two documents overlap."""
    return [
        {
            "role": "system",
            "content": (
                "You are an overlap detection assistant. Given two documents, determine if they "
                "represent overlapping or closely related work.\n\n"
                "Return ONLY a JSON object with:\n"
                '- "confidence": a float 0.0–1.0 indicating overlap likelihood\n'
                '- "summary": a 1–2 sentence description of the overlap\n\n'
                "Confidence guidelines:\n"
                "- 0.8–1.0: Clear overlap — same topic, similar goals, or duplicated effort\n"
                "- 0.5–0.7: Related — shared themes but different angles or scope\n"
                "- 0.0–0.4: Different work — no meaningful overlap\n\n"
                "Example response:\n"
                '{"confidence": 0.85, "summary": "Both documents discuss implementing user '
                'authentication with OAuth2, with similar design decisions around token refresh."}'
            ),
        },
        {
            "role": "user",
            "content": (
                f"Document A:\n"
                f"  Title: {source_title or 'Untitled'}\n"
                f"  Source: {source_provider or 'unknown'}\n"
                f"  Author: {source_author or 'Unknown'}\n"
                f"  Preview:\n{source_preview[:1000]}\n\n"
                f"Document B:\n"
                f"  Title: {target_title or 'Untitled'}\n"
                f"  Source: {target_provider or 'unknown'}\n"
                f"  Author: {target_author or 'Unknown'}\n"
                f"  Preview:\n{target_preview[:1000]}"
            ),
        },
    ]
