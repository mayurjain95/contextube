"""
Chunks a transcript, embeds it, and stores it in Chroma under a
collection named after the video ID — so each video's transcript is
isolated and queries never leak across videos.
"""

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.core.config import settings
from app.services.transcript_loader import TranscriptSegment

_embeddings = OllamaEmbeddings(
    model=settings.embedding_model,
    base_url=settings.ollama_base_url,
)


def _collection_name(video_id: str) -> str:
    return f"yt_{video_id}"


def build_index(video_id: str, segments: list[TranscriptSegment]) -> int:
    """Chunk segments, embed, and persist. Returns number of chunks stored."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
    )

    docs: list[Document] = []
    for seg in segments:
        for chunk in splitter.split_text(seg.text):
            docs.append(
                Document(
                    page_content=chunk,
                    metadata={"video_id": video_id, "start": seg.start},
                )
            )

    Chroma.from_documents(
        documents=docs,
        embedding=_embeddings,
        collection_name=_collection_name(video_id),
        persist_directory=settings.chroma_persist_dir,
    )
    return len(docs)


def get_retriever(video_id: str, k: int = 4):
    store = Chroma(
        collection_name=_collection_name(video_id),
        embedding_function=_embeddings,
        persist_directory=settings.chroma_persist_dir,
    )
    return store.as_retriever(search_kwargs={"k": k})


def index_exists(video_id: str) -> bool:
    store = Chroma(
        collection_name=_collection_name(video_id),
        embedding_function=_embeddings,
        persist_directory=settings.chroma_persist_dir,
    )
    return store._collection.count() > 0
