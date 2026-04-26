import unittest

from podlings.tools import (
    optional_string,
    require_string,
    resolve_source,
    resolve_sponsor_type,
    tool_active_podlings_by_year,
    tool_active_podlings_in_year,
    tool_completed_podlings_by_year,
    tool_completed_podlings_in_range,
    tool_completion_count_over_time,
    tool_completion_rate_over_time,
    tool_get_podling,
    tool_graduated_podlings_by_year,
    tool_graduation_rate_over_time,
    tool_graduation_time_over_time,
    tool_list_current_podlings,
    tool_list_graduated_podlings,
    tool_list_podlings,
    tool_list_retired_podlings,
    tool_mentor_count_stats,
    tool_podling_stats,
    tool_podlings_started_over_time,
    tool_raw_podlings_xml_info,
    tool_reporting_schedule,
    tool_retired_podlings_by_year,
    tool_started_podlings_by_year,
    tool_time_to_retirement_over_time,
)
from tests.fixtures import GRADUATION_TIMELINE_XML, REPORTING_XML, RETIREMENT_TIMELINE_XML, SAMPLE_XML, temporary_xml_file


class ArgumentHelperTests(unittest.TestCase):
    def test_require_string_accepts_non_empty_values(self) -> None:
        self.assertEqual(require_string({"name": " Gravitino "}, "name"), "Gravitino")

    def test_require_string_rejects_missing_or_blank_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "'name' must be a non-empty string"):
            require_string({}, "name")
        with self.assertRaisesRegex(ValueError, "'name' must be a non-empty string"):
            require_string({"name": "   "}, "name")

    def test_optional_string_rejects_non_string_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "'status' must be a string"):
            optional_string({"status": 123}, "status")

    def test_resolve_source_defaults_to_asf_url(self) -> None:
        self.assertEqual(resolve_source({}), "https://incubator.apache.org/podlings.xml")

    def test_resolve_sponsor_type_defaults_to_incubator(self) -> None:
        self.assertEqual(resolve_sponsor_type({}), "incubator")

    def test_resolve_sponsor_type_rejects_invalid_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "'sponsor_type' must be one of:"):
            resolve_sponsor_type({"sponsor_type": "pmc"})


