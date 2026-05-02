"""Tool handlers and shared argument helpers for the Podlings MCP server."""

from __future__ import annotations

import calendar
from collections import Counter
from dataclasses import asdict
from datetime import date
from typing import Any

from . import schemas
from .data import (
    DEFAULT_SOURCE,
    VALID_SPONSOR_TYPES,
    _build_duration_stats,
    _calculate_percentile,
    _months_between,
    _parse_date,
    _parse_year,
    parse_podlings,
)

MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
MONTH_NAME_TO_NUMBER = {name.lower(): index for index, name in enumerate(MONTH_NAMES, start=1)}
REPORTING_GROUP_MONTHS = {
    1: (1, 4, 7, 10),
    2: (2, 5, 8, 11),
    3: (3, 6, 9, 12),
}


def require_string(arguments: dict[str, Any], key: str) -> str:
    """Require a non-empty string argument and return the trimmed value."""

    value = arguments.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{key}' must be a non-empty string")
    return value.strip()


def optional_string(arguments: dict[str, Any], key: str) -> str | None:
    """Return a trimmed optional string argument."""

    value = arguments.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"'{key}' must be a string")
    stripped = value.strip()
    return stripped or None


def resolve_source(arguments: dict[str, Any]) -> str:
    """Resolve the podlings source, falling back to the ASF default URL."""

    return optional_string(arguments, "source") or DEFAULT_SOURCE


def resolve_sponsor_type(arguments: dict[str, Any], default: str = "incubator") -> str:
    """Resolve and validate sponsor_type, defaulting to incubator."""

    sponsor_type = optional_string(arguments, "sponsor_type") or default
    normalized = sponsor_type.lower()
    if normalized not in VALID_SPONSOR_TYPES:
        choices = ", ".join(sorted(VALID_SPONSOR_TYPES))
        raise ValueError(f"'sponsor_type' must be one of: {choices}")
    return normalized


def _resolve_as_of_date(arguments: dict[str, Any]) -> date:
    """Resolve the schedule inspection date, defaulting to today."""

    value = optional_string(arguments, "as_of_date")
    if value is None:
        return date.today()
    parsed = _parse_date(value)
    if parsed is None:
        raise ValueError("'as_of_date' must be an ISO date in YYYY-MM-DD format")
    return parsed


def _third_wednesday(year: int, month: int) -> date:
    """Return the third Wednesday for the given month."""

    wednesdays = [day for week in calendar.monthcalendar(year, month) if (day := week[calendar.WEDNESDAY]) != 0]
    return date(year, month, wednesdays[2])


def _resolve_report_month(arguments: dict[str, Any], *, default_date: date) -> date:
    """Resolve the reporting month, defaulting to the active reporting cycle."""

    value = optional_string(arguments, "report_month")
    if value is None:
        cutoff = _third_wednesday(default_date.year, default_date.month)
        if default_date > cutoff:
            if default_date.month == 12:
                return date(default_date.year + 1, 1, 1)
            return date(default_date.year, default_date.month + 1, 1)
        return default_date.replace(day=1)

    parts = value.split("-")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise ValueError("'report_month' must be in YYYY-MM format")

    year, month = int(parts[0]), int(parts[1])
    if month < 1 or month > 12:
        raise ValueError("'report_month' must be in YYYY-MM format")
    return date(year, month, 1)


def _resolve_year_filters(arguments: dict[str, Any]) -> tuple[int | None, int | None]:
    """Validate optional inclusive year filters used by timeline tools."""

    start_year = _resolve_optional_integer(arguments, "start_year")
    end_year = _resolve_optional_integer(arguments, "end_year")
    if start_year is not None and end_year is not None and start_year > end_year:
        raise ValueError("'start_year' must be less than or equal to 'end_year'")
    return start_year, end_year


def _resolve_year(arguments: dict[str, Any], key: str = "year") -> int:
    """Require a single integer year argument."""

    value = _resolve_optional_integer(arguments, key)
    if value is None:
        raise ValueError(f"'{key}' must be an integer")
    return value


def _resolve_optional_integer(arguments: dict[str, Any], key: str) -> int | None:
    """Return an optional integer while rejecting bools and string coercion."""

    value = arguments.get(key)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"'{key}' must be an integer")
    return value


def _resolve_completion_status(arguments: dict[str, Any]) -> str | None:
    """Validate an optional completed-status filter."""

    status = optional_string(arguments, "status")
    if status is None:
        return None
    normalized = status.lower()
    if normalized not in {"graduated", "retired"}:
        raise ValueError("'status' must be one of: graduated, retired")
    return normalized


def _resolve_required_year_range(arguments: dict[str, Any]) -> tuple[int, int]:
    """Require an inclusive year range and validate the ordering."""

    start_year = _resolve_optional_integer(arguments, "start_year")
    end_year = _resolve_optional_integer(arguments, "end_year")
    if start_year is None:
        raise ValueError("'start_year' must be an integer")
    if end_year is None:
        raise ValueError("'end_year' must be an integer")
    if start_year > end_year:
        raise ValueError("'start_year' must be less than or equal to 'end_year'")
    return start_year, end_year


