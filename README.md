# Podlings MCP

A small dependency-free MCP server for working with Apache Software Foundation Incubator `podlings.xml` data.

It exposes tools to:

- load podling metadata from a URL or local XML file
- list podlings with optional filtering
- list current, graduated, and retired podlings
- fetch details for a specific podling
- return basic Incubator summary statistics
- return mentor-count coverage statistics
- analyze podling starts and active population over time
- analyze yearly completion counts
- analyze graduation rate over time
- analyze graduation and retirement duration over time

If `source` is omitted, the server defaults to `https://incubator.apache.org/podlings.xml`.

The default ASF podlings XML source is cached locally for 24 hours. Set `PODLINGS_MCP_CACHE_DIR` to override the cache directory.

## Requirements

- Python 3.12+

## Run

```bash
python3 server.py
```

The server uses `stdio`, so it is intended to be launched by an MCP client.

## Install

```bash
python3 -m pip install .
```

For development tools:

```bash
python3 -m pip install -e .[dev]
```

## Test

```bash
python3 -m unittest discover -s tests -v
```

The tests cover parser behavior, tool functions, error cases, and a small end-to-end MCP `stdio` exchange.

## Developer Commands

```bash
make format
make check-format
make test
make coverage
make lint
make typecheck
make check
```

Formatting and linting use `ruff`, including `make check-format` for CI-style format verification, and type checking uses `mypy`. See [docs/architecture.md](./docs/architecture.md) for the current module layout.

## Example MCP client config

```json
{
  "mcpServers": {
    "podlings": {
      "command": "apache-podlings-mcp"
    }
  }
}
```

## Concepts and Defaults

- `sponsor_type` defaults to `incubator` across the filtering and analytics tools.
- `completed` means podlings that reached an end state: `graduated` or `retired`.
- Count and rate timeline tools use podling `enddate` to place outcomes into a year.
- Duration timeline tools use both `startdate` and `enddate` to calculate months to graduate or retire.
- `completed_podlings_by_year` returns both lists by default, and the `graduated_podlings_by_year` and `retired_podlings_by_year` tools are convenience wrappers over that same lookup.

## Tools

### `list_podlings`

List podlings from `podlings.xml`.

Arguments:

- `source`: URL or local file path
- `status`: optional exact status filter
- `sponsor_type`: optional sponsor type filter, defaults to `incubator`
- `search`: optional case-insensitive name/description/champion search
- `limit`: optional max number of results to return

`source` is optional and defaults to the ASF Incubator `podlings.xml` URL.

### `list_current_podlings`

List podlings with `status="current"`.

Arguments:

- `source`: URL or local file path
- `sponsor_type`: optional sponsor type filter, defaults to `incubator`
- `search`: optional case-insensitive name/description/champion search
- `limit`: optional max number of results to return

`source` is optional and defaults to the ASF Incubator `podlings.xml` URL.

### `list_graduated_podlings`

List podlings with `status="graduated"`.

Arguments:

- `source`: URL or local file path
- `sponsor_type`: optional sponsor type filter, defaults to `incubator`
- `search`: optional case-insensitive name/description/champion search
- `limit`: optional max number of results to return

`source` is optional and defaults to the ASF Incubator `podlings.xml` URL.

### `list_retired_podlings`

List podlings with `status="retired"`.

Arguments:

- `source`: URL or local file path
- `sponsor_type`: optional sponsor type filter, defaults to `incubator`
- `search`: optional case-insensitive name/description/champion search
- `limit`: optional max number of results to return

`source` is optional and defaults to the ASF Incubator `podlings.xml` URL.

### `get_podling`

Return a single podling by name.

Arguments:

- `source`: URL or local file path
- `name`: podling name

`source` is optional and defaults to the ASF Incubator `podlings.xml` URL.

### `podling_stats`

Return summary statistics for a `podlings.xml` source.

Arguments:

- `source`: URL or local file path
- `sponsor_type`: optional sponsor type filter, defaults to `incubator`

`source` is optional and defaults to the ASF Incubator `podlings.xml` URL.

The stats include sponsor classification so you can distinguish:

- `incubator`: sponsored by the Incubator
- `project`: sponsored by another ASF project/PMC
- `unknown`: no sponsor value was found

### `mentor_count_stats`

Return mentor coverage and mentor-count distribution stats for a `podlings.xml` source.

Arguments:

- `source`: URL or local file path
- `sponsor_type`: optional sponsor type filter, defaults to `incubator`

`source` is optional and defaults to the ASF Incubator `podlings.xml` URL.

### `raw_podlings_xml_info`

Return source metadata and a small preview of parsed records for troubleshooting.

Arguments:

- `source`: URL or local file path

`source` is optional and defaults to the ASF Incubator `podlings.xml` URL.