class ToolTests(unittest.TestCase):
    def test_list_podlings_returns_all_podlings(self) -> None:
        result = tool_list_podlings({"source": str(SAMPLE_XML)})

        self.assertEqual(result["returned"], 2)
        self.assertEqual(result["total_matching"], 2)
        self.assertEqual([item["name"] for item in result["podlings"]], ["ExampleOne", "ExampleThree"])

    def test_list_podlings_filters_by_status(self) -> None:
        result = tool_list_podlings({"source": str(SAMPLE_XML), "status": "current"})

        self.assertEqual(result["returned"], 1)
        self.assertEqual(result["podlings"][0]["name"], "ExampleOne")

    def test_list_podlings_filters_by_sponsor_type(self) -> None:
        result = tool_list_podlings({"source": str(SAMPLE_XML), "sponsor_type": "project"})

        self.assertEqual(result["returned"], 1)
        self.assertEqual(result["podlings"][0]["name"], "ExampleTwo")

    def test_list_podlings_defaults_to_incubator_sponsor_type(self) -> None:
        result = tool_list_podlings({"source": str(SAMPLE_XML)})

        self.assertEqual([item["name"] for item in result["podlings"]], ["ExampleOne", "ExampleThree"])

    def test_list_podlings_filters_by_search(self) -> None:
        result = tool_list_podlings({"source": str(SAMPLE_XML), "search": "john doe"})

        self.assertEqual(result["returned"], 0)

    def test_list_podlings_applies_limit(self) -> None:
        result = tool_list_podlings({"source": str(SAMPLE_XML), "limit": 1})

        self.assertEqual(result["returned"], 1)
        self.assertEqual(result["total_matching"], 2)

    def test_list_current_podlings_returns_current_only(self) -> None:
        result = tool_list_current_podlings({"source": str(SAMPLE_XML)})

        self.assertEqual(result["returned"], 1)
        self.assertEqual(result["podlings"][0]["name"], "ExampleOne")

    def test_list_graduated_podlings_returns_graduated_only(self) -> None:
        result = tool_list_graduated_podlings({"source": str(SAMPLE_XML)})

        self.assertEqual(result["returned"], 0)

    def test_list_retired_podlings_returns_retired_only(self) -> None:
        result = tool_list_retired_podlings({"source": str(SAMPLE_XML)})

        self.assertEqual(result["returned"], 1)
        self.assertEqual(result["podlings"][0]["name"], "ExampleThree")

    def test_reporting_schedule_returns_current_reporting_details(self) -> None:
        with temporary_xml_file(REPORTING_XML) as xml_path:
            result = tool_reporting_schedule({"source": xml_path, "as_of_date": "2026-04-25"})

        self.assertEqual(result["returned"], 5)
        self.assertEqual(result["total_matching"], 5)
        self.assertEqual(
            [item["name"] for item in result["podlings"]],
            ["MonthlyFallback", "MonthlyFresh", "MonthlyStale", "QuarterlyOne", "QuarterlyTwo"],
        )
        self.assertEqual(result["report_month"], "2026-05")

        monthly_fallback = result["podlings"][0]
        self.assertEqual(monthly_fallback["expected_cadence"], "monthly")
        self.assertTrue(monthly_fallback["due_this_month"])
        self.assertEqual(monthly_fallback["latest_expected_report_period_as_of"]["label"], "May 2026")
        self.assertEqual(monthly_fallback["next_expected_report_period"]["label"], "May 2026")

        monthly_fresh = result["podlings"][1]
        self.assertEqual(monthly_fresh["expected_cadence"], "monthly")
        self.assertTrue(monthly_fresh["due_this_month"])
        self.assertEqual(monthly_fresh["next_expected_report_period"]["label"], "May 2026")

        monthly_stale = result["podlings"][2]
        self.assertIsNone(monthly_stale["next_expected_report_period"])

        quarterly = result["podlings"][3]
        self.assertEqual(quarterly["expected_cadence"], "quarterly")
        self.assertFalse(quarterly["due_this_month"])
        self.assertEqual(quarterly["next_expected_report_period"]["label"], "July 2026")

        quarterly_two = result["podlings"][4]
        self.assertEqual(quarterly_two["expected_cadence"], "quarterly")
        self.assertTrue(quarterly_two["due_this_month"])
        self.assertEqual(quarterly_two["next_expected_report_period"]["label"], "May 2026")

    def test_reporting_schedule_supports_due_filter(self) -> None:
        with temporary_xml_file(REPORTING_XML) as xml_path:
            due_result = tool_reporting_schedule({"source": xml_path, "as_of_date": "2026-04-25", "due_this_month": True})

        self.assertEqual(
            [item["name"] for item in due_result["podlings"]],
            ["MonthlyFallback", "MonthlyFresh", "QuarterlyTwo"],
        )

    def test_reporting_schedule_supports_explicit_report_month(self) -> None:
        with temporary_xml_file(REPORTING_XML) as xml_path:
            result = tool_reporting_schedule(
                {"source": xml_path, "as_of_date": "2026-04-25", "report_month": "2026-05", "due_this_month": True}
            )

        self.assertEqual(result["report_month"], "2026-05")
        self.assertEqual(
            [item["name"] for item in result["podlings"]],
            ["MonthlyFallback", "MonthlyFresh", "QuarterlyTwo"],
        )

    def test_reporting_schedule_keeps_current_cycle_through_third_wednesday(self) -> None:
        with temporary_xml_file(REPORTING_XML) as xml_path:
            result = tool_reporting_schedule({"source": xml_path, "as_of_date": "2026-05-20", "due_this_month": True})

        self.assertEqual(result["report_month"], "2026-05")
        self.assertEqual(
            [item["name"] for item in result["podlings"]],
            ["MonthlyFallback", "MonthlyFresh", "QuarterlyTwo"],
        )

    def test_reporting_schedule_rolls_forward_after_third_wednesday(self) -> None:
        with temporary_xml_file(REPORTING_XML) as xml_path:
            result = tool_reporting_schedule({"source": xml_path, "as_of_date": "2026-05-21", "due_this_month": True})

        self.assertEqual(result["report_month"], "2026-06")
        self.assertEqual(
            [item["name"] for item in result["podlings"]],
            ["MonthlyFallback"],
        )

    def test_reporting_schedule_stops_monthly_schedule_after_explicit_periods_end(self) -> None:
        with temporary_xml_file(REPORTING_XML) as xml_path:
            result = tool_reporting_schedule({"source": xml_path, "report_month": "2026-07", "due_this_month": True})

        self.assertEqual(result["report_month"], "2026-07")
        self.assertEqual(
            [item["name"] for item in result["podlings"]],
            ["MonthlyFallback", "QuarterlyOne"],
        )

    def test_reporting_schedule_supports_name_lookup(self) -> None:
        with temporary_xml_file(REPORTING_XML) as xml_path:
            result = tool_reporting_schedule({"source": xml_path, "name": "QuarterlyOne", "as_of_date": "2026-04-25"})

        self.assertEqual(result["returned"], 1)
        self.assertEqual(result["podlings"][0]["name"], "QuarterlyOne")

    def test_reporting_schedule_rejects_invalid_date(self) -> None:
        with self.assertRaisesRegex(ValueError, "'as_of_date' must be an ISO date in YYYY-MM-DD format"):
            tool_reporting_schedule({"source": str(SAMPLE_XML), "as_of_date": "2026-99-99"})

    def test_reporting_schedule_rejects_invalid_report_month(self) -> None:
        with self.assertRaisesRegex(ValueError, "'report_month' must be in YYYY-MM format"):
            tool_reporting_schedule({"source": str(SAMPLE_XML), "report_month": "2026-99"})

    def test_list_graduated_podlings_allows_project_override(self) -> None:
        result = tool_list_graduated_podlings({"source": str(SAMPLE_XML), "sponsor_type": "project"})

        self.assertEqual(result["returned"], 1)
        self.assertEqual(result["podlings"][0]["name"], "ExampleTwo")

    def test_get_podling_returns_sponsor_type_and_mentors(self) -> None:
        result = tool_get_podling({"source": str(SAMPLE_XML), "name": "ExampleOne"})

        self.assertEqual(result["podling"]["sponsor_type"], "incubator")
        self.assertEqual(result["podling"]["mentors"], ["Mentor One", "Mentor Two"])

    def test_get_podling_rejects_unknown_name(self) -> None:
        with self.assertRaisesRegex(ValueError, "Podling 'MissingPodling' not found"):
            tool_get_podling({"source": str(SAMPLE_XML), "name": "MissingPodling"})

    def test_podling_stats_breaks_out_sponsor_types(self) -> None:
        result = tool_podling_stats({"source": str(SAMPLE_XML)})

        self.assertEqual(result["sponsor_type"], "incubator")
        self.assertEqual(result["sponsor_type_counts"], {"incubator": 2})
        self.assertEqual(result["incubator_sponsored_podlings"], 2)
        self.assertEqual(result["project_sponsored_podlings"], 0)
        self.assertEqual(result["status_counts"], {"current": 1, "retired": 1})
        self.assertEqual(result["total_podlings"], 2)
        self.assertEqual(result["average_mentor_count"], 1.5)

    def test_podling_stats_allows_project_override(self) -> None:
        result = tool_podling_stats({"source": str(SAMPLE_XML), "sponsor_type": "project"})

        self.assertEqual(result["sponsor_type"], "project")
        self.assertEqual(result["total_podlings"], 1)
        self.assertEqual(result["status_counts"], {"graduated": 1})
        self.assertEqual(result["sponsor_type_counts"], {"project": 1})
        self.assertEqual(result["average_mentor_count"], 1.0)

    def test_mentor_count_stats_returns_distribution(self) -> None:
        result = tool_mentor_count_stats({"source": str(SAMPLE_XML)})

        self.assertEqual(result["total_podlings"], 2)
        self.assertEqual(result["podlings_with_mentors"], 2)
        self.assertEqual(result["podlings_without_mentors"], 0)
        self.assertEqual(result["total_mentors_listed"], 3)
        self.assertEqual(result["average_mentor_count"], 1.5)
        self.assertEqual(result["median_mentor_count"], 1.5)
        self.assertEqual(result["p75_mentor_count"], 1.75)
        self.assertEqual(result["max_mentor_count"], 2)

    def test_podlings_started_over_time_returns_yearly_timeline(self) -> None:
        result = tool_podlings_started_over_time({"source": str(SAMPLE_XML)})

        self.assertEqual(result["years"], [{"year": 2022, "started": 1}, {"year": 2025, "started": 1}])
        self.assertEqual(result["overall_started"], 2)

    def test_podlings_started_over_time_allows_project_override(self) -> None:
        result = tool_podlings_started_over_time({"source": str(SAMPLE_XML), "sponsor_type": "project"})

        self.assertEqual(result["years"], [{"year": 2023, "started": 1}])
        self.assertEqual(result["overall_started"], 1)

    def test_started_podlings_by_year_returns_names(self) -> None:
        result = tool_started_podlings_by_year({"source": str(SAMPLE_XML), "year": 2025})

        self.assertEqual(result["started"], ["ExampleOne"])
        self.assertEqual(result["started_count"], 1)

    def test_started_podlings_by_year_rejects_invalid_year(self) -> None:
        with self.assertRaisesRegex(ValueError, "'year' must be an integer"):
            tool_started_podlings_by_year({"source": str(SAMPLE_XML), "year": "2025"})

    def test_active_podlings_by_year_returns_yearly_timeline(self) -> None:
        result = tool_active_podlings_by_year({"source": str(SAMPLE_XML)})

        self.assertEqual(
            result["years"],
            [
                {"year": 2022, "active": 1},
                {"year": 2023, "active": 1},
                {"year": 2025, "active": 1},
            ],
        )
        self.assertEqual(result["overall_active_years"], 3)
        self.assertEqual(result["peak_active"], 1)

    def test_active_podlings_by_year_honors_year_filters(self) -> None:
        result = tool_active_podlings_by_year({"source": str(SAMPLE_XML), "start_year": 2024, "end_year": 2025})

        self.assertEqual(result["years"], [{"year": 2025, "active": 1}])

    def test_active_podlings_in_year_returns_names(self) -> None:
        result = tool_active_podlings_in_year({"source": str(SAMPLE_XML), "year": 2023})

        self.assertEqual(result["active"], ["ExampleThree"])
        self.assertEqual(result["active_count"], 1)

    def test_active_podlings_in_year_allows_project_override(self) -> None:
        result = tool_active_podlings_in_year({"source": str(SAMPLE_XML), "year": 2024, "sponsor_type": "project"})

        self.assertEqual(result["active"], ["ExampleTwo"])
        self.assertEqual(result["active_count"], 1)

    def test_graduation_rate_over_time_returns_yearly_timeline(self) -> None:
        result = tool_graduation_rate_over_time({"source": str(SAMPLE_XML)})

        self.assertEqual(
            result["years"],
            [
                {"year": 2023, "graduated": 0, "retired": 1, "completed": 1, "graduation_rate": 0.0},
            ],
        )
        self.assertEqual(result["overall_completed"], 1)
        self.assertEqual(result["overall_graduated"], 0)
        self.assertEqual(result["overall_retired"], 1)
        self.assertEqual(result["overall_graduation_rate"], 0.0)

    def test_graduation_rate_over_time_honors_year_filters(self) -> None:
        result = tool_graduation_rate_over_time({"source": str(SAMPLE_XML), "start_year": 2024})

        self.assertEqual(result["years"], [])

    def test_graduation_rate_over_time_rejects_invalid_year_filters(self) -> None:
        with self.assertRaisesRegex(ValueError, "'start_year' must be an integer"):
            tool_graduation_rate_over_time({"source": str(SAMPLE_XML), "start_year": "2024"})
        with self.assertRaisesRegex(ValueError, "'end_year' must be an integer"):
            tool_graduation_rate_over_time({"source": str(SAMPLE_XML), "end_year": "2024"})

    def test_graduation_rate_over_time_allows_project_override(self) -> None:
        result = tool_graduation_rate_over_time({"source": str(SAMPLE_XML), "sponsor_type": "project"})

        self.assertEqual(
            result["years"],
            [
                {"year": 2024, "graduated": 1, "retired": 0, "completed": 1, "graduation_rate": 1.0},
            ],
        )

    def test_completion_rate_over_time_returns_yearly_timeline(self) -> None:
        result = tool_completion_rate_over_time({"source": str(SAMPLE_XML)})

        self.assertEqual(
            result["years"],
            [
                {"year": 2022, "active": 1, "graduated": 0, "retired": 0, "completed": 0, "completion_rate": 0.0},
                {"year": 2023, "active": 1, "graduated": 0, "retired": 1, "completed": 1, "completion_rate": 1.0},
                {"year": 2025, "active": 1, "graduated": 0, "retired": 0, "completed": 0, "completion_rate": 0.0},
            ],
        )
        self.assertEqual(result["overall_active"], 3)
        self.assertEqual(result["overall_completed"], 1)
        self.assertEqual(result["overall_completion_rate"], 0.333)

    def test_completion_rate_over_time_allows_project_override(self) -> None:
        result = tool_completion_rate_over_time({"source": str(SAMPLE_XML), "sponsor_type": "project"})

        self.assertEqual(
            result["years"],
            [
                {"year": 2023, "active": 1, "graduated": 0, "retired": 0, "completed": 0, "completion_rate": 0.0},
                {"year": 2024, "active": 1, "graduated": 1, "retired": 0, "completed": 1, "completion_rate": 1.0},
            ],
        )
        self.assertEqual(result["overall_completion_rate"], 0.5)

    def test_completion_count_over_time_returns_yearly_timeline(self) -> None:
        result = tool_completion_count_over_time({"source": str(SAMPLE_XML)})

        self.assertEqual(
            result["years"],
            [
                {"year": 2023, "graduated": 0, "retired": 1, "completed": 1},
            ],
        )
        self.assertEqual(result["overall_completed"], 1)
        self.assertEqual(result["overall_graduated"], 0)
        self.assertEqual(result["overall_retired"], 1)

    def test_completion_count_over_time_honors_year_filters(self) -> None:
        result = tool_completion_count_over_time({"source": str(SAMPLE_XML), "start_year": 2024})

        self.assertEqual(result["years"], [])
        self.assertEqual(result["overall_completed"], 0)
        self.assertEqual(result["overall_graduated"], 0)
        self.assertEqual(result["overall_retired"], 0)

    def test_completion_count_over_time_rejects_invalid_year_filters(self) -> None:
        with self.assertRaisesRegex(ValueError, "'start_year' must be an integer"):
            tool_completion_count_over_time({"source": str(SAMPLE_XML), "start_year": "2024"})
        with self.assertRaisesRegex(ValueError, "'end_year' must be an integer"):
            tool_completion_count_over_time({"source": str(SAMPLE_XML), "end_year": "2024"})

    def test_completion_count_over_time_allows_project_override(self) -> None:
        result = tool_completion_count_over_time({"source": str(SAMPLE_XML), "sponsor_type": "project"})

        self.assertEqual(
            result["years"],
            [
                {"year": 2024, "graduated": 1, "retired": 0, "completed": 1},
            ],
        )
        self.assertEqual(result["overall_completed"], 1)
        self.assertEqual(result["overall_graduated"], 1)
        self.assertEqual(result["overall_retired"], 0)

    def test_completed_podlings_by_year_returns_year_split(self) -> None:
        result = tool_completed_podlings_by_year({"source": str(SAMPLE_XML), "year": 2023})

        self.assertEqual(result["year"], 2023)
        self.assertEqual(result["status_filter"], "all")
        self.assertEqual(result["graduated"], [])
        self.assertEqual(result["retired"], ["ExampleThree"])
        self.assertEqual(result["completed"], ["ExampleThree"])
        self.assertEqual(result["completed_count"], 1)

    def test_completed_podlings_by_year_allows_project_override(self) -> None:
        result = tool_completed_podlings_by_year({"source": str(SAMPLE_XML), "year": 2024, "sponsor_type": "project"})

        self.assertEqual(result["graduated"], ["ExampleTwo"])
        self.assertEqual(result["retired"], [])
        self.assertEqual(result["completed"], ["ExampleTwo"])
        self.assertEqual(result["completed_count"], 1)

    def test_completed_podlings_by_year_honors_status_filter(self) -> None:
        result = tool_completed_podlings_by_year(
            {"source": str(SAMPLE_XML), "year": 2024, "sponsor_type": "project", "status": "graduated"}
        )

        self.assertEqual(result["status_filter"], "graduated")
        self.assertEqual(result["graduated"], ["ExampleTwo"])
        self.assertEqual(result["retired"], [])
        self.assertEqual(result["completed"], ["ExampleTwo"])

    def test_completed_podlings_by_year_rejects_invalid_inputs(self) -> None:
        with self.assertRaisesRegex(ValueError, "'year' must be an integer"):
            tool_completed_podlings_by_year({"source": str(SAMPLE_XML), "year": "2024"})
        with self.assertRaisesRegex(ValueError, "'status' must be one of:"):
            tool_completed_podlings_by_year({"source": str(SAMPLE_XML), "year": 2024, "status": "current"})

    def test_completed_podlings_in_range_returns_names(self) -> None:
        result = tool_completed_podlings_in_range({"source": str(SAMPLE_XML), "start_year": 2023, "end_year": 2024})

        self.assertEqual(result["graduated"], [])
        self.assertEqual(result["retired"], ["ExampleThree"])
        self.assertEqual(result["completed"], ["ExampleThree"])
        self.assertEqual(result["completed_count"], 1)

    def test_completed_podlings_in_range_allows_project_override(self) -> None:
        result = tool_completed_podlings_in_range(
            {"source": str(SAMPLE_XML), "start_year": 2024, "end_year": 2024, "sponsor_type": "project"}
        )

        self.assertEqual(result["graduated"], ["ExampleTwo"])
        self.assertEqual(result["retired"], [])
        self.assertEqual(result["completed_count"], 1)

    def test_completed_podlings_in_range_rejects_invalid_inputs(self) -> None:
        with self.assertRaisesRegex(ValueError, "'start_year' must be an integer"):
            tool_completed_podlings_in_range({"source": str(SAMPLE_XML), "start_year": "2024", "end_year": 2025})
        with self.assertRaisesRegex(ValueError, "'start_year' must be less than or equal to 'end_year'"):
            tool_completed_podlings_in_range({"source": str(SAMPLE_XML), "start_year": 2025, "end_year": 2024})

    def test_graduated_podlings_by_year_sets_graduated_filter(self) -> None:
        result = tool_graduated_podlings_by_year({"source": str(SAMPLE_XML), "year": 2024, "sponsor_type": "project"})

        self.assertEqual(result["status_filter"], "graduated")
        self.assertEqual(result["graduated"], ["ExampleTwo"])
        self.assertEqual(result["retired"], [])
        self.assertEqual(result["completed"], ["ExampleTwo"])

    def test_retired_podlings_by_year_sets_retired_filter(self) -> None:
        result = tool_retired_podlings_by_year({"source": str(SAMPLE_XML), "year": 2023})

        self.assertEqual(result["status_filter"], "retired")
        self.assertEqual(result["graduated"], [])
        self.assertEqual(result["retired"], ["ExampleThree"])
        self.assertEqual(result["completed"], ["ExampleThree"])

    def test_graduation_time_over_time_returns_yearly_timeline(self) -> None:
        result = tool_graduation_time_over_time({"source": str(SAMPLE_XML)})

        self.assertEqual(result["years"], [])
        self.assertEqual(result["overall_graduated"], 0)
        self.assertEqual(result["overall_total_months_to_graduate"], 0)
        self.assertEqual(result["overall_average_months_to_graduate"], 0.0)
        self.assertEqual(result["median_months_to_graduate"], 0.0)
        self.assertEqual(result["p75_months_to_graduate"], 0.0)
        self.assertEqual(result["p90_months_to_graduate"], 0.0)

    def test_graduation_time_over_time_honors_year_filters(self) -> None:
        result = tool_graduation_time_over_time({"source": str(SAMPLE_XML), "end_year": 2023})

        self.assertEqual(result["years"], [])
        self.assertEqual(result["overall_graduated"], 0)
        self.assertEqual(result["overall_total_months_to_graduate"], 0)
        self.assertEqual(result["overall_average_months_to_graduate"], 0.0)
        self.assertEqual(result["median_months_to_graduate"], 0.0)
        self.assertEqual(result["p75_months_to_graduate"], 0.0)
        self.assertEqual(result["p90_months_to_graduate"], 0.0)

    def test_graduation_time_over_time_rejects_invalid_year_filters(self) -> None:
        with self.assertRaisesRegex(ValueError, "'start_year' must be an integer"):
            tool_graduation_time_over_time({"source": str(SAMPLE_XML), "start_year": "2024"})
        with self.assertRaisesRegex(ValueError, "'end_year' must be an integer"):
            tool_graduation_time_over_time({"source": str(SAMPLE_XML), "end_year": "2024"})

    def test_graduation_time_over_time_allows_project_override(self) -> None:
        result = tool_graduation_time_over_time({"source": str(SAMPLE_XML), "sponsor_type": "project"})

        self.assertEqual(
            result["years"],
            [
                {
                    "year": 2024,
                    "graduated": 1,
                    "total_months_to_graduate": 17,
                    "average_months_to_graduate": 17.0,
                    "median_months_to_graduate": 17.0,
                    "p75_months_to_graduate": 17.0,
                    "p90_months_to_graduate": 17.0,
                },
            ],
        )
        self.assertEqual(result["overall_graduated"], 1)
        self.assertEqual(result["overall_total_months_to_graduate"], 17)
        self.assertEqual(result["overall_average_months_to_graduate"], 17.0)
        self.assertEqual(result["median_months_to_graduate"], 17.0)
        self.assertEqual(result["p75_months_to_graduate"], 17.0)
        self.assertEqual(result["p90_months_to_graduate"], 17.0)

    def test_graduation_time_over_time_includes_median_and_percentiles(self) -> None:
        with temporary_xml_file(GRADUATION_TIMELINE_XML) as xml_path:
            result = tool_graduation_time_over_time({"source": xml_path, "sponsor_type": "project"})

        self.assertEqual(
            result["years"],
            [
                {
                    "year": 2024,
                    "graduated": 2,
                    "total_months_to_graduate": 30,
                    "average_months_to_graduate": 15.0,
                    "median_months_to_graduate": 15.0,
                    "p75_months_to_graduate": 16.5,
                    "p90_months_to_graduate": 17.4,
                },
                {
                    "year": 2025,
                    "graduated": 2,
                    "total_months_to_graduate": 42,
                    "average_months_to_graduate": 21.0,
                    "median_months_to_graduate": 21.0,
                    "p75_months_to_graduate": 22.5,
                    "p90_months_to_graduate": 23.4,
                },
            ],
        )
        self.assertEqual(result["overall_graduated"], 4)
        self.assertEqual(result["overall_total_months_to_graduate"], 72)
        self.assertEqual(result["overall_average_months_to_graduate"], 18.0)
        self.assertEqual(result["median_months_to_graduate"], 18.0)
        self.assertEqual(result["p75_months_to_graduate"], 19.5)
        self.assertEqual(result["p90_months_to_graduate"], 22.2)

    def test_time_to_retirement_over_time_returns_yearly_timeline(self) -> None:
        result = tool_time_to_retirement_over_time({"source": str(SAMPLE_XML)})

        self.assertEqual(
            result["years"],
            [
                {
                    "year": 2023,
                    "retired": 1,
                    "total_months_to_retire": 16,
                    "average_months_to_retire": 16.0,
                    "median_months_to_retire": 16.0,
                    "p75_months_to_retire": 16.0,
                    "p90_months_to_retire": 16.0,
                },
            ],
        )
        self.assertEqual(result["overall_retired"], 1)
        self.assertEqual(result["overall_total_months_to_retire"], 16)
        self.assertEqual(result["overall_average_months_to_retire"], 16.0)
        self.assertEqual(result["median_months_to_retire"], 16.0)
        self.assertEqual(result["p75_months_to_retire"], 16.0)
        self.assertEqual(result["p90_months_to_retire"], 16.0)

    def test_time_to_retirement_over_time_rejects_invalid_year_filters(self) -> None:
        with self.assertRaisesRegex(ValueError, "'start_year' must be an integer"):
            tool_time_to_retirement_over_time({"source": str(SAMPLE_XML), "start_year": "2024"})
        with self.assertRaisesRegex(ValueError, "'end_year' must be an integer"):
            tool_time_to_retirement_over_time({"source": str(SAMPLE_XML), "end_year": "2024"})

    def test_time_to_retirement_over_time_allows_project_override(self) -> None:
        with temporary_xml_file(RETIREMENT_TIMELINE_XML) as xml_path:
            result = tool_time_to_retirement_over_time({"source": xml_path, "sponsor_type": "project"})

        self.assertEqual(
            result["years"],
            [
                {
                    "year": 2024,
                    "retired": 2,
                    "total_months_to_retire": 30,
                    "average_months_to_retire": 15.0,
                    "median_months_to_retire": 15.0,
                    "p75_months_to_retire": 16.5,
                    "p90_months_to_retire": 17.4,
                },
                {
                    "year": 2025,
                    "retired": 1,
                    "total_months_to_retire": 24,
                    "average_months_to_retire": 24.0,
                    "median_months_to_retire": 24.0,
                    "p75_months_to_retire": 24.0,
                    "p90_months_to_retire": 24.0,
                },
            ],
        )
        self.assertEqual(result["overall_retired"], 3)
        self.assertEqual(result["overall_total_months_to_retire"], 54)
        self.assertEqual(result["overall_average_months_to_retire"], 18.0)
        self.assertEqual(result["median_months_to_retire"], 18.0)
        self.assertEqual(result["p75_months_to_retire"], 21.0)
        self.assertEqual(result["p90_months_to_retire"], 22.8)

    def test_tools_reject_invalid_sponsor_type(self) -> None:
        with self.assertRaisesRegex(ValueError, "'sponsor_type' must be one of:"):
            tool_list_podlings({"source": str(SAMPLE_XML), "sponsor_type": "pmc"})

    def test_raw_podlings_xml_info_returns_preview(self) -> None:
        result = tool_raw_podlings_xml_info({"source": str(SAMPLE_XML)})

        self.assertEqual(result["source"]["count"], 3)
        self.assertEqual(len(result["preview"]), 3)
        self.assertEqual(result["preview"][0]["name"], "ExampleOne")
