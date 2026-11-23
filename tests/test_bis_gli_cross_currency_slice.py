"""Offline-only synthetic tests for BIS cross-currency GLI extraction."""
import csv
import hashlib
import importlib.util
import io
from decimal import Decimal
from pathlib import Path
import unittest
import zipfile

src = Path(__file__).resolve().parents[1] / "scripts" / "bis_gli_cross_currency_slice.py"
spec = importlib.util.spec_from_file_location("bis_gli_cross_currency_slice", src)
lib = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lib)


def synthetic_zip(*, drop=None, status="A: Normal", duplicate=False, bad_multiplier=False):
    fields = list(lib.DIMENSIONS) + [lib.TIME, lib.VALUE, lib.UNIT_MULT, lib.STATUS]
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    for c, value in (("USD", "8.03"), ("EUR", "12.5"), ("JPY", "-2.3")):
        for q, delta in (("2026-Q1", "0"), ("2026-Q2", "1")):
            for unit in (c, "771"):
                key = (c, q, "yoy_percent" if unit == "771" else "stock_millions_local_currency")
                if key == drop:
                    continue
                dims = ("Q", c, "3P", "N", "A", "I", "B", unit)
                row = {k:v for k,v in zip(lib.DIMENSIONS,dims)}
                row[lib.TIME] = q
                row[lib.VALUE] = str(Decimal(value) + Decimal(delta)) if unit=="771" else "1234.567"
                row[lib.UNIT_MULT] = "6" if unit != "771" else ("6" if bad_multiplier else "0")
                row[lib.STATUS] = status
                writer.writerow(row)
                if duplicate and c == "USD" and q == "2026-Q2" and unit == "771":
                    writer.writerow(row)
    csv_bytes = buf.getvalue().encode()
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(lib.MEMBER, csv_bytes)
    return out.getvalue(), hashlib.sha256(csv_bytes).hexdigest()


class TestCrossCurrencyOffline(unittest.TestCase):
    def inspect_synthetic(self, **kw):
        zip_bytes, inner_sha = synthetic_zip(**kw)
        orig_hash, orig_inner = lib.EXPECTED_MEMBER_SHA256, lib.EXPECTED_ZIP_SHA256
        try:
            lib.EXPECTED_MEMBER_SHA256 = inner_sha
            return lib.inspect_archive_bytes(zip_bytes, expected_hash=hashlib.sha256(zip_bytes).hexdigest())
        finally:
            lib.EXPECTED_MEMBER_SHA256 = orig_hash
            self.assertEqual(lib.EXPECTED_ZIP_SHA256, orig_inner)

    def test_exact_twelve_cells_and_blocked_gate(self):
        data = self.inspect_synthetic()
        self.assertEqual(data["selected_cells"], 12)
        self.assertEqual(data["gate0"], "BLOCKED")
        self.assertFalse(data["accepted_for_model"])

    def test_regional_scopes_not_same(self):
        a = self.inspect_synthetic()["currency_comparison"]
        self.assertEqual({r["geographical_scope"] for r in a.values()}, {"outside United States", "outside euro area", "outside Japan"})

    def test_delta_is_points_not_ratio(self):
        a = self.inspect_synthetic()["currency_comparison"]
        self.assertEqual(a["JPY"]["q2_minus_q1_yoy_percentage_points"], "1.0")

    def test_missing_cell_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Missing expected"):
            self.inspect_synthetic(drop=("EUR", "2026-Q1", "yoy_percent"))

    def test_non_normal_status_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Non-normal"):
            self.inspect_synthetic(status="M: Missing")

    def test_duplicate_cell_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate observation"):
            self.inspect_synthetic(duplicate=True)

    def test_wrong_unit_multiplier_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unexpected unit multiplier"):
            self.inspect_synthetic(bad_multiplier=True)

    def test_wrong_zip_hash_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "ZIP hash mismatch"):
            lib.inspect_archive_bytes(b"arbitrary bytes")

    def test_member_sha_is_required(self):
        z, _ = synthetic_zip()
        with self.assertRaisesRegex(ValueError, "CSV member hash mismatch"):
            lib.inspect_archive_bytes(z, expected_hash=hashlib.sha256(z).hexdigest())

    def test_no_file_fails_without_downloading(self):
        with self.assertRaisesRegex(ValueError, "Existing local ZIP required"):
            lib.inspect_local_file(Path("/nonexistent/bis.zip"))

    def test_decimal_finite(self):
        with self.assertRaisesRegex(ValueError, "finite"):
            lib.parse_signed_decimal("NaN", "test")

    def test_oversized_zip_fails(self):
        with self.assertRaisesRegex(ValueError, "Invalid ZIP byte count"):
            lib.inspect_archive_bytes(b"0" * (lib.MAX_ZIP_BYTES + 1))


if __name__ == "__main__":
    unittest.main()
