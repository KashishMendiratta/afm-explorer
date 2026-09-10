from __future__ import annotations

import hashlib
import re

import numpy as np
from langchain_core.embeddings import Embeddings

TOKEN_RE = re.compile(r"[a-z0-9]+")


class LocalHashEmbeddings(Embeddings):
    """Deterministic, dependency-light embeddings for the local demo corpus.

    Exact terms and short bigrams share hashed dimensions. This is not a
    hosted semantic model, but it makes retrieval reproducible, private and
    free in CI while still exercising LangChain's vector-store interface.
    """

    def __init__(self, dimensions: int = 768):
        self.dimensions = dimensions

    def _embed(self, text: str) -> list[float]:
        tokens = TOKEN_RE.findall(text.lower())
        features = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
        vector = np.zeros(self.dimensions, dtype=np.float32)
        for feature in features:
            digest = hashlib.blake2b(feature.encode(), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[bucket] += sign
        norm = float(np.linalg.norm(vector))
        if norm:
            vector /= norm
        return vector.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)
