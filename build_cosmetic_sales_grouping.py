from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_SUMMARY_CSV = PROJECT_ROOT / "data" / "brand_json_summaries" / "ttamtti2_brand_faq_review_summary.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "brand_json_summaries"


GROUPS = [
    {
        "code": "C01",
        "name": "장벽/진정/민감 케어",
        "keywords": ["시카", "병풀", "판테놀", "세라마이드", "장벽", "진정", "민감", "저자극", "아토", "가려움", "홍조"],
        "description": "민감 피부, 장벽, 진정, 피부 컨디션 회복 메시지가 중심인 브랜드",
    },
    {
        "code": "C02",
        "name": "보습/수분/리페어",
        "keywords": ["보습", "수분", "촉촉", "히알루론", "히알루론산", "알로에", "리페어", "크림", "로션", "건조"],
        "description": "수분감, 보습 지속, 건조 완화, 데일리 크림/로션이 중심인 브랜드",
    },
    {
        "code": "C03",
        "name": "트러블/피지/모공",
        "keywords": ["트러블", "여드름", "피지", "모공", "스팟", "티트리", "각질", "블랙헤드", "아크네"],
        "description": "트러블, 피지, 모공, 각질처럼 고민 해결형 전환 문구가 필요한 브랜드",
    },
    {
        "code": "C04",
        "name": "선케어/아웃도어",
        "keywords": ["선크림", "선로션", "선케어", "자외선", "SPF", "태닝", "애프터선", "썬", "sun"],
        "description": "계절성, 야외활동, 자외선 차단/진정 메시지가 중요한 브랜드",
    },
    {
        "code": "C05",
        "name": "미백/잡티/톤업",
        "keywords": ["미백", "기미", "잡티", "색소", "멜라닌", "비타민C", "톤업", "화이트닝", "브라이트닝"],
        "description": "기미, 잡티, 톤 개선, 비타민 성분 등의 전후 비교 설득이 필요한 브랜드",
    },
    {
        "code": "C06",
        "name": "안티에이징/탄력/리프팅",
        "keywords": ["탄력", "리프팅", "주름", "콜라겐", "레티놀", "펩타이드", "PDRN", "EGF", "퍼밍", "노화"],
        "description": "고단가 기능성, 주름/탄력, 리프팅 기대효과를 신뢰감 있게 보여야 하는 브랜드",
    },
    {
        "code": "C07",
        "name": "클렌징/바디/헤어",
        "keywords": ["클렌징", "클렌저", "워시", "샴푸", "바디", "헤어", "트리트먼트", "스크럽", "비누", "세정"],
        "description": "사용 루틴, 향/사용감, 세정력과 자극 균형이 구매 포인트인 브랜드",
    },
    {
        "code": "C08",
        "name": "베이비/패밀리/임산부",
        "keywords": ["베이비", "아기", "유아", "키즈", "임산부", "맘", "어린이", "신생아", "패밀리"],
        "description": "아기/가족 사용, 순함, 안전성, 보호자 신뢰가 핵심인 브랜드",
    },
    {
        "code": "C09",
        "name": "여성청결/특수케어/의약외품",
        "keywords": ["여성청결", "Y존", "질", "의약외품", "상처", "제대혈", "의료", "소독", "약국", "병원"],
        "description": "민감한 효능 표현과 사용 전 확인 포인트가 중요한 특수 케어 브랜드",
    },
    {
        "code": "C10",
        "name": "프리미엄/향/브랜드 라이프스타일",
        "keywords": ["향수", "프래그런스", "퍼퓸", "럭셔리", "프리미엄", "에스테틱", "스파", "브랜드스토리"],
        "description": "감도, 브랜드 무드, 선물성, 프리미엄 이미지가 중심인 브랜드",
    },
]


