# Architecture

The project is split into three main runtime modules plus a thin entrypoint:

- `podlings/data.py`
  - XML loading and parsing
  - shared date/sponsor helpers
  - `Podling` dataclass
- `podlings/tools.py`
  - MCP tool handlers
  - argument validation
  - analytics aggregation
  - `TOOLS` registry
- `podlings/protocol.py`
  - JSON-RPC response helpers
  - stdio request loop
  - tool dispatch
  - MCP tool response wrapping with `structuredContent` and a JSON text fallback
- `server.py`
  - compatibility facade and executable entrypoint

## Testing

The tests mirror the runtime split:

- `tests/test_data.py`
- `tests/test_tools.py`
- `tests/test_protocol.py`
- `tests/test_mcp_integration.py`

## Design Notes

- `podlings/data.py` should stay free of MCP-specific concerns.
- `podlings/tools.py` should contain business logic, but not stdio/protocol handling.
- `podlings/protocol.py` should only orchestrate requests and responses, not own analytics logic. Structured tool results are returned as both MCP `structuredContent` and a JSON text fallback for clients that only read `content`.
- `server.py` exists so the executable surface stays stable even if internal modules continue to evolve.
