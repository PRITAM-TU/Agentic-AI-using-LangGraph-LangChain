from datetime import datetime, timezone

from fastmcp import FastMCP


mcp = FastMCP("Test MCP Server")


@mcp.tool
def health_check() -> dict[str, str]:
	"""Return the server status and current UTC time."""
	return {"status": "ok", "server": "Test MCP Server", "utc": datetime.now(timezone.utc).isoformat()}


@mcp.tool
def greet(name: str) -> str:
	"""Return a greeting for a person."""
	name = name.strip()
	if not name:
		raise ValueError("name cannot be empty")
	return f"Hello, {name}! The MCP server is working."


@mcp.tool
def add_numbers(first: float, second: float) -> float:
	"""Add two numbers."""
	return first + second


@mcp.tool
def echo(message: str) -> str:
	"""Return the supplied message unchanged."""
	return message


if __name__ == "__main__":
	mcp.run(transport="http",host="0.0.0.0",port=8000)