### `graduation_rate_over_time`

Return yearly graduation and retirement counts plus graduation rate based on podling `enddate`.

Arguments:

- `source`: URL or local file path
- `start_year`: optional inclusive start year filter
- `end_year`: optional inclusive end year filter
- `sponsor_type`: optional sponsor type filter, defaults to `incubator`

`source` is optional and defaults to the ASF Incubator `podlings.xml` URL.

### `podlings_started_over_time`

Return yearly podling start counts based on `startdate`.

Arguments:

- `source`: URL or local file path
- `start_year`: optional inclusive start year filter
- `end_year`: optional inclusive end year filter
- `sponsor_type`: optional sponsor type filter, defaults to `incubator`

`source` is optional and defaults to the ASF Incubator `podlings.xml` URL.

### `started_podlings_by_year`

Return the podlings that started in a specific year.

Arguments:

- `source`: URL or local file path
- `year`: required year to inspect
- `sponsor_type`: optional sponsor type filter, defaults to `incubator`

`source` is optional and defaults to the ASF Incubator `podlings.xml` URL.

### `active_podlings_by_year`

Return yearly active-podling counts based on lifecycle span.

Arguments:

- `source`: URL or local file path
- `start_year`: optional inclusive start year filter
- `end_year`: optional inclusive end year filter
- `sponsor_type`: optional sponsor type filter, defaults to `incubator`

`source` is optional and defaults to the ASF Incubator `podlings.xml` URL.

### `active_podlings_in_year`

Return the podlings that were active during a specific year.

Arguments:

- `source`: URL or local file path
- `year`: required year to inspect
- `sponsor_type`: optional sponsor type filter, defaults to `incubator`

`source` is optional and defaults to the ASF Incubator `podlings.xml` URL.

### `completion_rate_over_time`

Return yearly completion rate using completed outcomes divided by active population.

Arguments:

- `source`: URL or local file path
- `start_year`: optional inclusive start year filter
- `end_year`: optional inclusive end year filter
- `sponsor_type`: optional sponsor type filter, defaults to `incubator`

`source` is optional and defaults to the ASF Incubator `podlings.xml` URL.

### `completion_count_over_time`

Return yearly completed podling counts based on `enddate`, split into graduated and retired outcomes.

Arguments:

- `source`: URL or local file path
- `start_year`: optional inclusive start year filter
- `end_year`: optional inclusive end year filter
- `sponsor_type`: optional sponsor type filter, defaults to `incubator`

`source` is optional and defaults to the ASF Incubator `podlings.xml` URL.

### `completed_podlings_by_year`

Return the podlings that completed in a specific year, split into graduated and retired outcomes.

Arguments:

- `source`: URL or local file path
- `year`: required year to inspect
- `status`: optional filter, `graduated` or `retired`
- `sponsor_type`: optional sponsor type filter, defaults to `incubator`

`source` is optional and defaults to the ASF Incubator `podlings.xml` URL.

### `completed_podlings_in_range`

Return the podlings that completed within an inclusive year range.

Arguments:

- `source`: URL or local file path
- `start_year`: required inclusive start year
- `end_year`: required inclusive end year
- `status`: optional filter, `graduated` or `retired`
- `sponsor_type`: optional sponsor type filter, defaults to `incubator`

`source` is optional and defaults to the ASF Incubator `podlings.xml` URL.

### `graduated_podlings_by_year`

Return the podlings that graduated in a specific year.

Arguments:

- `source`: URL or local file path
- `year`: required year to inspect
- `sponsor_type`: optional sponsor type filter, defaults to `incubator`

`source` is optional and defaults to the ASF Incubator `podlings.xml` URL.

### `retired_podlings_by_year`

Return the podlings that retired in a specific year.

Arguments:

- `source`: URL or local file path
- `year`: required year to inspect
- `sponsor_type`: optional sponsor type filter, defaults to `incubator`

`source` is optional and defaults to the ASF Incubator `podlings.xml` URL.

### `graduation_time_over_time`

Return yearly time-to-graduate stats in months based on podling `startdate` and `enddate`, including average, median, and percentile views.

Arguments:

- `source`: URL or local file path
- `start_year`: optional inclusive start year filter
- `end_year`: optional inclusive end year filter
- `sponsor_type`: optional sponsor type filter, defaults to `incubator`

`source` is optional and defaults to the ASF Incubator `podlings.xml` URL.

### `time_to_retirement_over_time`

Return yearly time-to-retirement stats in months based on podling `startdate` and `enddate`, including average, median, and percentile views.

Arguments:

- `source`: URL or local file path
- `start_year`: optional inclusive start year filter
- `end_year`: optional inclusive end year filter
- `sponsor_type`: optional sponsor type filter, defaults to `incubator`

