import json
import subprocess
import sys
import unittest
from pathlib import Path

from tests.fixtures import SAMPLE_XML

ROOT = Path(__file__).resolve().parent.parent
SERVER_SCRIPT = ROOT / "server.py"


class McpProtocolTests(unittest.TestCase):
    def _run_session(self, messages: list[dict]) -> list[dict]:
        proc = subprocess.Popen(
            [sys.executable, str(SERVER_SCRIPT)],
            cwd=str(ROOT),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            responses = []
            assert proc.stdin is not None
            assert proc.stdout is not None
            assert proc.stderr is not None

            for message in messages:
                proc.stdin.write(json.dumps(message) + "\n")
                proc.stdin.flush()
                responses.append(json.loads(proc.stdout.readline()))

            proc.stdin.close()
            proc.terminate()
            proc.wait(timeout=5)
            proc.stdout.close()
            proc.stderr.close()
            return responses
        finally:
            if proc.stdout and not proc.stdout.closed:
                proc.stdout.close()
            if proc.stderr and not proc.stderr.closed:
                proc.stderr.close()
            if proc.poll() is None:
                proc.kill()

    def test_initialize_and_tools_list(self) -> None:
        responses = self._run_session(
            [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            ]
        )

        self.assertEqual(responses[0]["result"]["serverInfo"]["name"], "podlings-mcp")
        tool_names = [tool["name"] for tool in responses[1]["result"]["tools"]]
        self.assertEqual(
            tool_names,
            [
                "list_podlings",
                "list_current_podlings",
                "list_graduated_podlings",
                "list_retired_podlings",
                "get_podling",
                "podling_stats",
                "mentor_count_stats",
                "podlings_started_over_time",
                "started_podlings_by_year",
                "active_podlings_by_year",
                "active_podlings_in_year",
                "graduation_rate_over_time",
                "completion_rate_over_time",
                "completion_count_over_time",
                "completed_podlings_by_year",
                "completed_podlings_in_range",
                "graduated_podlings_by_year",
                "retired_podlings_by_year",
                "graduation_time_over_time",
                "time_to_retirement_over_time",
                "raw_podlings_xml_info",
            ],
        )

    def test_tools_call_success(self) -> None:
        responses = self._run_session(
            [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "get_podling",
                        "arguments": {"source": str(SAMPLE_XML), "name": "ExampleOne"},
                    },
                },
            ]
        )

        payload = json.loads(responses[1]["result"]["content"][0]["text"])
        self.assertEqual(payload["podling"]["name"], "ExampleOne")
        self.assertEqual(payload["podling"]["mentors"], ["Mentor One", "Mentor Two"])

    def test_tools_call_unknown_tool_returns_jsonrpc_error(self) -> None:
        responses = self._run_session(
            [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "missing_tool", "arguments": {}}},
            ]
        )

        self.assertEqual(responses[1]["error"]["code"], -32602)
        self.assertIn("Unknown tool", responses[1]["error"]["message"])

    def test_tools_call_invalid_arguments_returns_jsonrpc_error(self) -> None:
        responses = self._run_session(
            [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "get_podling", "arguments": []}},
            ]
        )

        self.assertEqual(responses[1]["error"]["code"], -32602)
        self.assertIn("Tool arguments must be an object", responses[1]["error"]["message"])

    def test_tools_call_handler_error_returns_mcp_error_payload(self) -> None:
        responses = self._run_session(
            [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "get_podling",
                        "arguments": {"source": str(SAMPLE_XML), "name": "MissingPodling"},
                    },
                },
            ]
        )

        self.assertTrue(responses[1]["result"]["isError"])
        payload = json.loads(responses[1]["result"]["content"][0]["text"])
        self.assertFalse(payload["ok"])
        self.assertIn("MissingPodling", payload["error"])

    def test_unknown_method_returns_jsonrpc_error(self) -> None:
        responses = self._run_session(
            [
                {"jsonrpc": "2.0", "id": 1, "method": "unknown/method", "params": {}},
            ]
        )

        self.assertEqual(responses[0]["error"]["code"], -32601)
        self.assertIn("Method 'unknown/method' not found", responses[0]["error"]["message"])
