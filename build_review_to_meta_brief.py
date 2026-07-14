from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "brand_json_summaries"
INPUT_CSV = DATA_DIR / "ttamtti2_local_review_analysis.csv"
OUTPUT_JSON = DATA_DIR / "ttamtti2_review_to_meta_briefs.json"
OUTPUT_CSV = DATA_DIR / "ttamtti2_review_to_meta_briefs.csv"


def split_items(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[/,]", value or "") if item.strip()]


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def derive_ad_brief(row: dict[str, Any]) -> dict[str, Any]:
    brand = normalize_text(row.get("브랜드명", ""))
    group = normalize_text(row.get("대표그룹", ""))
    subtype = normalize_text(row.get("세부유형", ""))
    core_message = normalize_text(row.get("메인소구항목", ""))
    positive_keywords = split_items(row.get("긍정키워드", ""))
    negative_keywords = split_items(row.get("부정주의키워드", ""))
    review_excerpt = normalize_text(row.get("대표문장", ""))
    caution = normalize_text(row.get("주의항목", ""))
    top_keywords = split_items(row.get("상위키워드", ""))

    headline_seed = brand or "브랜드"
    if "진정" in core_message or "장벽" in group:
        headline = f"{headline_seed}, 민감 피부도 편안하게 쓰는 리뷰 기반 진정 케어"
        hero_message = "리뷰에서 반복된 진정·보습 포인트를 중심으로 광고 메시지를 구성합니다."
    elif "클렌징" in core_message or "클렌징" in group:
        headline = f"{headline_seed}, 세안 후까지 편안한 사용감을 보여주는 클렌징 제안"
        hero_message = "사용감과 세안 만족감을 중심으로 한 스토리로 광고를 구성합니다."
    elif "재구매" in core_message or "만족" in core_message:
        headline = f"{headline_seed}, 다시 찾는 이유가 있는 리뷰 기반 재구매 메시지"
        hero_message = "리뷰 반복 패턴을 바탕으로 재구매·만족감을 강조하는 광고 문구를 제안합니다."
    else:
        headline = f"{headline_seed}, 리뷰가 말하는 핵심 장점을 광고로 연결하는 제안"
        hero_message = "리뷰의 핵심 키워드를 광고 소재의 스토리로 변환합니다."

    positive_phrase = ", ".join(positive_keywords[:4]) if positive_keywords else "핵심 장점"
    negative_phrase = ", ".join(negative_keywords[:3]) if negative_keywords else "주의 포인트 미상"
    keyword_phrase = ", ".join(top_keywords[:4]) if top_keywords else "리뷰 키워드"

    return {
        "브랜드명": brand,
        "대표그룹": group,
        "세부유형": subtype,
        "소구핵심": core_message[:180],
        "광고헤드라인": headline,
        "광고본문": f"{brand}의 리뷰에서 {positive_phrase}가 반복적으로 확인되어, {hero_message} 리뷰 문장: {review_excerpt[:140] or '리뷰 근거 확보'}",
        "키워드제안": keyword_phrase,
        "주의포인트": f"{caution or '리뷰 기반 보완 포인트'} / {negative_phrase}",
    }


def build_briefs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [derive_ad_brief(row) for row in rows]


def write_outputs(briefs: list[dict[str, Any]]) -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(briefs, ensure_ascii=False, indent=2), encoding="utf-8")

    fieldnames = [
        "브랜드명",
        "대표그룹",
        "세부유형",
        "소구핵심",
        "광고헤드라인",
        "광고본문",
        "키워드제안",
        "주의포인트",
    ]
    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for brief in briefs:
            writer.writerow({key: brief.get(key, "") for key in fieldnames})


def main() -> None:
    parser = argparse.ArgumentParser(description="Create review-to-meta ad briefs from review analysis CSV")
    parser.add_argument("--input", default=str(INPUT_CSV))
    parser.add_argument("--output-json", default=str(OUTPUT_JSON))
    parser.add_argument("--output-csv", default=str(OUTPUT_CSV))
    args = parser.parse_args()

    with Path(args.input).open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    briefs = build_briefs(rows)
    write_outputs(briefs)

    print(f"Wrote {len(briefs)} briefs to {args.output_json} and {args.output_csv}")


if __name__ == "__main__":
    main()
