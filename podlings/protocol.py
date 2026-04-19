from __future__ import annotations

import json
import sys
import traceback
from typing import Any

from .tools import TOOLS

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

SERVER_INFO = {
    "name": "podlings-mcp",
    "version": "0.1.0",
}


def make_response(message_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def make_error(message_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": message_id, "error": error}


def emit(payload: Any) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=True) + "\n")
    sys.stdout.flush()


def _json_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, indent=2)


def tool_response(payload: Any, *, is_error: bool = False) -> dict[str, Any]:
    """Build a standard MCP tool result with structured data when available."""

    if isinstance(payload, str):
        result: dict[str, Any] = {"content": [{"type": "text", "text": payload}]}
    else:
        result = {
            "content": [{"type": "text", "text": _json_text(payload)}],
            "structuredContent": payload,
        }
    if is_error:
        result["isError"] = True
    return result


def list_tools_payload() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "description": info["description"],
            "inputSchema": info["inputSchema"],
        }
        for name, info in TOOLS.items()
    ]


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name not in TOOLS:
        raise ValueError(f"Unknown tool '{name}'")
    try:
        return tool_response(TOOLS[name]["handler"](arguments))
    except Exception as exc:
        return tool_response({"ok": False, "error": str(exc), "tool": name}, is_error=True)


def initialize_result(params: dict[str, Any]) -> dict[str, Any]:
    protocol_version = params.get("protocolVersion", "2024-11-05")
    if not isinstance(protocol_version, str):
        protocol_version = "2024-11-05"
    return {
        "protocolVersion": protocol_version,
        "capabilities": {"tools": {}},
        "serverInfo": SERVER_INFO,
    }


def handle_initialize(message_id: Any, params: dict[str, Any]) -> None:
    emit(make_response(message_id, initialize_result(params)))


def handle_tools_list(message_id: Any) -> None:
    emit(make_response(message_id, {"tools": list_tools_payload()}))


def tools_call_response(message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    name = params.get("name")
    arguments = params.get("arguments", {})
    if not isinstance(name, str):
        return make_error(
            message_id,
            INVALID_PARAMS,
            "Tool name must be a string",
            {"field": "name", "expected": "string"},
        )
    if name not in TOOLS:
        return make_error(
            message_id,
            INVALID_PARAMS,
            f"Unknown tool '{name}'",
            {"field": "name", "tool": name},
        )
    if not isinstance(arguments, dict):
        return make_error(
            message_id,
            INVALID_PARAMS,
            "Tool arguments must be an object",
            {"field": "arguments", "expected": "object"},
        )

    return make_response(message_id, call_tool(name, arguments))


def handle_tools_call(message_id: Any, params: dict[str, Any]) -> None:
    emit(tools_call_response(message_id, params))


def _is_valid_id(message_id: Any) -> bool:
    return message_id is None or (isinstance(message_id, (str, int)) and not isinstance(message_id, bool))


def _message_id_for_error(message: dict[str, Any]) -> Any:
    message_id = message.get("id")
    if _is_valid_id(message_id):
        return message_id
    return None


def handle_message(message: Any) -> dict[str, Any] | None:
    """Handle one JSON-RPC message and return a response, or None for notifications."""

    if not isinstance(message, dict):
        return make_error(None, INVALID_REQUEST, "JSON-RPC request must be an object")

    message_id = message.get("id")
    expects_response = "id" in message
    error_id = _message_id_for_error(message)

    if message.get("jsonrpc") != "2.0":
        return make_error(
            error_id,
            INVALID_REQUEST,
            "JSON-RPC version must be '2.0'",
            {"field": "jsonrpc", "expected": "2.0"},
        )

    if "id" in message and not _is_valid_id(message_id):
        return make_error(
            None,
            INVALID_REQUEST,
            "JSON-RPC id must be a string, integer, or null",
            {"field": "id"},
        )

    method = message.get("method")
    if not isinstance(method, str):
        return make_error(
            error_id,
            INVALID_REQUEST,
            "JSON-RPC method must be a string",
            {"field": "method", "expected": "string"},
        )

    params = message.get("params", {})
    if not isinstance(params, dict):
        if not expects_response:
            return None
        return make_error(
            error_id,
            INVALID_PARAMS,
            "Method params must be an object",
            {"field": "params", "expected": "object"},
        )

    try:
        if method == "initialize":
            if not expects_response:
                return None
            return make_response(message_id, initialize_result(params))
        if method == "notifications/initialized":
            return None
        if method == "tools/list":
            if not expects_response:
                return None
            return make_response(message_id, {"tools": list_tools_payload()})
        if method == "tools/call":
            if not expects_response:
                return None
            return tools_call_response(message_id, params)
        if not expects_response:
            return None
        return make_error(error_id, METHOD_NOT_FOUND, f"Method '{method}' not found", {"method": method})
    except Exception as exc:
        if not expects_response:
            return None
        return make_error(
            error_id,
            INTERNAL_ERROR,
            f"Internal error: {exc}",
            {"traceback": traceback.format_exc()},
        )


def handle_payload(payload: Any) -> dict[str, Any] | list[dict[str, Any]] | None:
    if isinstance(payload, list):
        if not payload:
            return make_error(None, INVALID_REQUEST, "JSON-RPC batch must contain at least one request")
        responses = [response for message in payload if (response := handle_message(message)) is not None]
        return responses or None
    return handle_message(payload)


def main() -> int:
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue

        try:
            response = handle_payload(json.loads(line))
            if response is not None:
                emit(response)
        except json.JSONDecodeError as exc:
            emit(make_error(None, PARSE_ERROR, "Parse error", {"details": str(exc)}))
        except Exception as exc:
            emit(
                make_error(
                    None,
                    INTERNAL_ERROR,
                    f"Internal error: {exc}",
                    {"traceback": traceback.format_exc()},
                )
            )

    return 0