def _resolve_limit(arguments: dict[str, Any]) -> int | None:
    """Validate an optional result limit."""

    return _resolve_optional_integer(arguments, "limit")


def _filter_podlings(
    podlings: list[Any],
    *,
    sponsor_type: str,
    statuses: set[str] | None = None,
) -> list[Any]:
    """Filter podlings by sponsor_type and, optionally, status set."""

    filtered = [item for item in podlings if (item.sponsor_type or "unknown") == sponsor_type]
    if statuses is None:
        return filtered
    return [item for item in filtered if (item.status or "").lower() in statuses]


def _period_payload(year: int, month: int) -> dict[str, Any]:
    """Build a normalized reporting-period payload."""

    last_day = calendar.monthrange(year, month)[1]
    return {
        "year": year,
        "month": month,
        "label": f"{MONTH_NAMES[month - 1]} {year}",
        "start_date": f"{year:04d}-{month:02d}-01",
        "end_date": f"{year:04d}-{month:02d}-{last_day:02d}",
    }


def _monthly_period_entries(item: Any, anchor: date) -> list[dict[str, Any]]:
    """Return nearby monthly reporting periods for a monthly podling."""

    start = _parse_date(item.startdate) or anchor
    start_index = start.year * 12 + start.month - 1
    anchor_index = anchor.year * 12 + anchor.month - 1
    first_index = max(start_index, anchor_index - 12)
    last_index = anchor_index + 12

    entries = []
    for month_index in range(first_index, last_index + 1):
        year, month_zero_based = divmod(month_index, 12)
        entries.append(_period_payload(year, month_zero_based + 1))
    return entries


def _reporting_period_entries(item: Any) -> list[dict[str, Any]]:
    """Return explicit monthly reporting periods derived from podlings.xml."""

    periods = item.reporting_periods or []
    start = _parse_date(item.startdate)
    if not periods or start is None:
        return []

    months = [MONTH_NAME_TO_NUMBER.get(period.lower()) for period in periods]
    if any(month is None for month in months):
        return []

    entries: list[dict[str, Any]] = []
    first_month = months[0]
    assert first_month is not None
    current_year = start.year + (1 if first_month <= start.month else 0)
    previous_month = 0

    for raw_month in months:
        assert raw_month is not None
        if previous_month and raw_month < previous_month:
            current_year += 1
        entries.append(_period_payload(current_year, raw_month))
        previous_month = raw_month

    return entries


def _quarterly_period_entries(group: int | None, as_of: date) -> list[dict[str, Any]]:
    """Return nearby quarterly reporting periods for the given reporting group."""

    months = REPORTING_GROUP_MONTHS.get(group or 0)
    if months is None:
        return []

    entries = []
    for year in range(as_of.year - 1, as_of.year + 2):
        for month in months:
            entries.append(_period_payload(year, month))
    return entries


def _latest_period_on_or_before(entries: list[dict[str, Any]], as_of: date) -> dict[str, Any] | None:
    """Return the latest reporting period whose month starts on or before as_of."""

    latest: dict[str, Any] | None = None
    for entry in entries:
        if entry["start_date"] <= as_of.isoformat():
            latest = entry
    return latest


def _next_period_for(entries: list[dict[str, Any]], as_of: date) -> dict[str, Any] | None:
    """Return the current or next reporting period relative to as_of."""

    current_month_start = as_of.replace(day=1).isoformat()
    for entry in entries:
        if entry["start_date"] >= current_month_start or entry["end_date"] >= as_of.isoformat():
            return entry
    return None


def _reporting_record(item: Any, *, report_month: date) -> dict[str, Any]:
    """Build one reporting-schedule record for a podling."""

    status = (item.status or "").lower()
    cadence = "monthly" if item.reporting_monthly else "quarterly" if item.reporting_group in REPORTING_GROUP_MONTHS else None
    due_this_month = False
    latest_expected: dict[str, Any] | None = None
    next_expected: dict[str, Any] | None = None

    if status == "current" and cadence == "monthly":
        explicit_periods = _reporting_period_entries(item)
        schedule_periods = explicit_periods or _monthly_period_entries(item, report_month)
        due_this_month = any(entry["year"] == report_month.year and entry["month"] == report_month.month for entry in schedule_periods)
        latest_expected = _latest_period_on_or_before(schedule_periods, report_month)
        next_expected = _next_period_for(schedule_periods, report_month)
    elif status == "current" and cadence == "quarterly":
        quarterly_periods = _quarterly_period_entries(item.reporting_group, report_month)
        due_this_month = report_month.month in REPORTING_GROUP_MONTHS.get(item.reporting_group or 0, ())
        latest_expected = _latest_period_on_or_before(quarterly_periods, report_month)
        next_expected = _next_period_for(quarterly_periods, report_month)

    return {
        "name": item.name,
        "status": item.status,
        "sponsor_type": item.sponsor_type,
        "reporting_applicable": status == "current" and cadence is not None,
        "reporting_group": item.reporting_group,
        "reporting_monthly": item.reporting_monthly,
        "reporting_periods": item.reporting_periods or [],
        "expected_cadence": cadence,
        "latest_expected_report_period_as_of": latest_expected,
        "next_expected_report_period": next_expected,
        "due_this_month": due_this_month,
    }


