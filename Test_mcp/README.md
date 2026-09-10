## Test MCP server

Small FastMCP server for testing a local MCP deployment. It provides these tools:

- `health_check`
- `greet`
- `add_numbers`
- `echo`

### Run with uv

From this directory:

```powershell
uv run test-mcp
```

### Claude Desktop configuration

Add this server under `mcpServers`:

```json
"test-mcp": {
	"command": "uv",
	"args": [
		"--directory",
		"C:\\path\\to\\Test_mcp",
		"run",
		"test-mcp"
	]
}
```

After saving the configuration, restart Claude Desktop and ask:

```text
Run the health check on the test-mcp server.
```
