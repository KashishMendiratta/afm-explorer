from __future__ import annotations

import os
import sys

from afm_rag import AFMRetriever
from agents import Agent, Runner
from agents.mcp import MCPServerStdio

from .config import AgentSettings
from .prompt import AGENT_INSTRUCTIONS
from .tools import build_search_afm_knowledge_tool


def build_mcp_environment(settings: AgentSettings) -> dict[str, str]:
    env = os.environ.copy()
    env["BACKEND_URL"] = settings.backend_url
    env["AFM_API_KEY"] = settings.api_key
    env["AFM_MCP_READONLY"] = "false" if settings.allow_writes else "true"
    return env


def build_agent(settings: AgentSettings, mcp_server, retriever: AFMRetriever) -> Agent:
    return Agent(
        name="AFM Explorer Agent",
        instructions=AGENT_INSTRUCTIONS,
        model=settings.model,
        mcp_servers=[mcp_server],
        tools=[build_search_afm_knowledge_tool(retriever)],
    )


async def run_agent(question: str, settings: AgentSettings | None = None) -> str:
    if not question.strip():
        raise ValueError("question must not be empty")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is required for real agent execution. Offline RAG and unit tests do not require it."
        )

    settings = settings or AgentSettings.from_env()
    retriever = AFMRetriever.from_path(settings.knowledge_path)
    async with MCPServerStdio(
        name="AFM Explorer MCP",
        params={
            "command": sys.executable,
            "args": ["-m", "mcp_server"],
            "env": build_mcp_environment(settings),
        },
        cache_tools_list=True,
    ) as mcp_server:
        agent = build_agent(settings, mcp_server, retriever)
        result = await Runner.run(agent, question, max_turns=settings.max_turns)
        return str(result.final_output)
