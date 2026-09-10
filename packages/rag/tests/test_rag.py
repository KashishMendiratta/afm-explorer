from pathlib import Path

from afm_rag.evaluation import RetrievalCase, retrieval_hit_rate
from afm_rag.ingest import chunk_documents, load_documents
from afm_rag.retriever import AFMRetriever

KNOWLEDGE = Path(__file__).resolve().parents[3] / "knowledge"


def test_load_and_chunk_markdown_documents():
    documents = load_documents(KNOWLEDGE)
    chunks = chunk_documents(documents, chunk_size=350, chunk_overlap=40)
    assert len(documents) >= 2
    assert len(chunks) >= len(documents)
    assert all(chunk.metadata["source"].endswith(".md") for chunk in chunks)


def test_local_retrieval_and_metadata_filtering():
    retriever = AFMRetriever.from_path(KNOWLEDGE, chunk_size=350, chunk_overlap=40)
    hits = retriever.search("adhesion snap-off retract curve artifact", top_k=2)
    assert hits
    assert "force_curve_artifacts" in hits[0].source

    filtered = retriever.search("contact point baseline", topic="afm-basics", top_k=3)
    assert filtered
    assert all(hit.topic == "afm-basics" for hit in filtered)


def test_retrieval_evaluation_runs_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    retriever = AFMRetriever.from_path(KNOWLEDGE)
    score = retrieval_hit_rate(
        retriever,
        [
            RetrievalCase("baseline contact point stiffness slope", "afm_basics"),
            RetrievalCase("retract snap-off adhesion artifact", "force_curve_artifacts"),
        ],
        top_k=2,
    )
    assert score == 1.0
