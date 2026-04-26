"""Helpers for loading and parsing ASF Incubator podlings XML data."""

from __future__ import annotations

import os
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

DEFAULT_SOURCE = "https://incubator.apache.org/podlings.xml"
DEFAULT_SOURCE_CACHE_TTL_SECONDS = 24 * 60 * 60
DEFAULT_SOURCE_CACHE_ENV = "PODLINGS_MCP_CACHE_DIR"
VALID_SPONSOR_TYPES = {"incubator", "project", "unknown"}


@dataclass
class Podling:
    """Normalized representation of a single podling entry."""

    name: str
    status: str | None = None
    description: str | None = None
    resource: str | None = None
    sponsor: str | None = None
    sponsor_type: str | None = None
    champion: str | None = None
    mentors: list[str] | None = None
    startdate: str | None = None
    enddate: str | None = None
    reporting_group: int | None = None
    reporting_monthly: bool | None = None
    reporting_periods: list[str] | None = None


def _is_url(value: str) -> bool:
    """Return True when the source value looks like an HTTP(S) URL."""

    parsed = urllib.parse.urlparse(value)
    return parsed.scheme in {"http", "https"}


def _default_source_cache_path() -> Path:
    """Return the cache path used for the default ASF podlings XML source."""

    cache_dir = os.environ.get(DEFAULT_SOURCE_CACHE_ENV)
    if cache_dir:
        return Path(os.path.expanduser(cache_dir)) / "podlings.xml"
    return Path.home() / ".cache" / "podlings-mcp" / "podlings.xml"


def _is_default_source(source: str) -> bool:
    """Return True when source is the default ASF podlings URL."""

    return source == DEFAULT_SOURCE


def _read_cached_default_source(source: str) -> tuple[str, dict[str, Any]] | None:
    """Return fresh cached default-source XML when available."""

    if not _is_default_source(source):
        return None

    cache_path = _default_source_cache_path()
    if not cache_path.exists():
        return None

    cache_age_seconds = max(0, int(time.time() - cache_path.stat().st_mtime))
    if cache_age_seconds > DEFAULT_SOURCE_CACHE_TTL_SECONDS:
        return None

    body = cache_path.read_text(encoding="utf-8")
    return body, {
        "source": source,
        "kind": "url",
        "cached": True,
        "cache_path": str(cache_path),
        "cache_age_seconds": cache_age_seconds,
        "size_bytes": len(body.encode("utf-8")),
    }


def _write_default_source_cache(source: str, body: str) -> None:
    """Best-effort write-through cache for the default ASF podlings XML."""

    if not _is_default_source(source):
        return

    cache_path = _default_source_cache_path()
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(body, encoding="utf-8")
    except OSError:
        return


def _normalize_text(value: str | None) -> str | None:
    """Collapse internal whitespace and normalize empty values to None."""

    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _split_people(value: str | None) -> list[str]:
    """Split a person list using the delimiters seen in podlings XML."""

    if not value:
        return []
    for delimiter in (";", ","):
        if delimiter in value:
            return [part.strip() for part in value.split(delimiter) if part.strip()]
    return [value.strip()] if value.strip() else []


def _classify_sponsor(sponsor: str | None) -> str:
    """Map raw sponsor text to the public sponsor_type values."""

    normalized = (sponsor or "").strip().lower()
    if normalized in {"incubator", "apache incubator"}:
        return "incubator"
    if normalized:
        return "project"
    return "unknown"


def _parse_year(value: str | None) -> int | None:
    """Extract a four-digit year from an ISO-like date string."""

    if not value:
        return None
    year_text = value[:4]
    if len(year_text) != 4 or not year_text.isdigit():
        return None
    return int(year_text)


def _parse_date(value: str | None) -> date | None:
    """Parse an ISO date, returning None for missing or invalid values."""

    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _months_between(start: str | None, end: str | None) -> int | None:
    """Return whole months between two ISO dates, adjusting for partial months."""

    start_date = _parse_date(start)
    end_date = _parse_date(end)
    if start_date is None or end_date is None or end_date < start_date:
        return None
    months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    if end_date.day < start_date.day:
        months -= 1
    return months


def _calculate_percentile(values: list[int], percentile: float) -> float:
    """Calculate a percentile using linear interpolation between ordered values."""

    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])

    position = (len(ordered) - 1) * percentile
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    fraction = position - lower_index
    lower_value = ordered[lower_index]
    upper_value = ordered[upper_index]
    return round(lower_value + (upper_value - lower_value) * fraction, 2)