def _build_started_timeline(
    podlings: list[Any],
    *,
    start_year: int | None,
    end_year: int | None,
) -> list[dict[str, Any]]:
    """Build yearly start counts based on podling start dates."""

    yearly: dict[int, dict[str, Any]] = {}

    for item in podlings:
        year = _parse_year(item.startdate)
        if year is None:
            continue
        if start_year is not None and year < start_year:
            continue
        if end_year is not None and year > end_year:
            continue

        bucket = yearly.setdefault(year, {"year": year, "started": 0})
        bucket["started"] += 1

    return [yearly[year] for year in sorted(yearly)]


def _build_completion_timeline(
    podlings: list[Any],
    *,
    start_year: int | None,
    end_year: int | None,
    include_rate: bool = False,
) -> list[dict[str, Any]]:
    """Build yearly completion buckets, optionally adding graduation rate."""

    yearly: dict[int, dict[str, Any]] = {}

    for item in podlings:
        year = _parse_year(item.enddate)
        status = (item.status or "").lower()
        if year is None or status not in {"graduated", "retired"}:
            continue
        if start_year is not None and year < start_year:
            continue
        if end_year is not None and year > end_year:
            continue

        bucket = yearly.setdefault(
            year,
            {
                "year": year,
                "graduated": 0,
                "retired": 0,
                "completed": 0,
            },
        )
        bucket[status] += 1
        bucket["completed"] += 1

    timeline = [yearly[year] for year in sorted(yearly)]
    if include_rate:
        for bucket in timeline:
            bucket["graduation_rate"] = round(bucket["graduated"] / bucket["completed"], 3) if bucket["completed"] else 0.0
    return timeline


def _is_active_in_year(item: Any, year: int) -> bool:
    """Return True when a podling was active at any point during the given year."""

    start_year = _parse_year(item.startdate)
    end_year = _parse_year(item.enddate)
    if start_year is None or start_year > year:
        return False
    if end_year is not None and end_year < year:
        return False
    return True


def _resolve_active_year_bounds(podlings: list[Any], *, start_year: int | None, end_year: int | None) -> tuple[int | None, int | None]:
    """Pick timeline bounds for active views when filters are omitted."""

    available_start_years = [_parse_year(item.startdate) for item in podlings]
    valid_start_years = [year for year in available_start_years if year is not None]
    if not valid_start_years:
        return start_year, end_year

    resolved_start_year = start_year if start_year is not None else min(valid_start_years)

    if end_year is not None:
        resolved_end_year = end_year
    else:
        valid_end_years = [
            max(filter(None, [_parse_year(item.startdate), _parse_year(item.enddate)]))  # type: ignore[arg-type]
            for item in podlings
            if _parse_year(item.startdate) is not None or _parse_year(item.enddate) is not None
        ]
        resolved_end_year = max(valid_end_years) if valid_end_years else resolved_start_year

    return resolved_start_year, resolved_end_year


def _build_active_timeline(
    podlings: list[Any],
    *,
    start_year: int | None,
    end_year: int | None,
) -> list[dict[str, Any]]:
    """Build yearly active-population counts."""

    resolved_start_year, resolved_end_year = _resolve_active_year_bounds(podlings, start_year=start_year, end_year=end_year)
    if resolved_start_year is None or resolved_end_year is None or resolved_start_year > resolved_end_year:
        return []

    timeline = []
    for year in range(resolved_start_year, resolved_end_year + 1):
        active = sum(1 for item in podlings if _is_active_in_year(item, year))
        if active:
            timeline.append({"year": year, "active": active})
    return timeline


def _completion_name_lists(podlings: list[Any], *, predicate: Any, status_filter: str | None) -> tuple[list[str], list[str], list[str]]:
    """Collect graduated, retired, and combined completion name lists."""

    graduated = sorted(
        [item.name for item in podlings if predicate(item) and (item.status or "").lower() == "graduated"],
        key=str.lower,
    )
    retired = sorted(
        [item.name for item in podlings if predicate(item) and (item.status or "").lower() == "retired"],
        key=str.lower,
    )

    if status_filter == "graduated":
        completed = list(graduated)
    elif status_filter == "retired":
        completed = list(retired)
    else:
        completed = sorted(graduated + retired, key=str.lower)

    return graduated, retired, completed


