# This Python file uses the following encoding: utf-8
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = PROJECT_ROOT.parent / "땀띠화장품"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "brand_json_summaries"
PPT_IMAGE_KEY = "PPT_이미지_반영"

SECTION_KEYS = {
    "competitor_detail": "경쟁사 상세페이지 분석",
    "faq": "FAQ 분석",
    "reviews": "후기 수집",
    "landing": "랜딩페이지 분석",
    "pros": "장점",
    "cons": "단점",
}

STOPWORDS = {
    "브랜드",
    "제품",
    "상품",
    "사용",
    "구매",
    "리뷰",
    "후기",
    "상세",
    "정보",
    "보기",
    "등록",
    "현재",
    "위치",
    "로그인",
    "회원가입",
    "장바구니",
    "주문조회",
    "마이페이지",
    "copyright",
    "search",
    "q&a",
    "faq",
    "event",
    "review",
    "reviews",
    "shipping",
    "customer",
    "center",
    "best",
    "view",
    "more",
    "가격",
    "판매가",
    "소비자가",
    "국내",
    "해외배송",
    "가능상품",
    "기본",
    "품절",
    "바로",
    "정기배송",
    "예약주문",
    "추가",
    "쿠폰",
    "다운로드",
    "신고하기",
    "사업자",
    "주소",
    "전화",
    "이메일",
    "개인정보",
    "이용약관",
    "내용",
    "페이지",
    "전체",
    "on",
    "off",
    "and",
    "or",
    "the",
    "for",
    "with",
    "from",
    "about",
    "purchase",
    "tests",
    "메인",
    "모듈",
    "상품보기",
    "뒤로가기",
    "낮은가격",
    "높은가격",
    "신상품",
    "인기상품순",
    "상품명순",
    "조회순",
    "언급",
    "근거",
    "포함",
    "쇼핑몰별",
    "최저가",
    "판매가",
}

NOISE_TERMS = {
    "로그인",
    "회원가입",
    "장바구니",
    "주문조회",
    "마이페이지",
    "Copyright",
    "SHIPPING TO",
    "사업자등록",
    "개인정보",
    "이용약관",
    "신고하기",
    "신고사유",
    "쿠폰 다운로드",
    "성인인증",
    "글읽기 권한",
    "검색 삭제",
    "고객센터",
    "통신판매",
    "닫기",
    "수집 실패",
    "ON 메인",
    "OFF ON",
    "상품보기",
    "뒤로가기",
    "상품비교",
    "낮은가격",
    "높은가격",
    "최근 본 상품",
    "현재 위치",
    "Hit enter",
    "ESC to close",
    "successfully added to your cart",
    "About Purchase Tests",
    "인기 검색어",
    "색상 미리보기",
    "샘플 사이트",
    "포인트 색상",
    "RGB 원색",
}

POSITIVE_TERMS = {
    "좋",
    "만족",
    "추천",
    "재구매",
    "순하",
    "촉촉",
    "보습",
    "진정",
    "효과",
    "산뜻",
    "가벼",
    "부드",
    "흡수",
    "빠르",
    "깔끔",
    "저렴",
    "가성비",
    "향",
    "자극없",
    "편하",
    "신선",
    "고급",
    "은은",
}

NEGATIVE_TERMS = {
    "아쉽",
    "별로",
    "싫",
    "자극",
    "트러블",
    "건조함",
    "끈적",
    "비싸",
    "불편",
    "냄새",
    "기름",
    "무겁",
    "부족",
    "품절",
    "반품",
    "환불",
    "배송지연",
    "느리",
    "안맞",
    "안 맞",
    "실망",
    "유통기한",
}

FAQ_TERMS = {
    "배송",
    "교환",
    "반품",
    "환불",
    "결제",
    "주문",
    "품절",
    "유통기한",
    "사용법",
    "구매안내",
    "문의",
    "고객센터",
    "무통장",
    "입금",
}

FAQ_ASPECTS = {
    "배송/출고": ["배송", "출고", "택배", "무료배송", "해외배송", "정기배송"],
    "교환/반품/환불": ["교환", "반품", "환불", "취소", "반송"],
    "결제/주문": ["결제", "주문", "무통장", "입금", "카드", "구매"],
    "유통기한/품질": ["유통기한", "개봉", "품질", "하자", "파손"],
    "상품문의/Q&A": ["Q&A", "상품문의", "문의", "게시물", "질문"],
    "고객센터/상담": ["고객센터", "상담", "전화", "문의하기", "운영시간"],
    "회원/쿠폰/혜택": ["회원", "쿠폰", "적립", "포인트", "할인", "이벤트"],
}

POSITIVE_ASPECTS = {
    "보습/촉촉함": ["보습", "촉촉", "수분", "건조한 피부", "건조"],
    "진정/피부장벽": ["진정", "시카", "병풀", "티트리", "장벽", "트러블"],
    "순함/저자극": ["순하", "저자극", "자극없", "민감", "편안"],
    "발림/흡수/산뜻함": ["발림", "흡수", "산뜻", "가벼운", "끈적임 없이", "마무리감"],
    "향/사용감": ["향", "아로마", "은은", "향기", "사용감"],
    "만족/재구매": ["만족", "좋", "추천", "재구매", "또사용", "감사"],
    "가격/혜택": ["할인", "쿠폰", "1+1", "무료배송", "저렴", "가성비"],
}

