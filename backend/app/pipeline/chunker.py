import tiktoken


def chunk_text(
    text: str,
    max_tokens: int = 512,
    overlap_tokens: int = 64,
    model: str = "cl100k_base",
) -> list[dict]:
    """Recursive character splitting by token count.

    Returns list of {content, token_count, chunk_index}.
    """
    enc = tiktoken.get_encoding(model)
    tokens = enc.encode(text)

    if len(tokens) <= max_tokens:
        return [{"content": text, "token_count": len(tokens), "chunk_index": 0}]

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = enc.decode(chunk_tokens)

        chunks.append({
            "content": chunk_text,
            "token_count": len(chunk_tokens),
            "chunk_index": chunk_index,
        })

        chunk_index += 1
        start += max_tokens - overlap_tokens

        if start >= len(tokens):
            break

    return chunks