def _duration_field_names(*, count_name: str, action_name: str) -> dict[str, str]:
    """Return the output field names for a duration-based timeline."""

    return {
        "count": count_name,
        "total": f"total_months_to_{action_name}",
        "average": f"average_months_to_{action_name}",
        "median": f"median_months_to_{action_name}",
        "p75": f"p75_months_to_{action_name}",
        "p90": f"p90_months_to_{action_name}",
    }


def _duration_bucket(year: int, *, count_name: str, action_name: str) -> dict[str, Any]:
    """Create an empty yearly bucket for duration analytics."""

    fields = _duration_field_names(count_name=count_name, action_name=action_name)
    return {
        "year": year,
        fields["count"]: 0,
        fields["total"]: 0,
        fields["average"]: 0.0,
        fields["median"]: 0.0,
        fields["p75"]: 0.0,
        fields["p90"]: 0.0,
        "_durations": [],
    }


def _apply_duration_stats(bucket: dict[str, Any], *, count_name: str, action_name: str) -> None:
    """Finalize average and percentile fields for a duration bucket."""

    fields = _duration_field_names(count_name=count_name, action_name=action_name)
    bucket[fields["average"]] = round(bucket[fields["total"]] / bucket[fields["count"]], 2) if bucket[fields["count"]] else 0.0
    duration_stats = _build_duration_stats(bucket["_durations"])
    bucket[fields["median"]] = duration_stats["median_months_to_graduate"]
    bucket[fields["p75"]] = duration_stats["p75_months_to_graduate"]
    bucket[fields["p90"]] = duration_stats["p90_months_to_graduate"]
    del bucket["_durations"]


def _build_duration_timeline(
    podlings: list[Any],
    *,
    status: str,
    count_name: str,
    action_name: str,
    start_year: int | None,
    end_year: int | None,
) -> tuple[list[dict[str, Any]], list[int]]:
    """Build a yearly duration timeline plus the raw durations used overall."""

    fields = _duration_field_names(count_name=count_name, action_name=action_name)
    yearly: dict[int, dict[str, Any]] = {}
    all_durations: list[int] = []

    for item in podlings:
        if (item.status or "").lower() != status:
            continue

        year = _parse_year(item.enddate)
        months = _months_between(item.startdate, item.enddate)
        if year is None or months is None:
            continue
        if start_year is not None and year < start_year:
            continue
        if end_year is not None and year > end_year:
            continue

        bucket = yearly.setdefault(year, _duration_bucket(year, count_name=count_name, action_name=action_name))
        bucket[fields["count"]] += 1
        bucket[fields["total"]] += months
        bucket["_durations"].append(months)
        all_durations.append(months)

    timeline = []
    for year in sorted(yearly):
        bucket = yearly[year]
        _apply_duration_stats(bucket, count_name=count_name, action_name=action_name)
        timeline.append(bucket)

    return timeline, all_durations


def tool_list_podlings(arguments: dict[str, Any]) -> dict[str, Any]:
    """List podlings with optional status, sponsor, search, and limit filters."""

    source = resolve_source(arguments)
    status = optional_string(arguments, "status")
    sponsor_type = resolve_sponsor_type(arguments)
    search = optional_string(arguments, "search")
    limit = _resolve_limit(arguments)

    podlings, meta = parse_podlings(source)

    if status:
        podlings = [p for p in podlings if (p.status or "").lower() == status.lower()]

    podlings = [p for p in podlings if (p.sponsor_type or "unknown") == sponsor_type]

    if search:
        needle = search.lower()
        podlings = [
            p
            for p in podlings
            if needle in p.name.lower() or needle in (p.description or "").lower() or needle in (p.champion or "").lower()
        ]

    limited = podlings if limit is None else podlings[: max(limit, 0)]
    return {
        "source": meta,
        "returned": len(limited),
        "total_matching": len(podlings),
        "podlings": [asdict(item) for item in limited],
    }


def _list_by_status(arguments: dict[str, Any], status: str) -> dict[str, Any]:
    """Reuse the generic list handler for a fixed status-specific tool."""

    updated_arguments = dict(arguments)
    updated_arguments["status"] = status
    return tool_list_podlings(updated_arguments)