NEGATIVE_ASPECTS = {
    "향/냄새 불만": ["냄새", "향이 싫", "기름냄새", "역한", "향 불호"],
    "자극/트러블": ["자극", "트러블", "따가", "붉어", "가려", "민감"],
    "건조/보습 부족": ["건조함", "당김", "보습 부족", "각질", "건조해"],
    "끈적임/무거움": ["끈적", "무겁", "기름", "번들"],
    "가격/용량 아쉬움": ["비싸", "가격대", "용량 아쉽", "양이 적", "아쉽"],
    "배송/CS 불만": ["배송지연", "배송 느리", "늦게", "오배송", "불친절", "응대 불만"],
    "유통기한/품질 이슈": ["유통기한", "임박", "파손", "하자", "불량"],
    "리뷰/정보 부족": ["게시물이 없습니다", "리뷰 0", "Q&A 0", "정보 부족"],
}

REVIEW_ASPECTS = {
    **POSITIVE_ASPECTS,
    **NEGATIVE_ASPECTS,
}

DETAIL_ASPECTS = {
    "상품/라인업": ["상품명", "라인", "세트", "기획전", "카테고리", "구성"],
    "가격/할인": ["판매가", "소비자가", "할인", "쿠폰", "1+1", "무료배송"],
    "리뷰/Q&A 규모": ["리뷰", "사용후기", "Q&A", "상품문의", "별점"],
    "성분/효능 메시지": ["성분", "진정", "보습", "시카", "병풀", "장벽", "저자극"],
    "사용감 메시지": ["산뜻", "흡수", "발림", "촉촉", "향", "마무리감"],
    "구매 유도": ["바로 구매", "장바구니", "정기배송", "관심상품", "혜택"],
    "브랜드 신뢰": ["브랜드", "고객센터", "공지사항", "회사소개", "사업자"],
}

WORD_RE = re.compile(r"[가-힣A-Za-z0-9]{2,}")
SPLIT_RE = re.compile(r"(?<=[.!?。！？])\s+|[\r\n]+|(?<=다)\s+(?=[가-힣A-Za-z0-9])")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize brand JSON FAQ/reviews/pros/cons without API or local LLM."
    )
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR), help="Folder containing brand JSON files")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Folder for CSV/JSON/Markdown outputs")
    parser.add_argument("--top-sentences", type=int, default=5, help="Representative sentences per section")
    parser.add_argument("--top-keywords", type=int, default=12, help="Keywords per section")
    parser.add_argument("--max-files", type=int, default=0, help="Optional limit for quick tests; 0 means all")
    parser.add_argument(
        "--only-file",
        action="append",
        default=[],
        help="Process only the given JSON filename. Can be used multiple times.",
    )
    parser.add_argument("--prefix", default="", help="Output filename prefix. Defaults to timestamped name")
    parser.add_argument(
        "--write-back-json",
        action="store_true",
        help="Update only FAQ/review/pro/con/competitor analysis fields in the source JSON files.",
    )
    parser.add_argument(
        "--write-back-ppt-image",
        action="store_true",
        help="Add or update only the PPT/image brief field in the source JSON files.",
    )
    return parser.parse_args()


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def flatten_text(value: Any) -> list[str]:
    texts: list[str] = []
    if value is None:
        return texts
    if isinstance(value, str):
        text = normalize_space(value)
        if text:
            texts.append(text)
        return texts
    if isinstance(value, dict):
        for nested in value.values():
            texts.extend(flatten_text(nested))
        return texts
    if isinstance(value, list):
        for nested in value:
            texts.extend(flatten_text(nested))
        return texts
    text = normalize_space(str(value))
    if text:
        texts.append(text)
    return texts


def normalize_space(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text).replace("\u00a0", " ")).strip()
    return text


def norm_name(value: str) -> str:
    return re.sub(r"[\s/|·ㆍ,()（）\[\]{}]+", "", value or "").casefold()


def domain(url: str) -> str:
    try:
        parsed = urlparse(url)
    except Exception:
        return ""
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def iter_tool_records(doc: dict[str, Any], tool_name: str | None = None) -> Iterable[dict[str, Any]]:
    tools = doc.get("tool_analysis") or {}
    if tool_name:
        for row in as_list(tools.get(tool_name)):
            if isinstance(row, dict):
                yield row
        return
    for rows in tools.values():
        for row in as_list(rows):
            if isinstance(row, dict):
                yield row


def collect_field(doc: dict[str, Any], key: str, tool_name: str | None = None) -> list[str]:
    texts: list[str] = []
    for record in iter_tool_records(doc, tool_name):
        texts.extend(flatten_text(record.get(key)))
    return dedupe_texts(texts)


def collect_scrapecraft(doc: dict[str, Any], key: str) -> list[str]:
    return collect_field(doc, key, "ScrapeCraft")


