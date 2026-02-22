def build_rag_prompt(query: str, chunks: list[dict]) -> list[dict]:
    """Build the RAG prompt with retrieved context chunks."""
    context_parts = []
    for i, chunk in enumerate(chunks):
        meta = chunk.get("metadata", {})
        source = f"[{i + 1}] [{meta.get('provider', 'unknown')}] {meta.get('title', 'Untitled')}"
        if meta.get("author_name"):
            source += f" (by {meta['author_name']})"
        if meta.get("url"):
            source += f"\nURL: {meta['url']}"
        context_parts.append(f"{source}\n{chunk['content']}")

    context = "\n\n---\n\n".join(context_parts)

    return [
        {
            "role": "system",
            "content": (
                "You are Connective, a work knowledge assistant. You answer questions about "
                "a user's work context by referencing evidence from their connected tools "
                "(Slack, GitHub, Google Drive).\n\n"
                "Rules:\n"
                "- Answer based ONLY on the provided context. If the context doesn't contain "
                "enough information, say so.\n"
                "- Use inline citations like [1], [2] to reference specific sources.\n"
                "- Every factual claim must have at least one citation.\n"
                "- Be concise but thorough.\n"
                "- If multiple sources discuss the same topic, synthesize them and cite all relevant ones.\n"
                "- Mention the people involved when relevant.\n"
            ),
        },
        {
            "role": "user",
            "content": f"Context:\n\n{context}\n\n---\n\nQuestion: {query}",
        },
    ]