`source` is optional and defaults to the ASF Incubator `podlings.xml` URL.

## Examples

List current incubator-sponsored podlings:

```json
{
  "name": "list_current_podlings",
  "arguments": {}
}
```

Typical response:

```json
{
  "returned": 1,
  "total_matching": 1,
  "podlings": [
    {
      "name": "ExampleOne",
      "status": "current",
      "sponsor_type": "incubator"
    }
  ]
}
```

Analyze graduation timing for project-sponsored podlings:

```json
{
  "name": "graduation_time_over_time",
  "arguments": {
    "sponsor_type": "project"
  }
}
```

Analyze yearly completion counts for project-sponsored podlings:

```json
{
  "name": "completion_count_over_time",
  "arguments": {
    "sponsor_type": "project"
  }
}
```

Typical response:

```json
{
  "years": [
    {
      "year": 2024,
      "graduated": 1,
      "retired": 0,
      "completed": 1
    }
  ],
  "overall_completed": 1,
  "overall_graduated": 1,
  "overall_retired": 0
}
```

Analyze yearly start counts for incubator-sponsored podlings:

```json
{
  "name": "podlings_started_over_time",
  "arguments": {}
}
```

Typical response:

```json
{
  "years": [
    {
      "year": 2022,
      "started": 1
    },
    {
      "year": 2025,
      "started": 1
    }
  ],
  "overall_started": 2
}
```

Look up which podlings were active in a specific year:

```json
{
  "name": "active_podlings_in_year",
  "arguments": {
    "year": 2023
  }
}
```

Typical response:

```json
{
  "year": 2023,
  "active": ["ExampleThree"],
  "active_count": 1
}
```

Look up which podlings completed in a specific year:

```json
{
  "name": "completed_podlings_by_year",
  "arguments": {
    "year": 2024,
    "sponsor_type": "project"
  }
}
```

Typical response:

```json
{
  "year": 2024,
  "status_filter": "all",
  "graduated": ["ExampleTwo"],
  "retired": [],
  "completed": ["ExampleTwo"],
  "completed_count": 1
}
```

Look up which podlings completed in a year range:

```json
{
  "name": "completed_podlings_in_range",
  "arguments": {
    "start_year": 2023,
    "end_year": 2024
  }
}
```

Typical response:

```json
{
  "start_year": 2023,
  "end_year": 2024,
  "status_filter": "all",
  "graduated": [],
  "retired": ["ExampleThree"],
  "completed": ["ExampleThree"],
  "completed_count": 1
}
```

Look up just the podlings that retired in a specific year:

```json
{
  "name": "retired_podlings_by_year",
  "arguments": {
    "year": 2023
  }
}
```

Typical response:

```json
{
  "year": 2023,
  "status_filter": "retired",
  "graduated": [],
  "retired": ["ExampleThree"],
  "completed": ["ExampleThree"],
  "completed_count": 1
}
```

Look up just the podlings that graduated in a specific year:

```json
{
  "name": "graduated_podlings_by_year",
  "arguments": {
    "year": 2024,
    "sponsor_type": "project"
  }
}
```

Typical response:

```json
{
  "year": 2024,
  "status_filter": "graduated",
  "graduated": ["ExampleTwo"],
  "retired": [],
  "completed": ["ExampleTwo"],
  "completed_count": 1
}
```

Typical response:

```json
{
  "years": [
    {
      "year": 2024,
      "graduated": 1,
      "total_months_to_graduate": 17,
      "average_months_to_graduate": 17.0,
      "median_months_to_graduate": 17.0,
      "p75_months_to_graduate": 17.0,
      "p90_months_to_graduate": 17.0
    }
  ],
  "overall_graduated": 1,
  "overall_average_months_to_graduate": 17.0
}
```

Analyze retirement timing for incubator-sponsored podlings after 2020:

```json
{
  "name": "time_to_retirement_over_time",
  "arguments": {
    "start_year": 2021
  }
}
```

Typical response:

```json
{
  "years": [
    {
      "year": 2023,
      "retired": 1,
      "total_months_to_retire": 16,
      "average_months_to_retire": 16.0,
      "median_months_to_retire": 16.0,
      "p75_months_to_retire": 16.0,
      "p90_months_to_retire": 16.0
    }
  ],
  "overall_retired": 1,
  "overall_average_months_to_retire": 16.0
}
```

## Source examples

- ASF URL: `https://incubator.apache.org/podlings.xml`
- Local file: `/path/to/podlings.xml`

## Notes

- Remote sources are fetched with Python's standard library.
- XML parsing targets the ASF Incubator `podlings.xml` structure directly.
- Tools that accept `sponsor_type` default to `incubator`.
- Valid `sponsor_type` values are `incubator`, `project`, and `unknown`.