def split_sentences(texts: Iterable[str]) -> list[str]:
    sentences: list[str] = []
    seen: set[str] = set()
    for text in texts:
        text = normalize_space(text)
        if not text:
            continue
        chunks = SPLIT_RE.split(text)
        if len(chunks) == 1 and len(text) > 260:
            chunks = re.split(r"\s{2,}|(?<=\))\s+|(?<=요)\s+", text)
        for chunk in chunks:
            chunk = normalize_space(chunk)
            if len(chunk) > 260:
                chunk = chunk[:260].strip()
            if len(chunk) < 12:
                continue
            if is_noise_sentence(chunk):
                continue
            key = compact_key(chunk)
            if key in seen:
                continue
            seen.add(key)
            sentences.append(chunk)
    return sentences


def is_noise_sentence(text: str) -> bool:
    lowered = text.casefold()
    if "수집 실패" in text:
        return True
    if any(noise.casefold() in lowered for noise in NOISE_TERMS):
        return True
    nav_terms = [
        "로그인",
        "회원가입",
        "장바구니",
        "주문조회",
        "마이쇼핑",
        "상품보기",
        "뒤로가기",
        "상품비교",
        "낮은가격",
        "높은가격",
        "최근 본 상품",
    ]
    if sum(1 for term in nav_terms if term.casefold() in lowered) >= 3:
        return True
    return False


def compact_key(text: str) -> str:
    return re.sub(r"\W+", "", text).casefold()[:120]


