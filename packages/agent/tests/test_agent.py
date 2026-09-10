import json
from pathlib import Path

import pytest
from afm_agent.cli import build_parser
from afm_agent.config import AgentSettings
from afm_agent.prompt import AGENT_INSTRUCTIONS
from afm_agent.runner import build_agent, build_mcp_environment, run_agent
from afm_agent.tools import search_knowledge
from afm_rag import AFMRetriever

KNOWLEDGE = Path(__file__).resolve().parents[3] / "knowledge"


def settings(**overrides):
    values = {
        "backend_url": "http://backend:8000",
        "model": "gpt-5.6-luna",
        "max_turns": 8,
        "allow_writes": False,
        "api_key": "secret",
        "knowledge_path": KNOWLEDGE,
    }
    values.update(overrides)
    return AgentSettings(**values)


def test_mcp_is_readonly_by_default():
    env = build_mcp_environment(settings())
    assert env["AFM_MCP_READONLY"] == "true"
    assert env["BACKEND_URL"] == "http://backend:8000"


def test_writes_require_explicit_opt_in():
    assert build_mcp_environment(settings(allow_writes=True))["AFM_MCP_READONLY"] == "false"
    assert "user explicitly" in AGENT_INSTRUCTIONS
    assert "Never fabricate" in AGENT_INSTRUCTIONS


def test_search_tool_returns_source_grounded_json_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    retriever = AFMRetriever.from_path(KNOWLEDGE)
    result = json.loads(search_knowledge(retriever, "retract adhesion snap-off", top_k=1))
    assert result["results"]
    assert result["results"][0]["source"].endswith("force_curve_artifacts.md")


def test_agent_can_be_constructed_offline_with_mcp_and_rag(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    retriever = AFMRetriever.from_path(KNOWLEDGE)
    mcp_server = object()
    agent = build_agent(settings(), mcp_server, retriever)
    assert agent.mcp_servers == [mcp_server]
    assert [tool.name for tool in agent.tools] == ["search_afm_knowledge"]


async def test_real_run_fails_fast_with_clear_api_key_message(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="Offline RAG and unit tests do not require it"):
        await run_agent("inspect the available scan", settings())


@pytest.mark.parametrize("value", [0, 21])
def test_turn_budget_is_bounded(monkeypatch, value):
    monkeypatch.setenv("AFM_AGENT_MAX_TURNS", str(value))
    with pytest.raises(ValueError, match="between 1 and 20"):
        AgentSettings.from_env()


def test_cli_preserves_runtime_overrides():
    args = build_parser().parse_args(
        ["--backend-url", "http://example.test/", "--model", "test-model", "inspect", "scan"]
    )
    assert args.backend_url == "http://example.test/"
    assert args.model == "test-model"
    assert args.question == ["inspect", "scan"]
