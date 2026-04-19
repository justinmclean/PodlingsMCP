# AGENTS

## Purpose

This repository contains a small dependency-light MCP server for working with Apache Software Foundation Incubator `podlings.xml` data.

## Project Layout

- `podlings/data.py`
  - XML loading, parsing, normalization, sponsor classification, and date/duration helpers
- `podlings/tools.py`
  - MCP tool handlers and shared argument/analytics helpers
- `podlings/schemas.py`
  - Shared tool schema fragments and schema-builder helpers
- `podlings/protocol.py`
  - JSON-RPC/MCP stdio protocol handling
- `server.py`
  - Thin entrypoint
- `tests/`
  - Unit and integration tests
- `tests/fixtures.py`
  - Shared Python test fixtures and temp XML helpers
- `tests/fixtures/`
  - File-based test fixtures such as `sample-podlings.xml`

## Key Defaults And Concepts

- `sponsor_type` defaults to `incubator` for filtering and analytics tools unless explicitly overridden.
- `completed` means podlings that reached an end state: `graduated` or `retired`.
- Count/rate timeline tools place results into years using `enddate`.
- Duration timeline tools use both `startdate` and `enddate`.

## Developer Workflow

Use these commands before finishing changes:

- `make check-format`
- `make lint`
- `make typecheck`
- `make test`

CI runs the same checks in GitHub Actions.

## Contribution Guidelines

- Keep new MCP tool schema definitions in `podlings/schemas.py`.
- Keep MCP protocol wiring in `podlings/protocol.py`.
- Prefer extending shared helpers in `podlings/tools.py` over copying analytics logic.
- Add tests for any new tool, filter, or output shape.
- Update `README.md` when adding or changing public MCP tools or defaults.
- Keep test-only data under `tests/fixtures.py` or `tests/fixtures/` rather than at the repo root.

## Testing Notes

- Direct tool behavior belongs in `tests/test_tools.py`.
- Parsing/data behavior belongs in `tests/test_data.py`.
- Protocol helper behavior belongs in `tests/test_protocol.py`.
- End-to-end MCP stdio coverage belongs in `tests/test_mcp_integration.py`.
