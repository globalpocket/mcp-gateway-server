# 📖 MCP Routing Gateway - User Manual

## 1. Introduction

**MCP Routing Gateway** is a pure, stateless routing proxy and facade layer designed to completely decouple AI agents (like Cline, Claude Desktop, Brownie, etc.) from the complexity of the underlying infrastructure.

To the AI agent, this gateway acts as a **"Single, Intelligent MCP Server"**. It transparently multiplexes standard communication via `stdio` (standard input/output) and routes it to multiple backend MCP servers via HTTP/SSE, while strictly managing and controlling the tools available to the AI.

## 2. Key Features

* **Zero Payload Interference (Pure Proxy):** When routing `tools/call` requests, it only rewrites the tool name for routing purposes; payloads like IDs and arguments are passed through completely unmodified.
* **Tool Filtering and Virtualization (Facade Pattern):** You can use a blocklist (described below) to completely hide specific tools from the AI, or provide safely wrapped "Virtual Tools".
* **Smart Namespace Resolution:** If tool names conflict across multiple servers, it provides both a prefixed alias (e.g., `serverA_read_file`) and the base name. Deterministic routing fixed to a specific server is also possible via configuration.
* **Full-Duplex Multiplexer and ID Collision Avoidance:** Maintains persistent SSE streams and fully supports reverse requests (like `sampling`) from the backend to the LLM. Even if request IDs overlap across multiple servers, the gateway swaps them with unique IDs internally to prevent routing failures.
* **Strict MCP Protocol Compliance:** Fully supports the `initialize` handshake, `ping` for health checks, and `notifications/cancelled` for interrupting long-running tasks.

## 3. Installation

This project requires Python 3.10 or higher.

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install the package
pip install -e .
```

## 4. Configuration (`gateway_config.yaml`)

The gateway's behavior is defined in a YAML configuration file.

```yaml
version: "1.0"

# 1. Virtual Tools (Facade)
# Define abstract tools that map securely to specific backend routes
virtual_tools:
  run_command:
    description: "Executes a shell command inside a secure sandbox."
    target_route: "/mcp/sandbox"

# 2. Explicit Routing (Highest Priority)
# Fix a base tool name to a specific server in case of name conflicts
explicit_routing:
  read_file: "serverA"
  search_github: "serverB"

# 3. Blocked Tools (Explicit Filtering)
# Completely hide (Hide) specific tools from the AI agent
blocked_tools:
  - "search_github"         # Block the base name
  - "serverA_run_command"   # Block the prefixed name
```

## 5. Usage

### Starting the Gateway

Start the gateway using the CLI. By default, it reads `gateway_config.yaml` in the current execution directory.

```bash
# Basic startup
mcp-gateway

# Specify a custom config file
mcp-gateway --config custom_config.yaml

# Override the backend base URL (default is http://localhost:8000)
MCP_BACKEND_BASE_URL="http://mcp-router.local" mcp-gateway
```

*Note: The gateway communicates with the AI agent via `stdio`. To prevent corrupting the JSON-RPC payloads, all logs are output to `stderr`.*

### Control Plane API (Admin Interface)

The gateway exposes a REST API at `http://127.0.0.1:8001`, enabling dynamic provisioning.

* **Dynamic Addition/Synchronization of Backend Servers:**
    Connects to the specified route, performs the `initialize` handshake, and then retrieves and merges the tool list.

```bash
curl -X POST http://127.0.0.1:8001/admin/routes/sync \
     -H "Content-Type: application/json" \
     -d '{"server_name": "serverA", "target_route": "/mcp/serverA"}'
```

* **Removing a Backend Server:**
    Removes the server from the registry and safely cancels the SSE connection task to that server to prevent resource leaks.

```bash
curl -X DELETE http://127.0.0.1:8001/admin/routes/serverA
```

## 6. Integration with AI Agents

To use this gateway with Claude Desktop or Cline, register it as a standard `stdio` MCP server in your configuration file.

**Configuration Example (Claude Desktop):**

```json
{
  "mcpServers": {
    "mcp-routing-gateway": {
      "command": "mcp-gateway",
      "args": ["--config", "/absolute/path/to/gateway_config.yaml"],
      "env": {
        "MCP_BACKEND_BASE_URL": "http://localhost:8000"
      }
    }
  }
}
```
