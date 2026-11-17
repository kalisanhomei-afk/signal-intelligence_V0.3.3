"""K5.2 third-party forecast parsing protects against prior-event conflation."""
import unittest
from research_core.k5.external_forecast_probe import parse_candidate,ExtractText,SOURCES

class K52ThirdPartyForecastTests(unittest.TestCase):
    def test_named_model_is_not_consensus(self):
        x=parse_candidate("named_forecaster_arc",
                          "Open call +13.4 Bcf, build Week ending Nov 13, 2026. "
                          "Published Fri Nov 13, 7:21 PM ET.")
        self.assertEqual(x["forecast_net_change_bcf"],13.4)
        self.assertEqual(x["forecast_class"],"SINGLE_NAMED_FORECASTER_NOT_CONSENSUS")
        self.assertFalse(x["publisher_claim_independently_authenticated"])

    def test_calendar_with_event_identity(self):
        x=parse_candidate("metatrader_event_calendar",
                          "Last release 13 Nov 2026 Actual 61 B Next release "
                          "19 Nov 2026 15:30 GMT Actual Coming in 2 days Forecast 69 B Previous 61 B")
        self.assertEqual(x["forecast_net_change_bcf"],69.0)
        self.assertIsNone(x["publisher_publication_time_claim"])
        self.assertIn("UNVERIFIED",x["forecast_class"])

    def test_previous_report_forecast_cannot_be_substituted(self):
        with self.assertRaisesRegex(ValueError,"TARGET_RELEASE_NOT_PRESENT"):
            parse_candidate("metatrader_event_calendar",
                            "Latest Nov 13 Forecast 65 B Previous 77 B")

    def test_unknown_forecast_but_correct_event_rejected(self):
        with self.assertRaisesRegex(ValueError,"WEB_EXPECTED_NUMBER_DIFFERENT"):
            parse_candidate("metatrader_event_calendar",
                            "Next release 19 Nov 2026 15:30 GMT Actual pending Forecast 61 B")

    def test_missing_model_claim_publication_rejected(self):
        with self.assertRaisesRegex(ValueError,"PUBLISHER_CLAIM_NOT_FOUND"):
            parse_candidate("named_forecaster_arc","Open call +13.4 Bcf, build Week ending Nov 13, 2026.")

    def test_html_text_skips_scripts(self):
        s=ExtractText()
        s.feed("<p>Open call</p><script>HIDDEN</script><p>+13.4 Bcf, build</p>")
        self.assertEqual(s.joined(),"Open call +13.4 Bcf, build")

    def test_source_allowlist_fixed(self):
        self.assertEqual(set(SOURCES),{"named_forecaster_arc","metatrader_event_calendar"})