SALES_PRODUCTS = {
    "S01": {
        "name": "리뷰/FAQ 기반 상세페이지 개선",
        "fit": "상세페이지, FAQ, 단점, 가격, 장점을 구매 전환 흐름으로 재배치",
    },
    "S02": {
        "name": "제안메일용 PPT/이미지 카드 제작",
        "fit": "브랜드별 핵심 근거를 한 장 이미지와 6-9장 PPT로 압축",
    },
    "S03": {
        "name": "네이버 검색광고/쇼핑 키워드 패키지",
        "fit": "고민 키워드, 성분 키워드, 가격/혜택 키워드를 광고그룹으로 분리",
    },
    "S04": {
        "name": "체험단/숏폼 리뷰 콘텐츠",
        "fit": "사용감, 전후 맥락, 후기/재구매 포인트를 짧은 콘텐츠로 증명",
    },
    "S05": {
        "name": "경쟁사 비교 랜딩/제안서",
        "fit": "경쟁사 상세페이지와 FAQ/후기 포인트를 비교해 차별점을 명확화",
    },
    "S06": {
        "name": "혜택/재구매 CRM 소재",
        "fit": "쿠폰, 무료배송, 세트, 정기배송, 재구매 메시지를 배너/메일로 전개",
    },
    "S07": {
        "name": "화장품 표현 리스크 검수",
        "fit": "치료/완치처럼 보일 수 있는 표현을 줄이고 안전한 효능 표현으로 정리",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Group cosmetic brand summaries and recommend sales products.")
    parser.add_argument("--summary-csv", default=str(DEFAULT_SUMMARY_CSV))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--prefix", default="ttamtti2_cosmetic_sales_grouping")
    return parser.parse_args()


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def clip(text: str, limit: int = 180) -> str:
    text = clean(text)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def keyword_hits(text: str, keywords: list[str]) -> list[str]:
    lowered = text.casefold()
    return [keyword for keyword in keywords if keyword.casefold() in lowered]


def row_blob(row: dict[str, str]) -> str:
    fields = [
        "브랜드명",
        "대표상품",
        "현재밀고있는상품",
        "브랜드_FAQ_키워드",
        "브랜드_FAQ_핵심",
        "브랜드_후기_키워드",
        "브랜드_후기_핵심",
        "브랜드_장점",
        "브랜드_단점",
        "경쟁사_상세페이지_키워드",
        "경쟁사_상세페이지_핵심",
        "경쟁사_FAQ_핵심",
        "경쟁사_후기_핵심",
        "PPT_핵심메시지",
        "이미지_대표키워드",
        "이미지_비주얼방향",
        "이미지_카피배지",
    ]
    return " ".join(clean(row.get(field, "")) for field in fields)


def primary_blob(row: dict[str, str]) -> str:
    fields = [
        "브랜드명",
        "대표상품",
        "현재밀고있는상품",
        "이미지_대표키워드",
        "이미지_카피배지",
    ]
    return " ".join(clean(row.get(field, "")) for field in fields)


def own_evidence_blob(row: dict[str, str]) -> str:
    fields = [
        "브랜드_FAQ_키워드",
        "브랜드_FAQ_핵심",
        "브랜드_후기_키워드",
        "브랜드_후기_핵심",
        "브랜드_장점",
        "브랜드_단점",
        "PPT_핵심메시지",
        "이미지_비주얼방향",
    ]
    return " ".join(clean(row.get(field, "")) for field in fields)


def competitor_blob(row: dict[str, str]) -> str:
    fields = [
        "경쟁사_상세페이지_키워드",
        "경쟁사_상세페이지_핵심",
        "경쟁사_FAQ_핵심",
        "경쟁사_후기_핵심",
    ]
    return " ".join(clean(row.get(field, "")) for field in fields)


def choose_group(row: dict[str, str]) -> tuple[dict[str, Any], list[str]]:
    primary = primary_blob(row)
    own = own_evidence_blob(row)
    competitor = competitor_blob(row)
    ranked: list[tuple[int, int, dict[str, Any], list[str]]] = []
    for index, group in enumerate(GROUPS):
        primary_hits = keyword_hits(primary, group["keywords"])
        own_hits = keyword_hits(own, group["keywords"])
        competitor_hits = keyword_hits(competitor, group["keywords"])
        score = len(primary_hits) * 4 + len(own_hits) * 2 + len(competitor_hits)
        hits = list(dict.fromkeys(primary_hits + own_hits + competitor_hits))
        ranked.append((score, -index, group, hits))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    score, _, group, hits = ranked[0]
    if score == 0:
        return {
            "code": "C99",
            "name": "검토필요/비화장품 가능",
            "description": "상품군 신호가 약하거나 수집 URL이 빗나간 브랜드",
        }, []
    return group, hits[:8]


def choose_subgroup(row: dict[str, str], group_name: str) -> tuple[str, list[str]]:
    blob = row_blob(row)
    rules = [
        ("후기 강점형", ["만족", "재구매", "추천", "좋", "후기로 확인", "별점"]),
        ("가격/혜택형", ["할인", "쿠폰", "무료배송", "1+1", "세트", "가성비", "저렴"]),
        ("FAQ/CS 보완형", ["교환", "반품", "환불", "문의", "배송", "결제", "주문", "품절"]),
        ("성분/효능 설득형", ["성분", "시카", "판테놀", "세라마이드", "콜라겐", "비타민", "PDRN", "저자극"]),
        ("사용감 증명형", ["발림", "흡수", "산뜻", "끈적", "향", "마무리감", "제형", "촉촉"]),
        ("경쟁사 비교형", ["경쟁사", "라인업", "상품명", "리뷰/Q&A", "브랜드 신뢰"]),
    ]
    scores = []
    for index, (name, keywords) in enumerate(rules):
        hits = keyword_hits(blob, keywords)
        scores.append((len(hits), -index, name, hits))
    scores.sort(key=lambda item: (item[0], item[1]), reverse=True)
    if scores[0][0] == 0:
        return f"{group_name} 기본형", []
    return scores[0][2], scores[0][3][:6]


def evidence_strength(row: dict[str, str]) -> int:
    fields = ["브랜드_FAQ_핵심", "브랜드_후기_핵심", "브랜드_장점", "브랜드_단점", "경쟁사_상세페이지_핵심"]
    return sum(1 for field in fields if clean(row.get(field)))


def recommend_sales(row: dict[str, str], group: dict[str, Any], subgroup: str) -> list[tuple[str, str]]:
    blob = row_blob(row)
    recs: list[tuple[str, str, int]] = []

    def add(code: str, reason: str, score: int) -> None:
        recs.append((code, reason, score))

    if clean(row.get("브랜드_FAQ_핵심")) or clean(row.get("브랜드_단점")) or clean(row.get("경쟁사_상세페이지_핵심")):
        add("S01", "FAQ/단점/경쟁사 상세페이지 근거가 있어 구매 전 확인 포인트를 상세페이지 흐름으로 바꾸기 좋음", 9)
    else:
        add("S01", "수집 근거가 약한 브랜드도 상세페이지 기본 구조 점검부터 시작하는 편이 안전함", 5)

    add("S02", "메일 제안에 바로 넣을 그룹 진단, 추천 이유, 이미지 배지 문구가 필요함", 8)

    if keyword_hits(blob, ["후기", "만족", "재구매", "추천", "발림", "흡수", "향", "촉촉", "산뜻", "사용감"]):
        add("S04", "사용감/후기/재구매 신호가 있어 숏폼이나 체험단에서 증거 장면을 만들기 좋음", 8)

    if keyword_hits(blob, ["할인", "쿠폰", "무료배송", "세트", "1+1", "가격", "판매가", "가성비", "정기배송"]):
        add("S06", "가격/혜택/세트 신호가 있어 쿠폰, 무료배송, 재구매 배너로 전환을 밀기 좋음", 7)

    if group["code"] in {"C01", "C02", "C03", "C04", "C05", "C06", "C07"} or keyword_hits(blob, ["검색", "기미", "트러블", "여드름", "선크림", "보습", "수분", "시카", "콜라겐", "미백"]):
        add("S03", "고민형/성분형 키워드가 있어 네이버 검색광고와 쇼핑 검색어를 그룹별로 쪼개기 좋음", 8)

    if clean(row.get("경쟁사")) or clean(row.get("경쟁사_상세페이지_핵심")):
        add("S05", "경쟁사 필드와 상세페이지 포인트가 있어 비교 제안서로 차별점을 만들 수 있음", 6)

    if group["code"] in {"C03", "C09"} or keyword_hits(blob, ["치료", "의약외품", "질환", "여드름", "가려움", "홍조", "아토", "트러블"]):
        add("S07", "고민/효능 표현이 강해 광고·상세페이지 문구를 보수적으로 검수해야 함", 7)

    if "FAQ/CS" in subgroup:
        add("S01", "세부그룹이 FAQ/CS 보완형이라 구매 불안을 줄이는 안내형 슬라이드가 필요함", 10)
    if "가격/혜택" in subgroup:
        add("S06", "세부그룹이 가격/혜택형이라 혜택 배지와 마감성 메시지가 바로 먹힘", 10)
    if "사용감" in subgroup or "후기" in subgroup:
        add("S04", "세부그룹이 후기/사용감형이라 실제 사용 장면 콘텐츠가 설득력이 큼", 10)

    best: dict[str, tuple[str, int]] = {}
    for code, reason, score in recs:
        if code not in best or score > best[code][1]:
            best[code] = (reason, score)
    ranked = sorted(best.items(), key=lambda item: item[1][1], reverse=True)[:3]
    return [(code, reason_score[0]) for code, reason_score in ranked]


def ppt_image_suggestion(row: dict[str, str], group: dict[str, Any], subgroup: str, sales: list[tuple[str, str]]) -> tuple[str, str]:
    brand = clean(row.get("브랜드명"))
    product = clean(row.get("현재밀고있는상품") or row.get("대표상품") or brand)
    badges = []
    blob = row_blob(row)
    for label, keywords in [
        ("진정/장벽", ["시카", "병풀", "판테놀", "장벽", "진정"]),
        ("촉촉한 보습감", ["보습", "수분", "촉촉"]),
        ("후기 기반 만족", ["만족", "재구매", "추천", "후기"]),
        ("구매 혜택", ["할인", "쿠폰", "무료배송", "1+1"]),
        ("저자극/민감피부", ["저자극", "민감", "순하"]),
        ("사용감 비교", ["발림", "흡수", "산뜻", "끈적"]),
    ]:
        if keyword_hits(blob, keywords):
            badges.append(label)
    if not badges:
        badges = [group["name"], subgroup]

    ppt = (
        f"{brand} 제안 PPT: 1) 브랜드/대표상품 '{clip(product, 50)}' 요약, "
        f"2) {group['name']} 그룹 진단, 3) {subgroup} 근거, "
        f"4) 추천 영업상품 {', '.join(SALES_PRODUCTS[code]['name'] for code, _ in sales)}, "
        "5) FAQ/단점은 구매 전 확인 포인트로 정리."
    )
    image = (
        f"메일 이미지: '{badges[0]}'을 메인 배지로 두고, "
        f"{', '.join(badges[1:4]) or '대표 성분/사용감'}을 보조 배지로 배치. "
        "화장품은 치료/완치 표현보다 사용감, 성분, 후기 근거 중심 카피 권장."
    )
    return ppt, image


def build_reason(row: dict[str, str], group: dict[str, Any], group_hits: list[str], subgroup: str, subgroup_hits: list[str], sales: list[tuple[str, str]]) -> str:
    parts = [
        f"그룹 근거: {', '.join(group_hits) if group_hits else group['description']}",
        f"세부 기준: {subgroup}" + (f"({', '.join(subgroup_hits)})" if subgroup_hits else ""),
    ]
    for field, label in [
        ("브랜드_장점", "장점"),
        ("브랜드_단점", "단점"),
        ("브랜드_FAQ_핵심", "FAQ"),
        ("브랜드_후기_핵심", "후기"),
        ("경쟁사_상세페이지_핵심", "경쟁사"),
    ]:
        value = clean(row.get(field))
        if value:
            parts.append(f"{label}: {clip(value, 130)}")
    parts.append("추천 상품 근거: " + " / ".join(f"{SALES_PRODUCTS[code]['name']} - {reason}" for code, reason in sales))
    return " | ".join(parts)


def process(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    output_rows: list[dict[str, str]] = []
    group_counter: Counter[str] = Counter()
    subgroup_counter: Counter[str] = Counter()
    sales_counter: Counter[str] = Counter()
    group_examples: dict[str, list[str]] = defaultdict(list)

    for row in rows:
        group, group_hits = choose_group(row)
        subgroup, subgroup_hits = choose_subgroup(row, group["name"])
        sales = recommend_sales(row, group, subgroup)
        ppt, image = ppt_image_suggestion(row, group, subgroup, sales)
        reason = build_reason(row, group, group_hits, subgroup, subgroup_hits, sales)
        sales_names = [SALES_PRODUCTS[code]["name"] for code, _ in sales]

        group_label = f"{group['code']} {group['name']}"
        group_counter[group_label] += 1
        subgroup_counter[subgroup] += 1
        for code, _ in sales:
            sales_counter[f"{code} {SALES_PRODUCTS[code]['name']}"] += 1
        if len(group_examples[group_label]) < 10:
            group_examples[group_label].append(clean(row.get("브랜드명")))

        output_rows.append(
            {
                "브랜드명": clean(row.get("브랜드명")),
                "파일명": clean(row.get("파일명")),
                "홈페이지": clean(row.get("홈페이지")),
                "대표상품": clean(row.get("대표상품")),
                "현재밀고있는상품": clean(row.get("현재밀고있는상품")),
                "경쟁사": clean(row.get("경쟁사")),
                "대그룹코드": group["code"],
                "대그룹": group["name"],
                "대그룹설명": group["description"],
                "세부그룹": subgroup,
                "그룹키워드근거": ", ".join(group_hits),
                "세부키워드근거": ", ".join(subgroup_hits),
                "근거강도": str(evidence_strength(row)),
                "추천영업상품": " / ".join(sales_names),
                "추천영업상품코드": " / ".join(code for code, _ in sales),
                "추천근거상세": reason,
                "PPT제안": ppt,
                "이미지제안": image,
                "메일첫문장제안": f"{clean(row.get('브랜드명'))}은(는) {group['name']} 안에서도 {subgroup}으로 보이며, 제안서는 {sales_names[0]} 중심으로 시작하는 것이 좋겠습니다.",
                "기존FAQ근거": clean(row.get("브랜드_FAQ_핵심")),
                "기존후기근거": clean(row.get("브랜드_후기_핵심")),
                "기존장점근거": clean(row.get("브랜드_장점")),
                "기존단점근거": clean(row.get("브랜드_단점")),
                "경쟁사근거": clean(row.get("경쟁사_상세페이지_핵심")),
                "이미지대표키워드": clean(row.get("이미지_대표키워드")),
                "이미지비주얼방향": clean(row.get("이미지_비주얼방향")),
                "이미지카피배지": clean(row.get("이미지_카피배지")),
            }
        )

    summary = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "brand_count": len(rows),
        "group_counts": dict(group_counter.most_common()),
        "subgroup_counts": dict(subgroup_counter.most_common()),
        "sales_product_counts": dict(sales_counter.most_common()),
        "group_examples": dict(group_examples),
        "sales_products": SALES_PRODUCTS,
    }
    return output_rows, summary


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]], summary: dict[str, Any]) -> None:
    lines = [
        "# 땀띠화장품2 세부 그룹 및 영업상품 추천",
        "",
        f"- 생성일: {summary['generated_at']}",
        f"- 분석 브랜드: {summary['brand_count']}개",
        "- 기준: 기존 FAQ/후기/장점/단점/가격/경쟁사 요약 + 제품 키워드 + 제안메일/PPT 활용성",
        "",
        "## 대그룹 요약",
        "",
        "| 그룹 | 브랜드 수 | 예시 브랜드 |",
        "|---|---:|---|",
    ]
    for group, count in summary["group_counts"].items():
        examples = ", ".join(summary["group_examples"].get(group, [])[:8])
        lines.append(f"| {group} | {count} | {examples} |")

    lines.extend(["", "## 추천 영업상품 분포", "", "| 영업상품 | 추천 브랜드 수 |", "|---|---:|"])
    for product, count in summary["sales_product_counts"].items():
        lines.append(f"| {product} | {count} |")

    lines.extend(["", "## 세부그룹 요약", "", "| 세부그룹 | 브랜드 수 |", "|---|---:|"])
    for subgroup, count in summary["subgroup_counts"].items():
        lines.append(f"| {subgroup} | {count} |")

    lines.extend(["", "## 브랜드별 추천 샘플", ""])
    for row in rows[:80]:
        lines.extend(
            [
                f"### {row['브랜드명']}",
                f"- 그룹: {row['대그룹코드']} {row['대그룹']} / {row['세부그룹']}",
                f"- 대표상품: {row['현재밀고있는상품'] or row['대표상품'] or '-'}",
                f"- 추천 영업상품: {row['추천영업상품']}",
                f"- 근거: {row['추천근거상세']}",
                f"- PPT: {row['PPT제안']}",
                f"- 이미지: {row['이미지제안']}",
                "",
            ]
        )
    if len(rows) > 80:
        lines.append(f"> 나머지 {len(rows) - 80}개 브랜드는 CSV/JSON에서 확인")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    summary_csv = Path(args.summary_csv).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    with summary_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"No rows found: {summary_csv}")

    grouped_rows, summary = process(rows)
    prefix = args.prefix
    csv_path = output_dir / f"{prefix}.csv"
    json_path = output_dir / f"{prefix}.json"
    md_path = output_dir / f"{prefix}.md"
    summary_path = output_dir / f"{prefix}_summary.json"

    write_csv(csv_path, grouped_rows)
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(grouped_rows, handle, ensure_ascii=False, indent=2)
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    write_markdown(md_path, grouped_rows, summary)

    print(f"brands={len(grouped_rows)}")
    print(f"csv={csv_path}")
    print(f"json={json_path}")
    print(f"markdown={md_path}")
    print(f"summary={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
