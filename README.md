# MCP Gateway Server

MCP Gateway Server is a stateless proxy and facade layer designed to completely decouple AI agents (like Cline, Brownie, etc.) from underlying infrastructure complexity. 

It acts as a **"Single, Intelligent MCP Server"**, curating exactly what tools the AI agent can see and use, while transparently handling complex routing to multiple backend MCP servers.

## 🌟 Why MCP Gateway?
When connecting AI agents to real-world infrastructure, you don't want to expose raw, potentially dangerous backend tools directly. 

MCP Gateway solves this by allowing you to **filter backend tools** and provide securely wrapped **"Virtual Tools"**. The LLM interacts with a clean, curated list of tools via standard `stdio`, while the Gateway handles the messy reality of HTTP/SSE protocol translation, container routing, and namespace conflicts in the background.

## 🏗️ Architecture & Core Features

### 1. Tool Filtering & Virtualization (Facade Pattern)
- **Virtual Tools:** Define custom, abstract tools in `gateway_config.yaml` that map to specific backend routes (e.g., exposing a safe `run_command` that secretly routes to an isolated, ephemeral sandbox).
- **Explicit Filtering:** Pass-through only the tools you want. Hide or intercept tools from backend servers to prevent the AI from accessing unnecessary or dangerous capabilities.

### 2. Smart Registry & Conflict Resolution
- **Dynamic Discovery:** Automatically fetches tool lists from newly provisioned backend servers.
- **Namespace Management:** Prevents collisions by automatically applying prefixes to raw backend tools (e.g., `serverA_read_file`), while giving highest priority to your static routing overrides (Last-Write-Wins).

### 3. Dual-Plane Architecture & Pure Proxy
- **Data Plane (Agent Interface):** Pure `stdio` communication. Translates JSON-RPC to HTTP/SSE seamlessly without interfering with the LLM's own error-correction loops (Validation errors are passed through exactly as received).
- **Control Plane (Admin Interface):** Provides a REST API for orchestration workflows to dynamically provision or tear down backend routes without restarting the gateway.
