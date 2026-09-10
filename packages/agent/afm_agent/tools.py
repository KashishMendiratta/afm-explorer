from __future__ import annotations

import json

from afm_rag import AFMRetriever
from agents import function_tool


def search_knowledge(
    retriever: AFMRetriever, query: str, top_k: int = 4, topic: str | None = None
) -> str:
    """Plain callable kept separate so retrieval is easy to evaluate offline."""
    hits = retriever.search(query, top_k=top_k, topic=topic)
    return json.dumps({"query": query, "results": [hit.to_dict() for hit in hits]}, indent=2)


def build_search_afm_knowledge_tool(retriever: AFMRetriever):
    @function_tool
    def search_afm_knowledge(query: str, top_k: int = 4, topic: str | None = None) -> str:
        """Search the local AFM knowledge base for interpretation guidance.

        Returns relevant passages with source paths, topic metadata and similarity
        scores. Use the source paths as citations in the final response.
        """
        return search_knowledge(retriever, query, top_k=top_k, topic=topic)

    return search_afm_knowledge
