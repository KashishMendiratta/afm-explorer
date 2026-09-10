from __future__ import annotations

from dataclasses import dataclass

from .retriever import AFMRetriever


@dataclass(frozen=True)
class RetrievalCase:
    query: str
    expected_source_fragment: str


def retrieval_hit_rate(retriever: AFMRetriever, cases: list[RetrievalCase], top_k: int = 3) -> float:
    if not cases:
        raise ValueError("at least one evaluation case is required")
    matches = 0
    for case in cases:
        hits = retriever.search(case.query, top_k=top_k)
        matches += any(case.expected_source_fragment in hit.source for hit in hits)
    return matches / len(cases)
