"""
Answers a question against a single video's indexed transcript.

Guardrail: before ever calling the LLM, we check the similarity scores
of the retrieved chunks. If nothing clears the threshold, we short-circuit
to "not covered in the video" — the model never gets a chance to
hallucinate an answer from its own general knowledge.
"""

from dataclasses import dataclass

from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings

NOT_COVERED_MESSAGE = "This wasn't covered in the video."

_embeddings = OllamaEmbeddings(
    model=settings.embedding_model,
    base_url=settings.ollama_base_url,
)

_llm = ChatOllama(
    model=settings.chat_model,
    base_url=settings.ollama_base_url,
    temperature=0,
)

_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You answer questions using ONLY the video transcript excerpts provided "
     "below. If the excerpts don't contain the answer, say so plainly — "
     "never use outside knowledge to fill gaps.\n\n"
     "Transcript excerpts:\n{context}"),
    ("human", "{question}"),
])


@dataclass
class Answer:
    text: str
    sources: list[float]  # timestamps (seconds) of chunks actually used
    was_covered: bool


def answer_question(video_id: str, question: str) -> Answer:
    store = Chroma(
        collection_name=f"yt_{video_id}",
        embedding_function=_embeddings,
        persist_directory=settings.chroma_persist_dir,
    )

    results = store.similarity_search_with_relevance_scores(question, k=4)

    passing = [(doc, score) for doc, score in results
               if score >= settings.retrieval_score_threshold]

    if not passing:
        return Answer(text=NOT_COVERED_MESSAGE, sources=[], was_covered=False)

    context = "\n\n---\n\n".join(doc.page_content for doc, _ in passing)
    sources = [doc.metadata.get("start", 0.0) for doc, _ in passing]

    chain = _PROMPT | _llm
    response = chain.invoke({"context": context, "question": question})

    return Answer(text=response.content, sources=sources, was_covered=True)
