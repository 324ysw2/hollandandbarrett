from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "fetch_meta_ads_library.py"

spec = importlib.util.spec_from_file_location("fetch_meta_ads_library", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class MetaAdsLibraryTests(unittest.TestCase):
    def test_build_query_params(self) -> None:
        params = module.build_query_params(
            search_terms="스킨케어",
            countries=["KR"],
            limit=5,
        )
        self.assertEqual(params["search_terms"], "스킨케어")
        self.assertEqual(params["ad_reached_countries"], ["KR"])
        self.assertEqual(params["limit"], 5)

    def test_fetch_ads_archive_normalizes_payload(self) -> None:
        payload = {
            "data": [
                {
                    "id": "ads-1",
                    "ad_creation_time": "2026-07-01T00:00:00+0000",
                    "ad_creative_body": "진정한 보습",
                    "ad_creative_link_title": "스킨케어",
                    "ad_creative_link_description": "리뷰 기반",
                    "ad_snapshot_url": "https://example.com/1",
                }
            ]
        }

        with mock.patch.object(module, "build_request_url") as mock_url:
            mock_url.return_value = "https://graph.facebook.com"
            rows = module.normalize_ads(payload, search_terms="스킨케어")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "ads-1")
        self.assertEqual(rows[0]["body"], "진정한 보습")

    def test_write_outputs_creates_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_json = Path(tmpdir) / "ads.json"
            output_csv = Path(tmpdir) / "ads.csv"
            rows = [{"id": "a", "body": "hello", "created_time": "2026-07-01", "title": "", "description": "", "snapshot_url": "", "search_terms": "테스트"}]
            module.write_outputs(rows, output_json, output_csv)
            self.assertTrue(output_json.exists())
            self.assertTrue(output_csv.exists())
            data = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(data[0]["id"], "a")


if __name__ == "__main__":
    unittest.main()