def _build_duration_stats(values: list[int]) -> dict[str, float]:
    """Return the median and percentile stats used by duration tools."""

    return {
        "median_months_to_graduate": _calculate_percentile(values, 0.5),
        "p75_months_to_graduate": _calculate_percentile(values, 0.75),
        "p90_months_to_graduate": _calculate_percentile(values, 0.9),
    }


def _read_source(source: str) -> tuple[str, dict[str, Any]]:
    """Read podlings XML from a local file path or remote URL."""

    cached = _read_cached_default_source(source)
    if cached is not None:
        return cached

    if _is_url(source):
        with urllib.request.urlopen(source, timeout=30) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read().decode(charset, errors="replace")
            _write_default_source_cache(source, body)
            meta = {
                "source": source,
                "kind": "url",
                "cached": False,
                "content_type": response.headers.get("Content-Type"),
                "size_bytes": len(body.encode(charset, errors="ignore")),
            }
            return body, meta

    path = os.path.expanduser(source)
    with open(path, "r", encoding="utf-8") as handle:
        body = handle.read()
    meta = {
        "source": os.path.abspath(path),
        "kind": "file",
        "size_bytes": len(body.encode("utf-8")),
    }
    return body, meta


def _find_podling_nodes(root: ET.Element) -> list[ET.Element]:
    """Return the top-level podling nodes from the parsed XML tree."""

    return list(root.findall("./podling"))


def _text_from_child(node: ET.Element, *names: str) -> str | None:
    """Extract normalized text from the first matching child element."""

    lower_names = {name.lower() for name in names}
    for child in list(node):
        if child.tag.lower() in lower_names:
            return _normalize_text(child.text)
    return None


def _mentors_from_node(node: ET.Element) -> list[str]:
    """Extract mentor names from the nested mentors element when present."""

    for child in list(node):
        if child.tag.lower() != "mentors":
            continue

        mentors: list[str] = []
        for mentor in list(child):
            if mentor.tag.lower() != "mentor":
                continue
            name = _normalize_text(mentor.text)
            if name:
                mentors.append(name)

        if mentors:
            return mentors

    return []


def _parse_reporting_group(value: str | None) -> int | None:
    """Parse a reporting group value, returning None for invalid input."""

    if value is None or value not in {"1", "2", "3"}:
        return None
    return int(value)


def _reporting_from_node(node: ET.Element) -> tuple[int | None, bool | None, list[str]]:
    """Extract reporting metadata from a nested reporting element."""

    for child in list(node):
        if child.tag.lower() != "reporting":
            continue

        attrs = {str(key).lower(): _normalize_text(value) for key, value in child.attrib.items()}
        group = _parse_reporting_group(attrs.get("group"))
        monthly = attrs.get("monthly")
        periods_text = _normalize_text(child.text)
        periods = [part.strip() for part in (periods_text or "").split(",") if part.strip()]
        return group, monthly == "true", periods

    return None, None, []


def _podling_from_node(node: ET.Element) -> Podling | None:
    """Convert a raw XML node into a normalized Podling object."""

    attrs = {str(key).lower(): _normalize_text(value) for key, value in node.attrib.items()}
    name = attrs.get("name")
    if not name:
        return None

    description = _text_from_child(node, "description")
    champion = _text_from_child(node, "champion")
    sponsor = attrs.get("sponsor")
    reporting_group, reporting_monthly, reporting_periods = _reporting_from_node(node)

    return Podling(
        name=name,
        status=attrs.get("status"),
        description=description,
        resource=attrs.get("resource"),
        sponsor=sponsor,
        sponsor_type=_classify_sponsor(sponsor),
        champion=champion,
        mentors=_mentors_from_node(node),
        startdate=attrs.get("startdate"),
        enddate=attrs.get("enddate"),
        reporting_group=reporting_group,
        reporting_monthly=reporting_monthly,
        reporting_periods=reporting_periods,
    )


def parse_podlings(source: str) -> tuple[list[Podling], dict[str, Any]]:
    """Load, parse, normalize, and sort podlings from a source."""

    xml_text, meta = _read_source(source)
    root = ET.fromstring(xml_text)
    podlings = []
    for node in _find_podling_nodes(root):
        podling = _podling_from_node(node)
        if podling is not None:
            podlings.append(podling)

    podlings.sort(key=lambda item: item.name.lower())
    meta["count"] = len(podlings)
    return podlings, meta
