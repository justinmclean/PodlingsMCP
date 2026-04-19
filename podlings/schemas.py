from __future__ import annotations

from typing import Any

SOURCE_PROPERTY = {"type": "string", "description": "HTTPS URL or local path to podlings.xml"}
SPONSOR_TYPE_PROPERTY = {
    "type": "string",
    "description": "Optional sponsor type filter, defaults to incubator: incubator, project, or unknown",
}
YEAR_FILTER_PROPERTIES = {
    "start_year": {"type": "integer", "description": "Optional inclusive start year filter"},
    "end_year": {"type": "integer", "description": "Optional inclusive end year filter"},
}
YEAR_PROPERTY = {"type": "integer", "description": "Required year to inspect"}
LIST_FILTER_PROPERTIES = {
    "search": {"type": "string", "description": "Optional text search across name, description, and champion"},
    "limit": {"type": "integer", "description": "Optional maximum number of results to return"},
}
COMPLETION_STATUS_PROPERTY = {
    "type": "string",
    "description": "Optional completion status filter: graduated or retired",
}


def input_schema(properties: dict[str, Any], *, required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


def tool_definition(
    *,
    description: str,
    handler: Any,
    properties: dict[str, Any],
    required: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "description": description,
        "inputSchema": input_schema(properties, required=required),
        "handler": handler,
    }


def base_properties(*, include_sponsor_type: bool = False, include_year_filters: bool = False) -> dict[str, Any]:
    properties: dict[str, Any] = {"source": SOURCE_PROPERTY}
    if include_sponsor_type:
        properties["sponsor_type"] = SPONSOR_TYPE_PROPERTY
    if include_year_filters:
        properties.update(YEAR_FILTER_PROPERTIES)
    return properties


def list_properties(*, include_status: bool = False) -> dict[str, Any]:
    properties = base_properties(include_sponsor_type=True)
    if include_status:
        properties["status"] = {"type": "string", "description": "Optional exact status filter"}
    properties.update(LIST_FILTER_PROPERTIES)
    return properties


def timeline_properties() -> dict[str, Any]:
    return base_properties(include_sponsor_type=True, include_year_filters=True)


def year_lookup_properties() -> dict[str, Any]:
    return {
        **base_properties(include_sponsor_type=True),
        "year": YEAR_PROPERTY,
    }


def completion_lookup_properties() -> dict[str, Any]:
    return {
        **base_properties(include_sponsor_type=True),
        "year": YEAR_PROPERTY,
        "status": COMPLETION_STATUS_PROPERTY,
    }


def completion_range_properties() -> dict[str, Any]:
    return {
        **base_properties(include_sponsor_type=True, include_year_filters=True),
        "status": COMPLETION_STATUS_PROPERTY,
    }
