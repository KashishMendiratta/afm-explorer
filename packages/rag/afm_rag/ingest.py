from __future__ import annotations

from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

SUPPORTED_SUFFIXES = {".md", ".txt", ".pdf"}


def discover_documents(root: str | Path) -> list[Path]:
    root = Path(root)
    if root.is_file():
        return [root] if root.suffix.lower() in SUPPORTED_SUFFIXES else []
    if not root.exists():
        raise FileNotFoundError(f"knowledge path does not exist: {root}")
    return sorted(path for path in root.rglob("*") if path.suffix.lower() in SUPPORTED_SUFFIXES)


def load_documents(root: str | Path) -> list[Document]:
    documents: list[Document] = []
    for path in discover_documents(root):
        loader = PyPDFLoader(str(path)) if path.suffix.lower() == ".pdf" else TextLoader(str(path), encoding="utf-8")
        loaded = loader.load()
        topic = path.stem.replace("_", "-")
        for document in loaded:
            document.metadata.update({"source": str(path), "topic": topic})
        documents.extend(loaded)
    return documents


def chunk_documents(
    documents: list[Document], chunk_size: int = 900, chunk_overlap: int = 120
) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " "],
    )
    return splitter.split_documents(documents)
