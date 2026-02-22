from pydantic import BaseModel


class ScanRequest(BaseModel):
    content: str
    content_type: str = "text"  # "text" or "url"


class OverlapItem(BaseModel):
    title: str | None
    url: str | None
    snippet: str
    provider: str
    author_name: str | None
    relevance_score: float


class PersonOverlap(BaseModel):
    name: str | None
    email: str | None
    overlap_count: int
    providers: list[str]


class ScanResponse(BaseModel):
    overlaps: list[OverlapItem]
    people: list[PersonOverlap]
    draft_message: str
    summary: str
