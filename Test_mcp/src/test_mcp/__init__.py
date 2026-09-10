from .main import mcp


def main() -> None:
    """Start the Test MCP server over stdio."""
    mcp.run(transport="http",host="0.0.0.0",port=8000)