def dedupe_texts(texts: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for text in texts:
        text = normalize_space(text)
        if not text:
            continue
        key = compact_key(text)
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def words_from_texts(texts: Iterable[str]) -> list[str]:
    words: list[str] = []
    for text in texts:
        for word in WORD_RE.findall(text):
            lowered = word.casefold()
            if lowered in STOPWORDS:
                continue
            if len(word) < 2 or len(word) > 18:
                continue
            if word.isdigit():
                continue
            words.append(word)
    return words


def top_keywords(texts: Iterable[str], limit: int) -> list[str]:
    usable_texts = [text for text in texts if not is_noise_sentence(text)]
    counter = Counter(words_from_texts(usable_texts))
    return [word for word, _ in counter.most_common(limit)]


def contains_any(text: str, terms: set[str]) -> bool:
    lowered = text.casefold()
    return any(term.casefold() in lowered for term in terms)


def sentence_score(sentence: str, keyword_counter: Counter[str], mode: str = "neutral") -> float:
    words = WORD_RE.findall(sentence)
    score = sum(keyword_counter.get(word, 0) for word in words)
    score += min(len(words), 28) * 0.18

    if 35 <= len(sentence) <= 180:
        score += 3
    if mode == "positive" and contains_any(sentence, POSITIVE_TERMS):
        score += 8
    if mode == "negative" and contains_any(sentence, NEGATIVE_TERMS):
        score += 8
    if mode == "faq" and contains_any(sentence, FAQ_TERMS):
        score += 6

    for noise in NOISE_TERMS:
        if noise.casefold() in sentence.casefold():
            score -= 5
    if len(sentence) > 220:
        score -= 3
    return score


def representative_sentences(texts: Iterable[str], limit: int, mode: str = "neutral") -> list[str]:
    sentences = split_sentences(texts)
    if not sentences:
        return []

    if mode == "positive":
        preferred = [sentence for sentence in sentences if contains_any(sentence, POSITIVE_TERMS)]
        if preferred:
            sentences = preferred
        else:
            return []
    elif mode == "negative":
        preferred = [sentence for sentence in sentences if contains_any(sentence, NEGATIVE_TERMS)]
        if preferred:
            sentences = preferred
        else:
            return []
    elif mode == "faq":
        preferred = [sentence for sentence in sentences if contains_any(sentence, FAQ_TERMS)]
        if preferred:
            sentences = preferred
        else:
            return []

    keyword_counter = Counter(words_from_texts(sentences))
    ranked = sorted(
        sentences,
        key=lambda sentence: sentence_score(sentence, keyword_counter, mode),
        reverse=True,
    )
    return ranked[:limit]


def aspect_map_for_mode(mode: str) -> dict[str, list[str]]:
    if mode == "faq":
        return FAQ_ASPECTS
    if mode == "positive":
        return POSITIVE_ASPECTS
    if mode == "negative":
        return NEGATIVE_ASPECTS
    if mode == "review":
        return REVIEW_ASPECTS
    if mode == "detail":
        return DETAIL_ASPECTS
    return {}


def aspect_bullets(texts: Iterable[str], mode: str, limit: int) -> list[str]:
    aspect_map = aspect_map_for_mode(mode)
    if not aspect_map:
        return []

    text_list = [normalize_space(text) for text in texts if normalize_space(text)]
    joined = "\n".join(text_list)
    sentences = split_sentences(text_list)
    ranked: list[tuple[int, str]] = []

    for aspect, terms in aspect_map.items():
        matched_terms = [term for term in terms if term.casefold() in joined.casefold()]
        if not matched_terms:
            continue
        count = sum(joined.casefold().count(term.casefold()) for term in matched_terms)
        evidence = find_evidence(
            sentences,
            matched_terms,
            skip_negated_negative=mode == "negative" or aspect in NEGATIVE_ASPECTS,
        )
        if mode in {"positive", "negative", "review"} and not evidence:
            continue
        term_text = ", ".join(matched_terms[:4])
        if evidence:
            bullet = f"{aspect}: {term_text} 언급. 근거: {evidence}"
        else:
            bullet = f"{aspect}: {term_text} 언급."
        ranked.append((count, bullet))

    ranked.sort(key=lambda row: row[0], reverse=True)
    return [bullet for _, bullet in ranked[:limit]]


def find_evidence(sentences: list[str], terms: list[str], skip_negated_negative: bool = False) -> str:
    candidates = [
        sentence
        for sentence in sentences
        if contains_any(sentence, set(terms)) and not is_noise_sentence(sentence)
    ]
    if skip_negated_negative:
        candidates = [sentence for sentence in candidates if not has_negative_negation(sentence)]
    if not candidates:
        return ""
    candidates.sort(key=lambda sentence: (abs(len(sentence) - 90), len(sentence)))
    return shorten(candidates[0], 150)


def has_negative_negation(sentence: str) -> bool:
    patterns = [
        "없이",
        "없고",
        "없어요",
        "없습니다",
        "없어서",
        "없는",
        "않고",
        "않아요",
        "않습니다",
        "안 나",
        "독하지",
        "자극이 없",
        "자극 없",
        "끈적임 없이",
        "끈적이지",
        "기름지지",
        "부담스럽지",
    ]
    return any(pattern in sentence for pattern in patterns)


def shorten(text: str, limit: int) -> str:
    text = normalize_space(text)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def section_summary(texts: list[str], top_sentences: int, top_words: int, mode: str = "neutral") -> dict[str, Any]:
    return {
        "mode": mode,
        "count": len(texts),
        "keywords": top_keywords(texts, top_words),
        "topics": aspect_bullets(texts, mode, min(top_sentences, 6)),
        "sentences": representative_sentences(texts, top_sentences, mode),
    }


def join_sentences(sentences: list[str]) -> str:
    return " / ".join(sentences)


def join_points(section: dict[str, Any]) -> str:
    topics = section.get("topics") or []
    if topics:
        return " / ".join(topics)
    if section.get("mode") in {"positive", "negative"}:
        return ""
    return join_sentences(section.get("sentences") or [])


def topic_label(point: str) -> str:
    return normalize_space(point.split(":", 1)[0])


def compact_point(point: str, limit: int = 120) -> str:
    point = normalize_space(point)
    if "근거:" in point:
        head, evidence = point.split("근거:", 1)
        evidence = normalize_space(evidence)
        if evidence.startswith("근거:"):
            evidence = normalize_space(evidence[3:])
        point = f"{head.strip()} 근거: {shorten(evidence.strip(), limit)}"
    return shorten(point, limit + 40)


def brief_points(section: dict[str, Any], limit: int = 4, allow_sentences: bool = True) -> list[str]:
    topics = section.get("topics") or []
    if topics:
        return [compact_point(point) for point in topics[:limit]]
    if allow_sentences:
        return [shorten(sentence, 140) for sentence in (section.get("sentences") or [])[:limit]]
    return []


def labels_from_sections(*sections: dict[str, Any], limit: int = 8) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for section in sections:
        for point in section.get("topics") or []:
            label = topic_label(point)
            if not label or label in seen:
                continue
            seen.add(label)
            labels.append(label)
            if len(labels) >= limit:
                return labels
    return labels


def keywords_from_sections(*sections: dict[str, Any], limit: int = 12) -> list[str]:
    keywords: list[str] = []
    seen: set[str] = set()
    for section in sections:
        for keyword in section.get("keywords") or []:
            keyword = normalize_space(keyword)
            if not keyword or keyword.casefold() in seen:
                continue
            seen.add(keyword.casefold())
            keywords.append(keyword)
            if len(keywords) >= limit:
                return keywords
    return keywords


def visual_direction_from_labels(labels: list[str]) -> list[str]:
    rules = [
        ("보습/촉촉함", "물방울, 수분막, 피부결 클로즈업으로 촉촉함을 시각화"),
        ("진정/피부장벽", "시카/병풀/장벽 보호를 연상시키는 그린 톤 성분 컷과 보호막 그래픽"),
        ("순함/저자극", "민감 피부도 편안하게 쓰는 느낌의 깨끗한 배경, 부드러운 피부 톤"),
        ("발림/흡수/산뜻함", "가벼운 텍스처 스와치, 빠르게 흡수되는 사용 장면"),
        ("향/사용감", "은은한 향과 사용감을 보여주는 라이프스타일 컷"),
        ("만족/재구매", "리뷰 별점, 재구매, 추천 배지를 카드뉴스형으로 배치"),
        ("가격/혜택", "1+1, 쿠폰, 무료배송 등 혜택 배지를 명확히 노출"),
        ("유통기한/품질 이슈", "유통기한/개봉 후 사용 가능 기간을 작게 숨기지 말고 안내 박스로 노출"),
        ("리뷰/정보 부족", "리뷰 수, Q&A, 사용법 등 신뢰 보강 정보를 별도 카드로 배치"),
    ]
    directions: list[str] = []
    for label in labels:
        for key, text in rules:
            if key == label and text not in directions:
                directions.append(text)
    return directions[:6]


def image_copy_from_labels(labels: list[str]) -> list[str]:
    copy_map = {
        "보습/촉촉함": "촉촉한 보습감",
        "진정/피부장벽": "진정과 장벽 케어",
        "순함/저자극": "민감 피부도 편안하게",
        "발림/흡수/산뜻함": "산뜻한 마무리감",
        "향/사용감": "은은한 사용감",
        "만족/재구매": "후기로 확인한 만족도",
        "가격/혜택": "구매 혜택 강조",
        "유통기한/품질 이슈": "구매 전 확인 포인트",
        "리뷰/정보 부족": "리뷰와 Q&A 보강 필요",
    }
    return [copy_map[label] for label in labels if label in copy_map][:8]


def build_ppt_image_brief(result: dict[str, Any]) -> dict[str, Any]:
    brand = result["brand"]
    competitor = result["competitor"]
    strength_points = brief_points(brand["strengths"], 5, allow_sentences=False)
    weakness_points = brief_points(brand["weaknesses"], 4, allow_sentences=False)
    faq_points = brief_points(brand["faq_analysis"], 4)
    review_points = brief_points(brand["review_collection"], 5)
    competitor_points = (
        brief_points(competitor["detail_page_analysis"], 4)
        + brief_points(competitor["faq_analysis"], 2)
        + brief_points(competitor["review_collection"], 2)
    )
    labels = labels_from_sections(
        brand["strengths"],
        brand["review_collection"],
        brand["weaknesses"],
        brand["faq_analysis"],
        limit=10,
    )
    keywords = keywords_from_sections(
        brand["strengths"],
        brand["review_collection"],
        brand["faq_analysis"],
        competitor["detail_page_analysis"],
        limit=12,
    )

    product = result["current_product"] or result["representative_product"] or result["brand_name"]
    key_message = strength_points[:3] or review_points[:3] or faq_points[:3]
    slide_flow = [
        f"브랜드/대표상품 개요: {product}",
        "후기 기반 강점: 장점/후기 수집 항목에서 반복되는 긍정 포인트를 카드형으로 제시",
        "구매 전 확인 포인트: FAQ와 단점 항목을 숨기지 말고 안내형 슬라이드로 정리",
    ]
    if result["competitor_name"]:
        slide_flow.append(f"경쟁사 비교: {result['competitor_name']}의 상세페이지/FAQ/후기 포인트와 대비")
    slide_flow.append("이미지 적용안: 대표 키워드, 사용감, 혜택 배지를 상세페이지와 PPT 이미지에 반영")

    return {
        "PPT 반영": {
            "슬라이드 제목": f"{result['brand_name']} FAQ/후기 기반 제안",
            "핵심 메시지": key_message,
            "장점 강조": strength_points,
            "보완/주의": weakness_points,
            "FAQ/CS 반영": faq_points,
            "경쟁사 비교": competitor_points,
            "추천 슬라이드 구성": slide_flow,
        },
        "이미지 반영": {
            "대표 키워드": (labels + [keyword for keyword in keywords if keyword not in labels])[:12],
            "비주얼 방향": visual_direction_from_labels(labels),
            "이미지 카피/배지": image_copy_from_labels(labels),
            "상세페이지 이미지 포인트": [
                point
                for point in (strength_points[:3] + weakness_points[:2] + faq_points[:2])
                if point
            ],
            "주의할 표현": [
                "후기 근거가 약한 효능 단정 표현은 피하기",
                "의약품처럼 보이는 치료/완치 표현은 피하기",
                "단점이나 FAQ 이슈는 숨기기보다 구매 전 확인 포인트로 안내하기",
            ],
        },
        "생성 기준": {
            "브랜드": result["brand_name"],
            "대표상품": result["representative_product"],
            "현재밀고있는상품": result["current_product"],
            "경쟁사": result["competitor_name"],
            "경쟁사파일": result["competitor_file"],
            "자료": "JSON 내 FAQ 분석, 후기 수집, 장점, 단점, 경쟁사 분석 요약 기반",
        },
    }


def find_competitor_doc(
    competitor_name: str,
    brand_index: dict[str, tuple[Path, dict[str, Any]]],
) -> tuple[Path | None, dict[str, Any] | None]:
    normalized = norm_name(competitor_name)
    if not normalized:
        return None, None
    if normalized in brand_index:
        return brand_index[normalized]
    for key, value in brand_index.items():
        if normalized in key or key in normalized:
            return value
    return None, None


def build_brand_index(files: list[Path]) -> dict[str, tuple[Path, dict[str, Any]]]:
    index: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path in files:
        try:
            doc = load_json(path)
        except Exception as exc:
            print(f"Skip index file {path.name}: {exc}")
            continue
        candidates = [
            str(doc.get("brand_name") or ""),
            path.stem,
            str((doc.get("summary") or {}).get("업체") or ""),
        ]
        for candidate in candidates:
            key = norm_name(candidate)
            if key and key not in index:
                index[key] = (path, doc)
    return index


def summarize_one(
    path: Path,
    doc: dict[str, Any],
    brand_index: dict[str, tuple[Path, dict[str, Any]]],
    top_sentences: int,
    top_words: int,
) -> dict[str, Any]:
    summary = doc.get("summary") or {}
    brand_name = str(doc.get("brand_name") or summary.get("업체") or path.stem)
    homepage = str(doc.get("homepage") or summary.get("홈페이지 URL") or "")
    own_domain = domain(homepage)

    competitor_name = str(summary.get("경쟁사") or "")
    competitor_path, competitor_doc = find_competitor_doc(competitor_name, brand_index)
    competitor_source = "matched_json" if competitor_doc else "current_json_field"

    brand_faq = collect_field(doc, SECTION_KEYS["faq"], "Firecrawl")
    brand_reviews = collect_field(doc, SECTION_KEYS["reviews"], "Firecrawl")
    brand_landing = collect_field(doc, SECTION_KEYS["landing"], "Firecrawl")
    brand_pros = collect_scrapecraft(doc, SECTION_KEYS["pros"]) + brand_reviews + brand_landing
    brand_cons = collect_scrapecraft(doc, SECTION_KEYS["cons"]) + brand_reviews

    if competitor_doc:
        competitor_detail = (
            collect_field(competitor_doc, SECTION_KEYS["competitor_detail"], "Firecrawl")
            + collect_field(competitor_doc, SECTION_KEYS["landing"], "Firecrawl")
        )
        competitor_faq = collect_field(competitor_doc, SECTION_KEYS["faq"], "Firecrawl")
        competitor_reviews = collect_field(competitor_doc, SECTION_KEYS["reviews"], "Firecrawl")
    else:
        competitor_detail = collect_field(doc, SECTION_KEYS["competitor_detail"], "Firecrawl")
        competitor_faq = collect_external_field(doc, SECTION_KEYS["faq"], own_domain)
        competitor_reviews = collect_external_field(doc, SECTION_KEYS["reviews"], own_domain)

    brand_faq_result = section_summary(brand_faq, top_sentences, top_words, "faq")
    brand_review_result = section_summary(brand_reviews, top_sentences, top_words, "review")
    brand_pro_result = section_summary(brand_pros, top_sentences, top_words, "positive")
    brand_con_result = section_summary(brand_cons, top_sentences, top_words, "negative")
    competitor_detail_result = section_summary(competitor_detail, top_sentences, top_words, "detail")
    competitor_faq_result = section_summary(competitor_faq, top_sentences, top_words, "faq")
    competitor_review_result = section_summary(competitor_reviews, top_sentences, top_words, "review")

    result = {
        "brand_name": brand_name,
        "file_name": path.name,
        "homepage": homepage,
        "homepage_domain": own_domain,
        "representative_product": str(summary.get("대표상품") or ""),
        "current_product": str(summary.get("현재밀고있는상품") or ""),
        "competitor_name": competitor_name,
        "competitor_file": competitor_path.name if competitor_path else "",
        "competitor_source": competitor_source,
        "brand": {
            "faq_analysis": brand_faq_result,
            "review_collection": brand_review_result,
            "strengths": brand_pro_result,
            "weaknesses": brand_con_result,
        },
        "competitor": {
            "detail_page_analysis": competitor_detail_result,
            "faq_analysis": competitor_faq_result,
            "review_collection": competitor_review_result,
        },
        "source_counts": {
            "brand_faq_texts": len(brand_faq),
            "brand_review_texts": len(brand_reviews),
            "brand_strength_texts": len(brand_pros),
            "brand_weakness_texts": len(brand_cons),
            "competitor_detail_texts": len(competitor_detail),
            "competitor_faq_texts": len(competitor_faq),
            "competitor_review_texts": len(competitor_reviews),
        },
    }
    result["ppt_image_brief"] = build_ppt_image_brief(result)
    return result


def collect_external_field(doc: dict[str, Any], key: str, own_domain: str) -> list[str]:
    texts: list[str] = []
    if not own_domain:
        return texts
    for record in iter_tool_records(doc, "Firecrawl"):
        record_domain = domain(str(record.get("url") or ""))
        if not record_domain or record_domain == own_domain:
            continue
        texts.extend(flatten_text(record.get(key)))
    return dedupe_texts(texts)


def csv_row(result: dict[str, Any]) -> dict[str, str]:
    brand = result["brand"]
    competitor = result["competitor"]
    ppt_image = result.get("ppt_image_brief") or {}
    ppt = ppt_image.get("PPT 반영") or {}
    image = ppt_image.get("이미지 반영") or {}
    return {
        "브랜드명": result["brand_name"],
        "파일명": result["file_name"],
        "홈페이지": result["homepage"],
        "대표상품": result["representative_product"],
        "현재밀고있는상품": result["current_product"],
        "경쟁사": result["competitor_name"],
        "경쟁사파일": result["competitor_file"],
        "경쟁사자료": result["competitor_source"],
        "브랜드_FAQ_키워드": ", ".join(brand["faq_analysis"]["keywords"]),
        "브랜드_FAQ_핵심": join_points(brand["faq_analysis"]),
        "브랜드_후기_키워드": ", ".join(brand["review_collection"]["keywords"]),
        "브랜드_후기_핵심": join_points(brand["review_collection"]),
        "브랜드_장점": join_points(brand["strengths"]),
        "브랜드_단점": join_points(brand["weaknesses"]),
        "경쟁사_상세페이지_키워드": ", ".join(competitor["detail_page_analysis"]["keywords"]),
        "경쟁사_상세페이지_핵심": join_points(competitor["detail_page_analysis"]),
        "경쟁사_FAQ_핵심": join_points(competitor["faq_analysis"]),
        "경쟁사_후기_핵심": join_points(competitor["review_collection"]),
        "PPT_핵심메시지": " / ".join(ppt.get("핵심 메시지") or []),
        "PPT_추천슬라이드구성": " / ".join(ppt.get("추천 슬라이드 구성") or []),
        "이미지_대표키워드": ", ".join(image.get("대표 키워드") or []),
        "이미지_비주얼방향": " / ".join(image.get("비주얼 방향") or []),
        "이미지_카피배지": " / ".join(image.get("이미지 카피/배지") or []),
    }


def write_csv(path: Path, results: list[dict[str, Any]]) -> None:
    rows = [csv_row(result) for result in results]
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, results: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(results, handle, ensure_ascii=False, indent=2)


def md_list(items: list[str], empty: str = "수집 문장 부족") -> list[str]:
    if not items:
        return [f"- {empty}"]
    return [f"- {item}" for item in items]


def section_lines(section: dict[str, Any], empty: str = "수집 문장 부족") -> list[str]:
    topics = section.get("topics") or []
    sentences = [] if section.get("mode") in {"positive", "negative"} else section.get("sentences") or []
    lines: list[str] = []
    if topics:
        lines.append("- 핵심 정리:")
        lines.extend([f"  - {item}" for item in topics])
    if sentences:
        lines.append("- 대표 문장:")
        lines.extend([f"  - {item}" for item in sentences])
    if not lines:
        lines.append(f"- {empty}")
    return lines


def write_markdown(path: Path, results: list[dict[str, Any]]) -> None:
    lines = [
        "# 땀띠화장품 JSON FAQ/후기 정리",
        "",
        f"- 생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 브랜드 수: {len(results)}",
        "- 방식: API/로컬 LLM 없이 JSON 텍스트에서 키워드 빈도와 대표문장을 추출",
        "",
    ]

    for result in results:
        brand = result["brand"]
        competitor = result["competitor"]
        ppt_image = result.get("ppt_image_brief") or {}
        ppt = ppt_image.get("PPT 반영") or {}
        image = ppt_image.get("이미지 반영") or {}
        lines.extend(
            [
                f"## {result['brand_name']}",
                "",
                f"- 파일: `{result['file_name']}`",
                f"- 홈페이지: {result['homepage'] or '-'}",
                f"- 대표상품: {result['representative_product'] or '-'}",
                f"- 현재밀고있는상품: {result['current_product'] or '-'}",
                f"- 경쟁사: {result['competitor_name'] or '-'}",
                f"- 경쟁사 자료: {result['competitor_source']}"
                + (f" (`{result['competitor_file']}`)" if result["competitor_file"] else ""),
                "",
                "### 브랜드 FAQ 분석",
                f"- 키워드: {', '.join(brand['faq_analysis']['keywords']) or '-'}",
            ]
        )
        lines.extend(section_lines(brand["faq_analysis"]))
        lines.extend(["", "### 브랜드 후기 수집", f"- 키워드: {', '.join(brand['review_collection']['keywords']) or '-'}"])
        lines.extend(section_lines(brand["review_collection"]))
        lines.extend(["", "### 장점"])
        lines.extend(section_lines(brand["strengths"]))
        lines.extend(["", "### 단점"])
        lines.extend(section_lines(brand["weaknesses"]))
        lines.extend(
            [
                "",
                "### 경쟁사 상세페이지 분석",
                f"- 키워드: {', '.join(competitor['detail_page_analysis']['keywords']) or '-'}",
            ]
        )
        lines.extend(section_lines(competitor["detail_page_analysis"]))
        lines.extend(["", "### 경쟁사 FAQ 분석"])
        lines.extend(section_lines(competitor["faq_analysis"]))
        lines.extend(["", "### 경쟁사 후기 수집"])
        lines.extend(section_lines(competitor["review_collection"]))
        lines.extend(["", "### PPT 반영"])
        lines.extend(md_list(ppt.get("핵심 메시지") or []))
        lines.extend(["", "### 이미지 반영"])
        lines.extend(md_list(image.get("비주얼 방향") or image.get("이미지 카피/배지") or []))
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def result_items(section: dict[str, Any], allow_sentences: bool = True) -> list[str]:
    topics = section.get("topics") or []
    if topics:
        return list(topics)
    if allow_sentences:
        return list(section.get("sentences") or [])
    return []


def update_firecrawl_record(record: dict[str, Any], result: dict[str, Any]) -> None:
    brand = result["brand"]
    competitor = result["competitor"]
    updates = {
        "경쟁사 상세페이지 분석": result_items(competitor["detail_page_analysis"]),
        "경쟁사 FAQ 분석": result_items(competitor["faq_analysis"]),
        "경쟁사 후기 수집": result_items(competitor["review_collection"]),
        "FAQ 분석": result_items(brand["faq_analysis"]),
        "후기 수집": result_items(brand["review_collection"]),
    }

    ordered: dict[str, Any] = {}
    inserted_competitor_children = False
    for key, value in record.items():
        if key in {"경쟁사 FAQ 분석", "경쟁사 후기 수집"}:
            continue
        ordered[key] = updates.get(key, value)
        if key == "경쟁사 상세페이지 분석":
            ordered["경쟁사 FAQ 분석"] = updates["경쟁사 FAQ 분석"]
            ordered["경쟁사 후기 수집"] = updates["경쟁사 후기 수집"]
            inserted_competitor_children = True

    if not inserted_competitor_children:
        ordered["경쟁사 상세페이지 분석"] = updates["경쟁사 상세페이지 분석"]
        ordered["경쟁사 FAQ 분석"] = updates["경쟁사 FAQ 분석"]
        ordered["경쟁사 후기 수집"] = updates["경쟁사 후기 수집"]
    if "FAQ 분석" not in ordered:
        ordered["FAQ 분석"] = updates["FAQ 분석"]
    if "후기 수집" not in ordered:
        ordered["후기 수집"] = updates["후기 수집"]

    record.clear()
    record.update(ordered)


def update_scrapecraft_record(record: dict[str, Any], result: dict[str, Any]) -> None:
    brand = result["brand"]
    if "장점" in record:
        record["장점"] = result_items(brand["strengths"], allow_sentences=False)
    if "단점" in record:
        record["단점"] = result_items(brand["weaknesses"], allow_sentences=False)


def write_back_json(
    path: Path,
    result: dict[str, Any],
    update_analysis: bool = True,
    update_ppt_image: bool = True,
) -> bool:
    doc = load_json(path)
    original_semantic_guard = strip_unmanaged_fields(doc)
    tool_analysis = doc.get("tool_analysis")

    changed = False
    if update_analysis and isinstance(tool_analysis, dict):
        for record in as_list(tool_analysis.get("Firecrawl")):
            if isinstance(record, dict):
                before = json.dumps(record, ensure_ascii=False, sort_keys=True)
                update_firecrawl_record(record, result)
                after = json.dumps(record, ensure_ascii=False, sort_keys=True)
                changed = changed or before != after

        for record in as_list(tool_analysis.get("ScrapeCraft")):
            if isinstance(record, dict):
                before = json.dumps(record, ensure_ascii=False, sort_keys=True)
                update_scrapecraft_record(record, result)
                after = json.dumps(record, ensure_ascii=False, sort_keys=True)
                changed = changed or before != after

    if update_ppt_image:
        before = json.dumps(doc.get(PPT_IMAGE_KEY), ensure_ascii=False, sort_keys=True)
        doc[PPT_IMAGE_KEY] = result.get("ppt_image_brief") or {}
        after = json.dumps(doc.get(PPT_IMAGE_KEY), ensure_ascii=False, sort_keys=True)
        changed = changed or before != after

    if not changed:
        return False

    if strip_unmanaged_fields(doc) != original_semantic_guard:
        raise RuntimeError(f"Refusing to write unmanaged field changes: {path}")

    path.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return True


def strip_unmanaged_fields(value: Any) -> Any:
    managed_keys = {
        "FAQ 분석",
        "후기 수집",
        "장점",
        "단점",
        "경쟁사 상세페이지 분석",
        "경쟁사 FAQ 분석",
        "경쟁사 후기 수집",
        PPT_IMAGE_KEY,
    }
    if isinstance(value, dict):
        return {
            key: strip_unmanaged_fields(nested)
            for key, nested in value.items()
            if key not in managed_keys
        }
    if isinstance(value, list):
        return [strip_unmanaged_fields(item) for item in value]
    return value


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(input_dir.glob("*.json"))
    if args.only_file:
        wanted = {name.casefold() for name in args.only_file}
        files = [path for path in files if path.name.casefold() in wanted]
    if args.max_files > 0:
        files = files[: args.max_files]
    if not files:
        raise FileNotFoundError(f"No JSON files found: {input_dir}")

    brand_index = build_brand_index(sorted(input_dir.glob("*.json")))
    results: list[dict[str, Any]] = []
    for path in files:
        try:
            doc = load_json(path)
            results.append(
                summarize_one(
                    path=path,
                    doc=doc,
                    brand_index=brand_index,
                    top_sentences=args.top_sentences,
                    top_words=args.top_keywords,
                )
            )
        except Exception as exc:
            print(f"Skip {path.name}: {exc}")

    prefix = args.prefix or f"brand_faq_review_summary_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    csv_path = output_dir / f"{prefix}.csv"
    json_path = output_dir / f"{prefix}.json"
    md_path = output_dir / f"{prefix}.md"

    write_csv(csv_path, results)
    write_json(json_path, results)
    write_markdown(md_path, results)

    updated_files = 0
    if args.write_back_json or args.write_back_ppt_image:
        by_file = {result["file_name"]: result for result in results}
        for path in files:
            result = by_file.get(path.name)
            if result and write_back_json(
                path,
                result,
                update_analysis=args.write_back_json,
                update_ppt_image=args.write_back_json or args.write_back_ppt_image,
            ):
                updated_files += 1

    print(f"Input JSON files: {len(files)}")
    print(f"Saved brands: {len(results)}")
    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")
    if args.write_back_json or args.write_back_ppt_image:
        print(f"Updated source JSON files: {updated_files}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
