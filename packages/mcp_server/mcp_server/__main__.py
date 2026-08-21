"""Entry point: `python -m mcp_server` or the `afm-mcp-server` console
script (see pyproject.toml). Configuration is entirely via environment
variables so it's easy to set from a Claude Desktop config file or a
docker-compose service:

  BACKEND_URL       AFM Explorer backend base URL (default http://localhost:8000)
  AFM_API_KEY       matches the backend's AFM_API_KEY if it has one configured;
                    required to call write tools against an auth-gated backend
  AFM_MCP_READONLY  set (to 1/true/yes) to omit write tools entirely
  MCP_TRANSPORT     'stdio' (default — for Claude Desktop and most local MCP
                    clients) or 'http' (runs a small web server instead, for
                    a remote/containerized assistant)
  MCP_HTTP_HOST     default 0.0.0.0, only used when MCP_TRANSPORT=http
  MCP_HTTP_PORT     default 8765, only used when MCP_TRANSPORT=http
"""

from __future__ import annotations

import os

from mcp_server.server import mcp


def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "stdio").strip().lower()
    if transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(
            transport=transport,
            host=os.environ.get("MCP_HTTP_HOST", "0.0.0.0"),
            port=int(os.environ.get("MCP_HTTP_PORT", "8765")),
        )


if __name__ == "__main__":
    main()
