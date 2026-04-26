from __future__ import annotations

import tempfile
from contextlib import contextmanager
from pathlib import Path
from textwrap import dedent
from typing import Iterator

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
SAMPLE_XML = FIXTURES_DIR / "sample-podlings.xml"

PARSING_EDGE_CASES_XML = dedent(
    """\
    <?xml version="1.0" encoding="UTF-8"?>
    <podlings>
      <podling sponsor="Apache Incubator" />
      <podling name="Named" status="current" sponsor="Apache Incubator">
        <mentors>
          <observer>Ignored</observer>
          <mentor></mentor>
        </mentors>
      </podling>
    </podlings>
    """
)

GRADUATION_TIMELINE_XML = dedent(
    """\
    <?xml version="1.0" encoding="UTF-8"?>
    <podlings>
      <podling name="Alpha" status="graduated" sponsor="Apache Foo" startdate="2023-01-01" enddate="2024-01-01" />
      <podling name="Beta" status="graduated" sponsor="Apache Foo" startdate="2023-01-01" enddate="2024-07-01" />
      <podling name="Gamma" status="graduated" sponsor="Apache Foo" startdate="2023-01-01" enddate="2025-01-01" />
      <podling name="Delta" status="graduated" sponsor="Apache Foo" startdate="2024-01-01" enddate="2025-07-01" />
    </podlings>
    """
)

RETIREMENT_TIMELINE_XML = dedent(
    """\
    <?xml version="1.0" encoding="UTF-8"?>
    <podlings>
      <podling name="Alpha" status="retired" sponsor="Apache Foo" startdate="2023-01-01" enddate="2024-01-01" />
      <podling name="Beta" status="retired" sponsor="Apache Foo" startdate="2023-01-01" enddate="2024-07-01" />
      <podling name="Gamma" status="retired" sponsor="Apache Foo" startdate="2023-01-01" enddate="2025-01-01" />
    </podlings>
    """
)

REPORTING_XML = dedent(
    """\
    <?xml version="1.0" encoding="UTF-8"?>
    <podlings>
      <podling name="QuarterlyOne" status="current" sponsor="Incubator" startdate="2024-01-15">
        <description>Quarterly reporting podling</description>
        <reporting group="1" />
      </podling>
      <podling name="MonthlyFresh" status="current" sponsor="Incubator" startdate="2026-02-10">
        <description>New monthly podling</description>
        <reporting group="1" monthly="true">March, April, May</reporting>
      </podling>
      <podling name="MonthlyStale" status="current" sponsor="Apache Incubator" startdate="2025-11-01">
        <description>Monthly schedule that has already elapsed</description>
        <reporting group="3" monthly="true">December, January, February</reporting>
      </podling>
      <podling name="MonthlyFallback" status="current" sponsor="Apache Incubator" startdate="2025-10-01">
        <description>Monthly podling with no explicit reporting periods</description>
        <reporting group="1" monthly="true" />
      </podling>
      <podling name="QuarterlyTwo" status="current" sponsor="Apache Incubator" startdate="2025-02-01">
        <description>Incubator-sponsored quarterly group two podling</description>
        <reporting group="2" />
      </podling>
      <podling name="ProjectQuarterly" status="current" sponsor="Apache Foo" startdate="2025-02-01">
        <description>Project-sponsored quarterly podling</description>
        <reporting group="2" />
      </podling>
    </podlings>
    """
)


@contextmanager
def temporary_xml_file(xml_text: str) -> Iterator[str]:
    with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False) as handle:
        handle.write(xml_text)
        xml_path = handle.name

    try:
        yield xml_path
    finally:
        Path(xml_path).unlink(missing_ok=True)
