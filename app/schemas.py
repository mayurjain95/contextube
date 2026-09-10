from pydantic import BaseModel


class IndexRequest(BaseModel):
    url: str


class IndexResponse(BaseModel):
    video_id: str
    chunks_indexed: int


class AskRequest(BaseModel):
    video_id: str
    question: str


class AskResponse(BaseModel):
    answer: str
    was_covered: bool
    source_timestamps: list[float]
