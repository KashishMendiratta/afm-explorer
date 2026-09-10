from __future__ import annotations

import argparse
import asyncio
from dataclasses import replace

from afm_rag import AFMRetriever

from .config import AgentSettings
from .runner import run_agent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the AFM Explorer MCP + RAG agent")
    parser.add_argument("question", nargs="*", help="AFM analysis question")
    parser.add_argument("--backend-url", help="override BACKEND_URL")
    parser.add_argument("--model", help="override AFM_AGENT_MODEL")
    parser.add_argument("--max-turns", type=int, help="maximum autonomous reasoning turns (1-20)")
    parser.add_argument(
        "--allow-writes",
        action="store_true",
        help="expose MCP write tools; individual writes still require an explicit user request",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify local configuration and RAG indexing without an API call",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = AgentSettings.from_env()
    if args.backend_url:
        settings = replace(settings, backend_url=args.backend_url.rstrip("/"))
    if args.model:
        settings = replace(settings, model=args.model)
    if args.max_turns is not None:
        if not 1 <= args.max_turns <= 20:
            raise SystemExit("--max-turns must be between 1 and 20")
        settings = replace(settings, max_turns=args.max_turns)
    if args.allow_writes:
        settings = replace(settings, allow_writes=True)
    if args.check:
        retriever = AFMRetriever.from_path(settings.knowledge_path)
        print(f"Ready: indexed {retriever.chunk_count} local knowledge chunks; writes={settings.allow_writes}")
        return
    if not args.question:
        raise SystemExit("provide a question, or use --check")
    print(asyncio.run(run_agent(" ".join(args.question), settings)))


if __name__ == "__main__":
    main()
