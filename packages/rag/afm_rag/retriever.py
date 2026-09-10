from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from langchain_core.vectorstores import InMemoryVectorStore

from .embeddings import LocalHashEmbeddings
from .ingest import chunk_documents, load_documents


@dataclass(frozen=True)
class KnowledgeHit:
    content: str
    source: str
    topic: str
    score: float

    def to_dict(self) -> dict:
        return asdict(self)


class AFMRetriever:
    """LangChain-backed, local vector retrieval over AFM reference files."""

    def __init__(self, store: InMemoryVectorStore, chunk_count: int):
        self.store = store
        self.chunk_count = chunk_count

    @classmethod
    def from_path(
        cls,
        knowledge_path: str | Path,
        *,
        chunk_size: int = 900,
        chunk_overlap: int = 120,
    ) -> "AFMRetriever":
        chunks = chunk_documents(load_documents(knowledge_path), chunk_size, chunk_overlap)
        if not chunks:
            raise ValueError(f"no supported knowledge documents found in {knowledge_path}")
        store = InMemoryVectorStore(embedding=LocalHashEmbeddings())
        store.add_documents(chunks)
        return cls(store, len(chunks))

    def search(self, query: str, *, top_k: int = 4, topic: str | None = None) -> list[KnowledgeHit]:
        if not query.strip():
            raise ValueError("query must not be empty")
        if not 1 <= top_k <= 10:
            raise ValueError("top_k must be between 1 and 10")
        candidates = self.store.similarity_search_with_score(query, k=min(self.chunk_count, max(top_k * 4, top_k)))
        hits = [
            KnowledgeHit(
                content=document.page_content,
                source=document.metadata.get("source", "unknown"),
                topic=document.metadata.get("topic", "unknown"),
                score=float(score),
            )
            for document, score in candidates
            if topic is None or document.metadata.get("topic") == topic
        ]
        return hits[:top_k]
