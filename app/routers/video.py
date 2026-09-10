from fastapi import APIRouter, HTTPException
import logging

from app.schemas import IndexRequest, IndexResponse, AskRequest, AskResponse
from app.services.transcript_loader import (
    get_transcript,
    extract_video_id,
    TranscriptUnavailableError,
)
from app.services.vector_store import build_index, index_exists
from app.services.qa_chain import answer_question

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/index", response_model=IndexResponse)
def index_video(payload: IndexRequest):
    try:
        video_id = extract_video_id(payload.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        segments = get_transcript(payload.url)
    except TranscriptUnavailableError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Could not retrieve a transcript for this video: {e}",
        )

    try:
        chunk_count = build_index(video_id, segments)
    except Exception as e:
        logger.exception("Failed to build index for video %s", video_id)
        raise HTTPException(status_code=502, detail=f"Could not build the video index: {e}")
    return IndexResponse(video_id=video_id, chunks_indexed=chunk_count)


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest):
    if not index_exists(payload.video_id):
        raise HTTPException(
            status_code=404,
            detail="This video hasn't been indexed yet. Call /index first.",
        )

    result = answer_question(payload.video_id, payload.question)
    return AskResponse(
        answer=result.text,
        was_covered=result.was_covered,
        source_timestamps=result.sources,
    )
