from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "build_review_to_meta_brief.py"

spec = importlib.util.spec_from_file_location("build_review_to_meta_brief", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class ReviewToMetaBriefTests(unittest.TestCase):
    def test_builds_ad_brief_from_review_row(self) -> None:
        row = {
            "브랜드명": "HYCL",
            "대표그룹": "보습/수분/리페어",
            "세부유형": "후기 강점형",
            "메인소구항목": "재구매/만족(95%+/0%-) / 보습/촉촉함(64%+/9%-)",
            "긍정키워드": "좋, 좋아, 촉촉, 만족",
            "부정주의키워드": "자극, 비싸",
            "대표문장": "순하고 촉촉한 클렌저라 재구매 중입니다",
            "주의항목": "트러블/자극 주의",
            "상위키워드": "보습, 수분, 촉촉",
        }

        brief = module.derive_ad_brief(row)

        self.assertEqual(brief["브랜드명"], "HYCL")
        self.assertIn("재구매/만족", brief["소구핵심"])
        self.assertIn("HYCL", brief["광고헤드라인"])
        self.assertIn("리뷰", brief["광고본문"])
        self.assertIn("자극", brief["주의포인트"]) or self.assertIn("비싸", brief["주의포인트"])


if __name__ == "__main__":
    unittest.main()
