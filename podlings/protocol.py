from __future__ import annotations

import json
import sys
import traceback
from typing import Any

from .tools import TOOLS

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


def emit(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=True) + "\n")
    sys.stdout.flush()


def handle_initialize(message_id: Any, params: dict[str, Any]) -> None:
    protocol_version = params.get("protocolVersion", "2024-11-05")
    emit(
        make_response(
            message_id,
            {
                "protocolVersion": protocol_version,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
        )
    )


def handle_tools_list(message_id: Any) -> None:
    tools = []
    for name, info in TOOLS.items():
        tools.append(
            {
                "name": name,
                "description": info["description"],
                "inputSchema": info["inputSchema"],
            }
        )
    emit(make_response(message_id, {"tools": tools}))


def handle_tools_call(message_id: Any, params: dict[str, Any]) -> None:
    name = params.get("name")
    arguments = params.get("arguments", {})
    if name not in TOOLS:
        emit(make_error(message_id, -32602, f"Unknown tool '{name}'"))
        return
    if not isinstance(arguments, dict):
        emit(make_error(message_id, -32602, "Tool arguments must be an object"))
        return

    try:
        result = TOOLS[name]["handler"](arguments)
    except Exception as exc:
        emit(
            make_response(
                message_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {
                                    "ok": False,
                                    "error": str(exc),
                                },
                                ensure_ascii=True,
                                indent=2,
                            ),
                        }
                    ],
                    "isError": True,
                },
            )
        )
        return

    emit(
        make_response(
            message_id,
            {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, ensure_ascii=True, indent=2),
                    }
                ]
            },
        )
    )


def main() -> int:
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue

        try:
            message = json.loads(line)
            message_id = message.get("id")
            method = message.get("method")
            params = message.get("params", {})

            if method == "initialize":
                handle_initialize(message_id, params if isinstance(params, dict) else {})
            elif method == "notifications/initialized":
                continue
            elif method == "tools/list":
                handle_tools_list(message_id)
            elif method == "tools/call":
                handle_tools_call(message_id, params if isinstance(params, dict) else {})
            else:
                emit(make_error(message_id, -32601, f"Method '{method}' not found"))
        except Exception as exc:
            emit(
                make_error(
                    None,
                    -32603,
                    f"Internal error: {exc}",
                    {"traceback": traceback.format_exc()},
                )
            )

    return 0
