import io
import json
import unittest
from unittest.mock import patch

from podlings.protocol import (
    emit,
    handle_initialize,
    handle_message,
    handle_payload,
    handle_tools_call,
    handle_tools_list,
    main,
    make_error,
    make_response,
)
from tests.fixtures import SAMPLE_XML


class ProtocolHelperTests(unittest.TestCase):
    def test_make_response_shape(self) -> None:
        self.assertEqual(
            make_response(1, {"ok": True}),
            {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}},
        )

    def test_make_error_shape(self) -> None:
        self.assertEqual(
            make_error(1, -32601, "nope"),
            {"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "nope"}},
        )

    def test_make_error_includes_optional_data(self) -> None:
        self.assertEqual(
            make_error(1, -32603, "boom", {"traceback": "x"}),
            {"jsonrpc": "2.0", "id": 1, "error": {"code": -32603, "message": "boom", "data": {"traceback": "x"}}},
        )

    def test_emit_writes_json_line(self) -> None:
        stdout = io.StringIO()
        with patch("podlings.protocol.sys.stdout", stdout):
            emit({"ok": True})

        self.assertEqual(stdout.getvalue(), '{"ok": true}\n')

    def test_handle_initialize_emits_response(self) -> None:
        with patch("podlings.protocol.emit") as emit_mock:
            handle_initialize(1, {"protocolVersion": "2024-11-05"})

        emit_mock.assert_called_once()
        payload = emit_mock.call_args.args[0]
        self.assertEqual(payload["result"]["serverInfo"]["name"], "podlings-mcp")

    def test_handle_tools_list_emits_tools(self) -> None:
        with patch("podlings.protocol.emit") as emit_mock:
            handle_tools_list(2)

        emit_mock.assert_called_once()
        payload = emit_mock.call_args.args[0]
        tool_names = [tool["name"] for tool in payload["result"]["tools"]]
        self.assertIn("mentor_count_stats", tool_names)
        self.assertIn("podlings_started_over_time", tool_names)
        self.assertIn("started_podlings_by_year", tool_names)
        self.assertIn("active_podlings_by_year", tool_names)
        self.assertIn("active_podlings_in_year", tool_names)
        self.assertIn("completion_rate_over_time", tool_names)
        self.assertIn("completed_podlings_by_year", tool_names)
        self.assertIn("completed_podlings_in_range", tool_names)
        self.assertIn("graduated_podlings_by_year", tool_names)
        self.assertIn("retired_podlings_by_year", tool_names)
        self.assertIn("completion_count_over_time", tool_names)
        self.assertIn("time_to_retirement_over_time", tool_names)

    def test_handle_tools_call_emits_success_payload(self) -> None:
        with patch("podlings.protocol.emit") as emit_mock:
            handle_tools_call(3, {"name": "get_podling", "arguments": {"source": str(SAMPLE_XML), "name": "ExampleOne"}})

        emit_mock.assert_called_once()
        payload = emit_mock.call_args.args[0]
        self.assertEqual(payload["result"]["structuredContent"]["podling"]["name"], "ExampleOne")

    def test_tool_response_includes_structured_content_for_json_payloads(self) -> None:
        from podlings.protocol import tool_response

        response = tool_response({"ok": True})

        self.assertEqual(response["structuredContent"], {"ok": True})
        self.assertEqual(json.loads(response["content"][0]["text"]), {"ok": True})

    def test_handle_tools_call_emits_unknown_tool_error(self) -> None:
        with patch("podlings.protocol.emit") as emit_mock:
            handle_tools_call(4, {"name": "missing_tool", "arguments": {}})

        payload = emit_mock.call_args.args[0]
        self.assertEqual(payload["error"]["code"], -32602)

    def test_handle_tools_call_emits_invalid_arguments_error(self) -> None:
        with patch("podlings.protocol.emit") as emit_mock:
            handle_tools_call(5, {"name": "get_podling", "arguments": []})

        payload = emit_mock.call_args.args[0]
        self.assertEqual(payload["error"]["code"], -32602)
        self.assertEqual(payload["error"]["data"]["field"], "arguments")

    def test_handle_tools_call_requires_string_tool_name(self) -> None:
        with patch("podlings.protocol.emit") as emit_mock:
            handle_tools_call(5, {"name": 123, "arguments": {}})

        payload = emit_mock.call_args.args[0]
        self.assertEqual(payload["error"]["code"], -32602)
        self.assertEqual(payload["error"]["data"]["field"], "name")

    def test_handle_tools_call_emits_handler_exception_payload(self) -> None:
        with patch("podlings.protocol.emit") as emit_mock:
            handle_tools_call(6, {"name": "get_podling", "arguments": {"source": str(SAMPLE_XML), "name": "Missing"}})

        payload = emit_mock.call_args.args[0]
        self.assertTrue(payload["result"]["isError"])

    def test_handle_message_rejects_non_object_request(self) -> None:
        payload = handle_message("not a request")

        assert payload is not None
        self.assertEqual(payload["error"]["code"], -32600)

    def test_handle_message_rejects_missing_jsonrpc_version(self) -> None:
        payload = handle_message({"id": 1, "method": "tools/list", "params": {}})

        assert payload is not None
        self.assertEqual(payload["error"]["code"], -32600)
        self.assertEqual(payload["error"]["data"]["field"], "jsonrpc")

    def test_handle_message_rejects_non_string_method(self) -> None:
        payload = handle_message({"jsonrpc": "2.0", "id": 1, "method": 123, "params": {}})

        assert payload is not None
        self.assertEqual(payload["error"]["code"], -32600)
        self.assertEqual(payload["error"]["data"]["field"], "method")

    def test_handle_message_rejects_non_object_params(self) -> None:
        payload = handle_message({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": []})

        assert payload is not None
        self.assertEqual(payload["error"]["code"], -32602)
        self.assertEqual(payload["error"]["data"]["field"], "params")

    def test_handle_message_rejects_invalid_id_type(self) -> None:
        payload = handle_message({"jsonrpc": "2.0", "id": True, "method": "tools/list", "params": {}})

        assert payload is not None
        self.assertEqual(payload["id"], None)
        self.assertEqual(payload["error"]["code"], -32600)

    def test_handle_payload_supports_jsonrpc_batches(self) -> None:
        payload = handle_payload(
            [
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 2, "method": "unknown", "params": {}},
            ]
        )

        assert isinstance(payload, list)
        self.assertEqual(len(payload), 2)
        self.assertIn("result", payload[0])
        self.assertEqual(payload[1]["error"]["code"], -32601)

    def test_handle_payload_rejects_empty_batch(self) -> None:
        payload = handle_payload([])

        assert payload is not None
        assert not isinstance(payload, list)
        self.assertEqual(payload["error"]["code"], -32600)

    def test_main_ignores_blank_lines(self) -> None:
        with patch("podlings.protocol.sys.stdin", io.StringIO("\n")):
            self.assertEqual(main(), 0)

    def test_main_emits_initialize_response(self) -> None:
        with patch("podlings.protocol.sys.stdin", io.StringIO('{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n')):
            with patch("podlings.protocol.emit") as emit_mock:
                self.assertEqual(main(), 0)

        payload = emit_mock.call_args.args[0]
        self.assertEqual(payload["result"]["serverInfo"]["name"], "podlings-mcp")

    def test_main_ignores_initialized_notification(self) -> None:
        with patch("podlings.protocol.sys.stdin", io.StringIO('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')):
            with patch("podlings.protocol.emit") as emit_mock:
                self.assertEqual(main(), 0)

        emit_mock.assert_not_called()

    def test_main_emits_tools_list_and_call_responses(self) -> None:
        stdin = io.StringIO(
            '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}\n'
            '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_podling","arguments":{"source":"%s","name":"ExampleOne"}}}\n'
            % str(SAMPLE_XML)
        )
        with patch("podlings.protocol.sys.stdin", stdin):
            with patch("podlings.protocol.emit") as emit_mock:
                self.assertEqual(main(), 0)

        self.assertEqual(emit_mock.call_count, 2)
        self.assertIn("tools", emit_mock.call_args_list[0].args[0]["result"])
        self.assertEqual(emit_mock.call_args_list[1].args[0]["result"]["structuredContent"]["podling"]["name"], "ExampleOne")

    def test_main_emits_unknown_method_error(self) -> None:
        with patch("podlings.protocol.sys.stdin", io.StringIO('{"jsonrpc":"2.0","id":1,"method":"unknown"}\n')):
            with patch("podlings.protocol.emit") as emit_mock:
                self.assertEqual(main(), 0)

        payload = emit_mock.call_args.args[0]
        self.assertEqual(payload["error"]["code"], -32601)

    def test_main_emits_internal_error_payload(self) -> None:
        with patch("podlings.protocol.sys.stdin", io.StringIO('{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}\n')):
            with patch("podlings.protocol.list_tools_payload", side_effect=RuntimeError("boom")):
                with patch("podlings.protocol.emit") as emit_mock:
                    self.assertEqual(main(), 0)

        payload = emit_mock.call_args.args[0]
        self.assertEqual(payload["error"]["code"], -32603)
        self.assertIn("traceback", payload["error"]["data"])

    def test_main_emits_parse_error_for_malformed_json(self) -> None:
        with patch("podlings.protocol.sys.stdin", io.StringIO('{"jsonrpc":"2.0","id":1,"method":"tools/list"\n')):
            with patch("podlings.protocol.emit") as emit_mock:
                self.assertEqual(main(), 0)

        payload = emit_mock.call_args.args[0]
        self.assertEqual(payload["id"], None)
        self.assertEqual(payload["error"]["code"], -32700)

    def test_main_emits_batch_response_array(self) -> None:
        stdin = io.StringIO(
            json.dumps(
                [
                    {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                    {"jsonrpc": "2.0", "method": "notifications/initialized"},
                    {"jsonrpc": "2.0", "id": 2, "method": "missing", "params": {}},
                ]
            )
            + "\n"
        )
        with patch("podlings.protocol.sys.stdin", stdin):
            with patch("podlings.protocol.emit") as emit_mock:
                self.assertEqual(main(), 0)

        payload = emit_mock.call_args.args[0]
        self.assertIsInstance(payload, list)
        self.assertEqual(len(payload), 2)