def tool_get_podling(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return one podling by case-insensitive name match."""

    source = resolve_source(arguments)
    name = require_string(arguments, "name")

    podlings, meta = parse_podlings(source)
    for podling in podlings:
        if podling.name.lower() == name.lower():
            return {
                "source": meta,
                "podling": asdict(podling),
            }

    raise ValueError(f"Podling '{name}' not found")


def tool_list_current_podlings(arguments: dict[str, Any]) -> dict[str, Any]:
    """List podlings whose current status is current."""

    return _list_by_status(arguments, "current")


def tool_list_graduated_podlings(arguments: dict[str, Any]) -> dict[str, Any]:
    """List podlings whose current status is graduated."""

    return _list_by_status(arguments, "graduated")


def tool_list_retired_podlings(arguments: dict[str, Any]) -> dict[str, Any]:
    """List podlings whose current status is retired."""

    return _list_by_status(arguments, "retired")


def tool_podling_stats(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return aggregate counts and coverage stats for filtered podlings."""

    source = resolve_source(arguments)
    sponsor_type = resolve_sponsor_type(arguments)
    podlings, meta = parse_podlings(source)
    podlings = _filter_podlings(podlings, sponsor_type=sponsor_type)

    status_counts = Counter((item.status or "unknown").lower() for item in podlings)
    sponsor_type_counts = Counter(item.sponsor_type or "unknown" for item in podlings)
    mentor_counts = [len(item.mentors or []) for item in podlings]
    incubator_sponsored = [item for item in podlings if item.sponsor_type == "incubator"]
    project_sponsored = [item for item in podlings if item.sponsor_type == "project"]

    return {
        "source": meta,
        "sponsor_type": sponsor_type,
        "total_podlings": len(podlings),
        "status_counts": dict(status_counts),
        "sponsor_type_counts": dict(sponsor_type_counts),
        "incubator_sponsored_podlings": len(incubator_sponsored),
        "project_sponsored_podlings": len(project_sponsored),
        "with_description": sum(1 for item in podlings if item.description),
        "with_sponsor": sum(1 for item in podlings if item.sponsor),
        "with_champion": sum(1 for item in podlings if item.champion),
        "average_mentor_count": round(sum(mentor_counts) / len(mentor_counts), 2) if mentor_counts else 0.0,
    }


def tool_mentor_count_stats(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return mentor-count coverage and distribution stats for filtered podlings."""

    source = resolve_source(arguments)
    sponsor_type = resolve_sponsor_type(arguments)
    podlings, meta = parse_podlings(source)
    podlings = _filter_podlings(podlings, sponsor_type=sponsor_type)

    mentor_counts = [len(item.mentors or []) for item in podlings]

    return {
        "source": meta,
        "sponsor_type": sponsor_type,
        "total_podlings": len(podlings),
        "podlings_with_mentors": sum(1 for count in mentor_counts if count > 0),
        "podlings_without_mentors": sum(1 for count in mentor_counts if count == 0),
        "total_mentors_listed": sum(mentor_counts),
        "average_mentor_count": round(sum(mentor_counts) / len(mentor_counts), 2) if mentor_counts else 0.0,
        "median_mentor_count": _calculate_percentile(mentor_counts, 0.5),
        "p75_mentor_count": _calculate_percentile(mentor_counts, 0.75),
        "max_mentor_count": max(mentor_counts) if mentor_counts else 0,
    }


def tool_podlings_started_over_time(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return yearly podling start counts based on start dates."""

    source = resolve_source(arguments)
    start_year, end_year = _resolve_year_filters(arguments)
    sponsor_type = resolve_sponsor_type(arguments)

    podlings, meta = parse_podlings(source)
    podlings = _filter_podlings(podlings, sponsor_type=sponsor_type)
    timeline = _build_started_timeline(podlings, start_year=start_year, end_year=end_year)

    return {
        "source": meta,
        "years": timeline,
        "overall_started": sum(item["started"] for item in timeline),
    }


def tool_started_podlings_by_year(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return the podlings that started in a given year."""

    source = resolve_source(arguments)
    year = _resolve_year(arguments)
    sponsor_type = resolve_sponsor_type(arguments)

    podlings, meta = parse_podlings(source)
    podlings = _filter_podlings(podlings, sponsor_type=sponsor_type)
    started = sorted([item.name for item in podlings if _parse_year(item.startdate) == year], key=str.lower)

    return {
        "source": meta,
        "year": year,
        "sponsor_type": sponsor_type,
        "started": started,
        "started_count": len(started),
    }


def tool_active_podlings_by_year(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return yearly active-podling counts based on lifecycle span."""

    source = resolve_source(arguments)
    start_year, end_year = _resolve_year_filters(arguments)
    sponsor_type = resolve_sponsor_type(arguments)

    podlings, meta = parse_podlings(source)
    podlings = _filter_podlings(podlings, sponsor_type=sponsor_type)
    timeline = _build_active_timeline(podlings, start_year=start_year, end_year=end_year)

    return {
        "source": meta,
        "years": timeline,
        "overall_active_years": len(timeline),
        "peak_active": max((item["active"] for item in timeline), default=0),
    }


def tool_active_podlings_in_year(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return the podlings that were active during a specific year."""

    source = resolve_source(arguments)
    year = _resolve_year(arguments)
    sponsor_type = resolve_sponsor_type(arguments)

    podlings, meta = parse_podlings(source)
    podlings = _filter_podlings(podlings, sponsor_type=sponsor_type)
    active = sorted([item.name for item in podlings if _is_active_in_year(item, year)], key=str.lower)

    return {
        "source": meta,
        "year": year,
        "sponsor_type": sponsor_type,
        "active": active,
        "active_count": len(active),
    }


def tool_graduation_rate_over_time(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return yearly completed counts plus graduation rate by end year."""

    source = resolve_source(arguments)
    start_year, end_year = _resolve_year_filters(arguments)
    sponsor_type = resolve_sponsor_type(arguments)

    podlings, meta = parse_podlings(source)
    podlings = _filter_podlings(podlings, sponsor_type=sponsor_type, statuses={"graduated", "retired"})
    timeline = _build_completion_timeline(podlings, start_year=start_year, end_year=end_year, include_rate=True)

    return {
        "source": meta,
        "years": timeline,
        "overall_completed": sum(item["completed"] for item in timeline),
        "overall_graduated": sum(item["graduated"] for item in timeline),
        "overall_retired": sum(item["retired"] for item in timeline),
        "overall_graduation_rate": round(
            sum(item["graduated"] for item in timeline) / sum(item["completed"] for item in timeline),
            3,
        )
        if timeline and sum(item["completed"] for item in timeline)
        else 0.0,
    }


def tool_completion_rate_over_time(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return yearly completion rate using completed divided by active population."""

    source = resolve_source(arguments)
    start_year, end_year = _resolve_year_filters(arguments)
    sponsor_type = resolve_sponsor_type(arguments)

    podlings, meta = parse_podlings(source)
    podlings = _filter_podlings(podlings, sponsor_type=sponsor_type)
    active_timeline = {item["year"]: item["active"] for item in _build_active_timeline(podlings, start_year=start_year, end_year=end_year)}
    completion_timeline = {item["year"]: item for item in _build_completion_timeline(podlings, start_year=start_year, end_year=end_year)}

    years = sorted(set(active_timeline) | set(completion_timeline))
    timeline = []
    for year in years:
        active = active_timeline.get(year, 0)
        completed_bucket = completion_timeline.get(year, {"graduated": 0, "retired": 0, "completed": 0})
        completed = completed_bucket["completed"]
        timeline.append(
            {
                "year": year,
                "active": active,
                "graduated": completed_bucket["graduated"],
                "retired": completed_bucket["retired"],
                "completed": completed,
                "completion_rate": round(completed / active, 3) if active else 0.0,
            }
        )

    return {
        "source": meta,
        "years": timeline,
        "overall_active": sum(item["active"] for item in timeline),
        "overall_completed": sum(item["completed"] for item in timeline),
        "overall_completion_rate": round(
            sum(item["completed"] for item in timeline) / sum(item["active"] for item in timeline),
            3,
        )
        if timeline and sum(item["active"] for item in timeline)
        else 0.0,
    }


def tool_completion_count_over_time(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return yearly completed counts split into graduated and retired outcomes."""

    source = resolve_source(arguments)
    start_year, end_year = _resolve_year_filters(arguments)
    sponsor_type = resolve_sponsor_type(arguments)

    podlings, meta = parse_podlings(source)
    podlings = _filter_podlings(podlings, sponsor_type=sponsor_type, statuses={"graduated", "retired"})
    timeline = _build_completion_timeline(podlings, start_year=start_year, end_year=end_year)

    return {
        "source": meta,
        "years": timeline,
        "overall_completed": sum(item["completed"] for item in timeline),
        "overall_graduated": sum(item["graduated"] for item in timeline),
        "overall_retired": sum(item["retired"] for item in timeline),
    }


def tool_completed_podlings_by_year(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return the specific podling names that completed in a given year."""

    source = resolve_source(arguments)
    year = _resolve_year(arguments)
    sponsor_type = resolve_sponsor_type(arguments)
    status_filter = _resolve_completion_status(arguments)

    podlings, meta = parse_podlings(source)
    podlings = _filter_podlings(podlings, sponsor_type=sponsor_type, statuses={"graduated", "retired"})
    graduated, retired, completed = _completion_name_lists(
        podlings, predicate=lambda item: _parse_year(item.enddate) == year, status_filter=status_filter
    )

    return {
        "source": meta,
        "year": year,
        "sponsor_type": sponsor_type,
        "status_filter": status_filter or "all",
        "graduated": graduated,
        "retired": retired,
        "completed": completed,
        "completed_count": len(completed),
    }


def tool_completed_podlings_in_range(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return podlings that completed within an inclusive year range."""

    source = resolve_source(arguments)
    start_year, end_year = _resolve_required_year_range(arguments)
    sponsor_type = resolve_sponsor_type(arguments)
    status_filter = _resolve_completion_status(arguments)

    podlings, meta = parse_podlings(source)
    podlings = _filter_podlings(podlings, sponsor_type=sponsor_type, statuses={"graduated", "retired"})
    graduated, retired, completed = _completion_name_lists(
        podlings,
        predicate=lambda item: (completion_year := _parse_year(item.enddate)) is not None and start_year <= completion_year <= end_year,
        status_filter=status_filter,
    )

    return {
        "source": meta,
        "start_year": start_year,
        "end_year": end_year,
        "sponsor_type": sponsor_type,
        "status_filter": status_filter or "all",
        "graduated": graduated,
        "retired": retired,
        "completed": completed,
        "completed_count": len(completed),
    }


def tool_graduated_podlings_by_year(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return the podlings that graduated in a given year."""

    updated_arguments = dict(arguments)
    updated_arguments["status"] = "graduated"
    return tool_completed_podlings_by_year(updated_arguments)


def tool_retired_podlings_by_year(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return the podlings that retired in a given year."""

    updated_arguments = dict(arguments)
    updated_arguments["status"] = "retired"
    return tool_completed_podlings_by_year(updated_arguments)


def tool_graduation_time_over_time(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return yearly graduation timing stats based on start and end dates."""

    source = resolve_source(arguments)
    start_year, end_year = _resolve_year_filters(arguments)
    sponsor_type = resolve_sponsor_type(arguments)

    podlings, meta = parse_podlings(source)
    podlings = _filter_podlings(podlings, sponsor_type=sponsor_type, statuses={"graduated"})
    timeline, all_durations = _build_duration_timeline(
        podlings,
        status="graduated",
        count_name="graduated",
        action_name="graduate",
        start_year=start_year,
        end_year=end_year,
    )

    overall_graduated = sum(item["graduated"] for item in timeline)
    overall_total_months = sum(item["total_months_to_graduate"] for item in timeline)

    return {
        "source": meta,
        "years": timeline,
        "overall_graduated": overall_graduated,
        "overall_total_months_to_graduate": overall_total_months,
        "overall_average_months_to_graduate": round(overall_total_months / overall_graduated, 2) if overall_graduated else 0.0,
        **_build_duration_stats(all_durations),
    }


def tool_time_to_retirement_over_time(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return yearly retirement timing stats based on start and end dates."""

    source = resolve_source(arguments)
    start_year, end_year = _resolve_year_filters(arguments)
    sponsor_type = resolve_sponsor_type(arguments)

    podlings, meta = parse_podlings(source)
    podlings = _filter_podlings(podlings, sponsor_type=sponsor_type, statuses={"retired"})
    timeline, all_durations = _build_duration_timeline(
        podlings,
        status="retired",
        count_name="retired",
        action_name="retire",
        start_year=start_year,
        end_year=end_year,
    )

    overall_retired = sum(item["retired"] for item in timeline)
    overall_total_months = sum(item["total_months_to_retire"] for item in timeline)
    overall_stats = _build_duration_stats(all_durations)

    return {
        "source": meta,
        "years": timeline,
        "overall_retired": overall_retired,
        "overall_total_months_to_retire": overall_total_months,
        "overall_average_months_to_retire": round(overall_total_months / overall_retired, 2) if overall_retired else 0.0,
        "median_months_to_retire": overall_stats["median_months_to_graduate"],
        "p75_months_to_retire": overall_stats["p75_months_to_graduate"],
        "p90_months_to_retire": overall_stats["p90_months_to_graduate"],
    }


def tool_reporting_schedule(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return reporting cadence and next-expected schedule details for podlings."""

    source = resolve_source(arguments)
    sponsor_type = resolve_sponsor_type(arguments)
    as_of = _resolve_as_of_date(arguments)
    report_month = _resolve_report_month(arguments, default_date=as_of)
    name = optional_string(arguments, "name")
    due_this_month_filter = arguments.get("due_this_month")
    if due_this_month_filter is not None and not isinstance(due_this_month_filter, bool):
        raise ValueError("'due_this_month' must be a boolean")

    podlings, meta = parse_podlings(source)
    podlings = _filter_podlings(podlings, sponsor_type=sponsor_type)

    if name is None:
        podlings = [item for item in podlings if (item.status or "").lower() == "current"]
    else:
        podlings = [item for item in podlings if item.name.lower() == name.lower()]
        if not podlings:
            raise ValueError(f"Podling '{name}' not found")

    records = [_reporting_record(item, report_month=report_month) for item in podlings]
    total_matching = len(records)

    if due_this_month_filter is not None:
        records = [record for record in records if record["due_this_month"] is due_this_month_filter]

    return {
        "source": meta,
        "as_of_date": as_of.isoformat(),
        "report_month": f"{report_month.year:04d}-{report_month.month:02d}",
        "sponsor_type": sponsor_type,
        "returned": len(records),
        "total_matching": total_matching,
        "podlings": records,
    }


def tool_raw_podlings_xml_info(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return source metadata plus a small parsed preview for troubleshooting."""

    source = resolve_source(arguments)
    podlings, meta = parse_podlings(source)
    preview = [asdict(item) for item in podlings[:5]]
    return {
        "source": meta,
        "preview": preview,
    }


TOOLS: dict[str, dict[str, Any]] = {
    "list_podlings": schemas.tool_definition(
        description="List ASF Incubator podlings from podlings.xml with optional filtering.",
        handler=tool_list_podlings,
        properties=schemas.list_properties(include_status=True),
    ),
    "list_current_podlings": schemas.tool_definition(
        description="List current podlings.",
        handler=tool_list_current_podlings,
        properties=schemas.list_properties(),
    ),
    "list_graduated_podlings": schemas.tool_definition(
        description="List graduated podlings.",
        handler=tool_list_graduated_podlings,
        properties=schemas.list_properties(),
    ),
    "list_retired_podlings": schemas.tool_definition(
        description="List retired podlings.",
        handler=tool_list_retired_podlings,
        properties=schemas.list_properties(),
    ),
    "get_podling": schemas.tool_definition(
        description="Return details for a single podling by name.",
        handler=tool_get_podling,
        properties={
            **schemas.base_properties(),
            "name": {"type": "string", "description": "Podling name"},
        },
        required=["name"],
    ),
    "podling_stats": schemas.tool_definition(
        description="Return summary statistics for a podlings.xml source.",
        handler=tool_podling_stats,
        properties=schemas.base_properties(include_sponsor_type=True),
    ),
    "mentor_count_stats": schemas.tool_definition(
        description="Return mentor coverage and mentor-count distribution stats for a podlings.xml source.",
        handler=tool_mentor_count_stats,
        properties=schemas.base_properties(include_sponsor_type=True),
    ),
    "podlings_started_over_time": schemas.tool_definition(
        description="Return yearly podling start counts based on start dates.",
        handler=tool_podlings_started_over_time,
        properties=schemas.timeline_properties(),
    ),
    "started_podlings_by_year": schemas.tool_definition(
        description="Return the podlings that started in a specific year.",
        handler=tool_started_podlings_by_year,
        properties=schemas.year_lookup_properties(),
        required=["year"],
    ),
    "active_podlings_by_year": schemas.tool_definition(
        description="Return yearly active-podling counts based on lifecycle span.",
        handler=tool_active_podlings_by_year,
        properties=schemas.timeline_properties(),
    ),
    "active_podlings_in_year": schemas.tool_definition(
        description="Return the podlings that were active during a specific year.",
        handler=tool_active_podlings_in_year,
        properties=schemas.year_lookup_properties(),
        required=["year"],
    ),
    "graduation_rate_over_time": schemas.tool_definition(
        description="Return yearly graduation and retirement counts plus graduation rate based on podling end dates.",
        handler=tool_graduation_rate_over_time,
        properties=schemas.timeline_properties(),
    ),
    "completion_rate_over_time": schemas.tool_definition(
        description="Return yearly completion rate using completed outcomes divided by active population.",
        handler=tool_completion_rate_over_time,
        properties=schemas.timeline_properties(),
    ),
    "completion_count_over_time": schemas.tool_definition(
        description="Return yearly completed podling counts based on end dates, split into graduated and retired outcomes.",
        handler=tool_completion_count_over_time,
        properties=schemas.timeline_properties(),
    ),
    "completed_podlings_by_year": schemas.tool_definition(
        description="Return the podlings that completed in a specific year, split into graduated and retired outcomes.",
        handler=tool_completed_podlings_by_year,
        properties=schemas.completion_lookup_properties(),
        required=["year"],
    ),
    "completed_podlings_in_range": schemas.tool_definition(
        description="Return the podlings that completed within an inclusive year range.",
        handler=tool_completed_podlings_in_range,
        properties=schemas.completion_range_properties(),
        required=["start_year", "end_year"],
    ),
    "graduated_podlings_by_year": schemas.tool_definition(
        description="Return the podlings that graduated in a specific year.",
        handler=tool_graduated_podlings_by_year,
        properties=schemas.completion_lookup_properties(),
        required=["year"],
    ),
    "retired_podlings_by_year": schemas.tool_definition(
        description="Return the podlings that retired in a specific year.",
        handler=tool_retired_podlings_by_year,
        properties=schemas.completion_lookup_properties(),
        required=["year"],
    ),
    "graduation_time_over_time": schemas.tool_definition(
        description="Return yearly average incubation time for graduated podlings based on start and end dates.",
        handler=tool_graduation_time_over_time,
        properties=schemas.timeline_properties(),
    ),
    "time_to_retirement_over_time": schemas.tool_definition(
        description="Return yearly retirement timing stats based on podling start and end dates.",
        handler=tool_time_to_retirement_over_time,
        properties=schemas.timeline_properties(),
    ),
    "reporting_schedule": schemas.tool_definition(
        description="Return expected reporting cadence, due-this-month status, and next expected reporting period for podlings.",
        handler=tool_reporting_schedule,
        properties=schemas.reporting_schedule_properties(),
    ),
    "raw_podlings_xml_info": schemas.tool_definition(
        description="Return parsing metadata and a small preview of podlings.xml content.",
        handler=tool_raw_podlings_xml_info,
        properties=schemas.base_properties(),
    ),
}
