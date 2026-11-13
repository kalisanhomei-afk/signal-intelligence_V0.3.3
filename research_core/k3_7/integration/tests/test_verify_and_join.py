"""Research-only deterministic safety tests; no synthetic observations enter final outputs."""
import unittest
from research_core.k3_7.integration.verify_and_join import align, validate_sources, report


def make_w(date="2020-06-11", marketing_year="2020/21"):
    return dict(release_date=date, marketing_year=marketing_year, commodity="Corn",
                region="United States", metric="ending_stocks_million_bushels",
                value="123.00", unit="Million Bushels", source_sha256="a"*64,
                timestamp_quality="UNKNOWN", published_at_utc="", available_at_utc="",
                quality_status="PIT_UNVERIFIED")


def make_n(date="2020-06-08", marketing_year="2020/21"):
    return dict(report_date=date, week_ending="2020-06-07", calendar_year="2020",
                marketing_year=marketing_year, state="Iowa", crop="CORN",
                source_sha256="b"*64, source_version_id="c"*64,
                timestamp_quality="UNKNOWN", published_at_utc="", available_at_utc="",
                quality_status="REVISED_EDITION_PIT_UNVERIFIED", revision_marker="true",
                very_poor_pct="1", poor_pct="4", fair_pct="20", good_pct="50",
                excellent_pct="25", good_excellent_pct="75")


class IntegrationGuards(unittest.TestCase):
    def test_valid_sources_still_pit_unverified(self):
        a = validate_sources([make_w()], [make_n()])
        self.assertEqual(a["NASS_REVISION_MARKER_TRUE_ORIGINALITY_UNVERIFIED"], 1)
        rows, excluded = align([make_w()], [make_n()])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["pit_certified"], "false")
        self.assertLess(rows[0]["nass_report_date"], rows[0]["wasde_release_date"])

    def test_same_day_report_not_assumed_available(self):
        rows, excluded = align([make_w("2020-06-08")], [make_n()])
        self.assertEqual(rows, [])
        self.assertTrue(excluded["NO_STRICTLY_EARLIER_NASS_REPORT"])

    def test_future_report_never_joins(self):
        rows, _ = align([make_w("2020-06-01")], [make_n()])
        self.assertFalse(rows)

    def test_duplicate_source_versions_fail_closed(self):
        rows, excluded = align([make_w()], [make_n(), make_n()])
        self.assertFalse(rows)
        self.assertEqual(excluded["CONFLICTING_OR_DUPLICATE_LATEST_REPORT"], 1)

    def test_cross_marketing_year_rejected(self):
        rows, _ = align([make_w()], [make_n(marketing_year="2019/20")])
        self.assertFalse(rows)

    def test_unverified_published_at_cannot_be_promoted(self):
        w = make_w()
        w["published_at_utc"] = "2020-06-11T17:00:00Z"
        with self.assertRaisesRegex(ValueError, "Unreviewed WASDE temporal claims"):
            validate_sources([w], [make_n()])

    def test_unexpected_timestamp_quality_rejected(self):
        n = make_n()
        n["timestamp_quality"] = "VERIFIED_PUBLIC_TIMESTAMP"
        with self.assertRaisesRegex(ValueError, "Unexpected NASS publication-time certification"):
            validate_sources([make_w()], [n])

    def test_bad_percentages_rejected(self):
        n = make_n()
        n["excellent_pct"] = "30"
        with self.assertRaisesRegex(ValueError, "percentage out of range"):
            validate_sources([make_w()], [n])

    def test_yield_unit_ambiguous_is_flagged_not_promoted(self):
        w = make_w()
        w["metric"] = "yield_bushels_per_acre"
        w["unit"] = "Bushels"
        warnings = validate_sources([w], [make_n()])
        self.assertEqual(warnings["YIELD_UNIT_LABEL_AMBIGUOUS_BUSHELS_VS_PER_ACRE"], 1)

    def test_summary_explicitly_disables_pit(self):
        rows, excluded = align([make_w()], [make_n()])
        result = report([make_w()], [make_n()], rows, {}, excluded)
        self.assertFalse(result["pit_certified"])
        self.assertEqual(result["certified_join_rows"], 0)
        self.assertTrue(result["release_coverage_unverified"])


if __name__ == "__main__":
    unittest.main()
