import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from podlings.data import (
    DEFAULT_SOURCE,
    DEFAULT_SOURCE_CACHE_TTL_SECONDS,
    _calculate_percentile,
    _classify_sponsor,
    _months_between,
    _parse_date,
    _parse_year,
    _read_source,
    _split_people,
    parse_podlings,
)
from tests.fixtures import PARSING_EDGE_CASES_XML, SAMPLE_XML, temporary_xml_file


class SponsorClassificationTests(unittest.TestCase):
    def test_classify_incubator_sponsors(self) -> None:
        self.assertEqual(_classify_sponsor("Incubator"), "incubator")
        self.assertEqual(_classify_sponsor("Apache Incubator"), "incubator")

    def test_classify_project_and_unknown_sponsors(self) -> None:
        self.assertEqual(_classify_sponsor("Apache Foo"), "project")
        self.assertEqual(_classify_sponsor(None), "unknown")

    def test_split_people_supports_multiple_shapes(self) -> None:
        self.assertEqual(_split_people(None), [])
        self.assertEqual(_split_people("A; B"), ["A", "B"])
        self.assertEqual(_split_people("A, B"), ["A", "B"])
        self.assertEqual(_split_people("Solo"), ["Solo"])


class DateHelperTests(unittest.TestCase):
    def test_parse_year_rejects_invalid_values(self) -> None:
        self.assertIsNone(_parse_year(None))
        self.assertIsNone(_parse_year("20A4-01-01"))

    def test_parse_date_rejects_invalid_values(self) -> None:
        self.assertIsNone(_parse_date(None))
        self.assertIsNone(_parse_date("2024-13-40"))

    def test_months_between_adjusts_for_partial_month(self) -> None:
        self.assertEqual(_months_between("2024-01-15", "2024-03-14"), 1)

    def test_calculate_percentile_returns_zero_for_empty_values(self) -> None:
        self.assertEqual(_calculate_percentile([], 0.5), 0.0)


class PodlingParsingTests(unittest.TestCase):
    def test_parse_podlings_extracts_nested_mentors(self) -> None:
        podlings, meta = parse_podlings(str(SAMPLE_XML))

        self.assertEqual(meta["count"], 3)
        self.assertEqual([podling.name for podling in podlings], ["ExampleOne", "ExampleThree", "ExampleTwo"])
        self.assertEqual(podlings[0].mentors, ["Mentor One", "Mentor Two"])
        self.assertEqual(podlings[1].mentors, ["Mentor Four"])
        self.assertEqual(podlings[2].mentors, ["Mentor Three"])

    def test_parse_podlings_sets_sponsor_type(self) -> None:
        podlings, _ = parse_podlings(str(SAMPLE_XML))

        self.assertEqual(podlings[0].sponsor_type, "incubator")
        self.assertEqual(podlings[1].sponsor_type, "incubator")
        self.assertEqual(podlings[2].sponsor_type, "project")

    def test_parse_podlings_raises_for_malformed_xml(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False) as handle:
            handle.write("<podlings><podling name='Broken'></podlings>")
            malformed_path = handle.name

        try:
            with self.assertRaises(Exception):
                parse_podlings(malformed_path)
        finally:
            Path(malformed_path).unlink(missing_ok=True)

    def test_read_source_supports_url_sources(self) -> None:
        class FakeHeaders:
            def get_content_charset(self) -> str:
                return "utf-8"

            def get(self, key: str) -> str | None:
                if key == "Content-Type":
                    return "application/xml"
                return None

        class FakeResponse:
            headers = FakeHeaders()

            def read(self) -> bytes:
                return b"<podlings />"

            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

        with patch("podlings.data.urllib.request.urlopen", return_value=FakeResponse()):
            body, meta = _read_source("https://example.com/podlings.xml")

        self.assertEqual(body, "<podlings />")
        self.assertEqual(meta["kind"], "url")
        self.assertFalse(meta["cached"])
        self.assertEqual(meta["content_type"], "application/xml")

    def test_read_source_uses_fresh_cache_for_default_source(self) -> None:
        with tempfile.TemporaryDirectory() as cache_dir:
            cache_path = Path(cache_dir) / "podlings.xml"
            cache_path.write_text("<podlings />", encoding="utf-8")
            now = 1_700_000_000
            cache_mtime = now - 60

            os.utime(cache_path, (cache_mtime, cache_mtime))

            with patch.dict("podlings.data.os.environ", {"PODLINGS_MCP_CACHE_DIR": cache_dir}):
                with patch("podlings.data.time.time", return_value=now):
                    with patch("podlings.data.urllib.request.urlopen") as urlopen_mock:
                        body, meta = _read_source(DEFAULT_SOURCE)

        self.assertEqual(body, "<podlings />")
        self.assertTrue(meta["cached"])
        self.assertEqual(meta["cache_age_seconds"], 60)
        urlopen_mock.assert_not_called()

    def test_read_source_refreshes_stale_default_source_cache(self) -> None:
        class FakeHeaders:
            def get_content_charset(self) -> str:
                return "utf-8"

            def get(self, key: str) -> str | None:
                if key == "Content-Type":
                    return "application/xml"
                return None

        class FakeResponse:
            headers = FakeHeaders()

            def read(self) -> bytes:
                return b"<podlings><podling name='Fresh' /></podlings>"

            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

        with tempfile.TemporaryDirectory() as cache_dir:
            cache_path = Path(cache_dir) / "podlings.xml"
            cache_path.write_text("<podlings />", encoding="utf-8")
            now = 1_700_000_000
            stale_mtime = now - DEFAULT_SOURCE_CACHE_TTL_SECONDS - 1

            os.utime(cache_path, (stale_mtime, stale_mtime))

            with patch.dict("podlings.data.os.environ", {"PODLINGS_MCP_CACHE_DIR": cache_dir}):
                with patch("podlings.data.time.time", return_value=now):
                    with patch("podlings.data.urllib.request.urlopen", return_value=FakeResponse()) as urlopen_mock:
                        body, meta = _read_source(DEFAULT_SOURCE)
                cached_body = cache_path.read_text(encoding="utf-8")

        self.assertEqual(body, "<podlings><podling name='Fresh' /></podlings>")
        self.assertEqual(cached_body, body)
        self.assertFalse(meta["cached"])
        urlopen_mock.assert_called_once()

    def test_parse_podlings_skips_nameless_podling_and_empty_mentor_nodes(self) -> None:
        with temporary_xml_file(PARSING_EDGE_CASES_XML) as xml_path:
            podlings, meta = parse_podlings(xml_path)

        self.assertEqual(meta["count"], 1)
        self.assertEqual(podlings[0].name, "Named")
        self.assertEqual(podlings[0].mentors, [])
