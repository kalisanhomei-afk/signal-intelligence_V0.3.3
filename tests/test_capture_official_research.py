"""Offline unit tests; never contacts a website."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

src = Path(__file__).resolve().parents[1] / 'scripts' / 'capture_official_research.py'
spec = importlib.util.spec_from_file_location('capture_official_research', src)
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)

class FakeResponse(io.BytesIO):
    def __init__(self, data, final_url, content_type):
        super().__init__(data)
        self._url = final_url
        self.status = 200
        self.headers = {'Content-Type': content_type, 'Content-Length': str(len(data))}
    def geturl(self):
        return self._url

class FakeOpener:
    def __init__(self, data, final_url, content_type='text/html'):
        self.data = data
        self.final_url = final_url
        self.content_type = content_type
    def open(self, request, timeout=20):
        return FakeResponse(self.data, self.final_url, self.content_type)

class CaptureTests(unittest.TestCase):
    H6 = 'https://www.federalreserve.gov/releases/h6/20200827/'
    TIC = 'https://home.treasury.gov/resource-center/data-chart-center/tic/Documents/ticrel_20200316.zip'

    def test_disallow_unsafe_urls(self):
        urls = ['http://www.federalreserve.gov/x', 'https://evil.example/x',
                'https://www.federalreserve.gov.evil.example/x',
                'https://u:p@www.federalreserve.gov/x',
                'https://www.federalreserve.gov:444/x',
                'https://home.treasury.gov/x?api_key=SECRET',
                'https://127.0.0.1/x']
        for url in urls:
            with self.subTest(url=url), self.assertRaises(ValueError):
                capture.validate_url(url)

    def test_allow_known_official_sites(self):
        self.assertEqual(capture.validate_url(self.TIC), 'treasury')
        self.assertEqual(capture.validate_url(self.H6), 'federalreserve')

    def test_html_captures_exact_bytes_and_no_pit_claim(self):
        raw = b'<!doctype html><html><body>official archived example</body></html>'
        with tempfile.TemporaryDirectory() as td:
            rec = capture.capture(self.H6, 'html', Path(td), opener=FakeOpener(raw, self.H6))
            raw_saved = (Path(td) / rec['saved_raw_basename']).read_bytes()
            manifest = json.loads(Path(rec['local_receipt_path']).read_text())
            self.assertEqual(raw, raw_saved)
            self.assertEqual(rec['raw_body_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(manifest['raw_body_sha256'], rec['raw_body_sha256'])
            self.assertIsNone(manifest['reported_publication_utc'])
            self.assertFalse(manifest['accepted_for_model'])
            self.assertFalse(manifest['contemporaneous_original_file_certified'])
            self.assertEqual(manifest['status'], 'CAPTURED_NOT_PIT_VERIFIED')

    def test_block_cross_agency_final_redirect(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, 'Cross-agency'):
                capture.capture(self.H6, 'html', Path(td), opener=FakeOpener(b'<html></html>', self.TIC))
            self.assertEqual(list(Path(td).iterdir()), [])

    def test_block_excess_body(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, 'excessive response size|larger than byte limit'):
                capture.capture(self.H6, 'html', Path(td), max_bytes=100,
                                opener=FakeOpener(b'<html>' + b'x'*500, self.H6))
            self.assertFalse(list(Path(td).iterdir()))

    @staticmethod
    def make_zip(member='sample.txt'):
        b = io.BytesIO()
        with zipfile.ZipFile(b, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr(member, b'official fixture')
        return b.getvalue()

    def test_valid_zip(self):
        zdata = self.make_zip()
        with tempfile.TemporaryDirectory() as td:
            rec = capture.capture(self.TIC, 'zip', Path(td), opener=FakeOpener(zdata, self.TIC, 'application/zip'))
            self.assertEqual(rec['archive_inspection']['member_count'], 1)
            self.assertEqual((Path(td) / rec['saved_raw_basename']).read_bytes(), zdata)

    def test_zip_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, 'Unsafe ZIP'):
                capture.capture(self.TIC, 'zip', Path(td), opener=FakeOpener(self.make_zip('../bad.txt'), self.TIC))
            self.assertFalse(list(Path(td).iterdir()))

    def test_non_zip_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                capture.capture(self.TIC, 'zip', Path(td), opener=FakeOpener(b'<html>not a zip</html>', self.TIC))
            self.assertFalse(list(Path(td).iterdir())

if __name__ == '__main__':
    unittest.main()
