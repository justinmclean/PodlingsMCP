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

## Install

```bash
python3 -m pip install .
```

For development tools:

```bash
python3 -m pip install -e .[dev]
```

## Run

After installation, run the stdio MCP server with:

```bash
podlings-mcp
```

For local development without installing first, you can still run:

```bash
python3 server.py
```

The server uses `stdio`, so it is intended to be launched by an MCP client.
It accepts standard JSON-RPC 2.0 request objects and non-empty batches, ignores notifications, and returns structured JSON-RPC errors for malformed input, invalid request shapes, unknown methods, and invalid MCP tool parameters.

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
      "command": "podlings-mcp"
    }
  }
}
```

The package also keeps `apache-podlings-mcp` as a backwards-compatible command alias.

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

## Usage Examples

These examples show natural-language requests an MCP client can answer with the tools below.

### Current Podling Review Workflow

Use these when preparing for a regular review of the active Incubator podling roster:

- "Show me the current Incubator-sponsored podlings."
- "Summarize the current Incubator podlings, including how many have descriptions, sponsors, champions, and mentors listed."
- "Which current podlings have unusually low mentor coverage?"
- "Give me the full podlings.xml record for PodlingFoo."

This gives reviewers a quick view of the active roster, basic metadata coverage, and mentor coverage without needing to inspect `podlings.xml` directly.

### Cohort And Lifecycle Review

Use these when trying to understand how a group of podlings moved through incubation over time:

- "How many Incubator-sponsored podlings started each year from 2020 onwards?"
- "Which podlings started in 2022?"
- "Show the active podling count by year from 2020 to 2025."
- "Which podlings were active during 2023?"

This connects yearly trends to the specific podlings behind those trends.

### Completion And Graduation Review

Use these when reviewing graduation and retirement outcomes for a period:

- "Show yearly Incubator podling completions since 2020, split into graduations and retirements."
- "What was the graduation rate for completed podlings each year from 2020 to 2025?"
- "Which podlings completed between 2023 and 2024?"
- "Which podlings retired in 2023?"

This is useful for turning trend charts into a concrete list of podlings to discuss.

### Duration Trend Review

Use these when reviewing how long podlings take to reach terminal outcomes:

- "How long did graduated podlings take to graduate each year, including median and percentile timings?"
- "Show retirement timing by year for podlings that retired after 2020."
- "What is the average and median time to retirement for recent retired podlings?"

This separates completion volume from time-to-outcome trends.

### Source Troubleshooting Workflow

Use these when a local XML file or alternate URL does not produce the expected results:

- "Inspect `/path/to/podlings.xml` and show me the source metadata plus a few parsed records."
- "List the first 10 normalized podling records from `/path/to/podlings.xml`."
- "In `/path/to/podlings.xml`, show me the parsed record for ExampleOne."
- "Using `/path/to/podlings.xml`, show yearly completion counts from 2020 onwards."

This helps separate source-loading issues from filtering or analytics questions.

## Source examples

- ASF URL: `https://incubator.apache.org/podlings.xml`
- Local file: `/path/to/podlings.xml`

## Notes

- Remote sources are fetched with Python's standard library.
- XML parsing targets the ASF Incubator `podlings.xml` structure directly.
- Tools that accept `sponsor_type` default to `incubator`.
- Valid `sponsor_type` values are `incubator`, `project`, and `unknown`.
