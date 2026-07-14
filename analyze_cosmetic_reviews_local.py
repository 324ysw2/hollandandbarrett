from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT_DIR = ROOT.parent / "땀띠화장품2"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "brand_json_summaries"
KNU_JSON = ROOT / "KnuSentiLex" / "data" / "SentiWord_info.json"
KR_WORDRANK_DIR = ROOT / "KR-WordRank"

if str(KR_WORDRANK_DIR) not in sys.path:
    sys.path.insert(0, str(KR_WORDRANK_DIR))

try:
    from kiwipiepy import Kiwi
except Exception:
    Kiwi = None  # type: ignore
else:
    if not callable(Kiwi):
        Kiwi = None  # type: ignore

try:
    from krwordrank.word import KRWordRank
except Exception:
    KRWordRank = None  # type: ignore


NOISE_TERMS = {
    "로그인",
    "회원가입",
    "장바구니",
    "마이페이지",
    "주문조회",
    "사업자정보",
    "사업자 등록번호",
    "통신판매업",
    "대표이사",
    "운영시간",
    "점심시간",
    "제휴문의",
    "제휴 문의",
    "고객센터 전화",
    "서울특별시",
    "이용약관",
    "개인정보처리방침",
    "개인정보",
    "수집 실패",
    "접속 불가",
    "DNS 오류",
    "렌더링 실패",
    "대체 수집 실패",
    "페이지 업체명 신호",
    "copyright",
    "all rights reserved",
    "hit enter",
    "esc to close",
    "skip to content",
    "privacy policy",
    "cookie policy",
    "@official",
    "인스타그램에 방문",
    "현재 위치",
    "상품보기",
    "뒤로가기",
    "상품비교",
    "낮은가격",
    "높은가격",
    "최근 본 상품",
    "전체상품목록 바로가기",
    "본문 바로가기",
    "상품요약정보",
    "할인판매가",
    "최적할인가",
}

NAV_TERMS = {
    "로그인",
    "회원가입",
    "장바구니",
    "마이페이지",
    "검색",
    "메뉴",
    "공지사항",
    "고객센터",
    "회사소개",
    "이벤트",
    "브랜드",
    "전체상품",
    "카테고리",
    "instagram",
    "facebook",
    "youtube",
}

CATALOG_TERMS = {
    "상품요약정보",
    "소비자가",
    "판매가",
    "할인판매가",
    "최적할인가",
    "상품명",
    "옵션",
    "재고",
    "품절",
    "장바구니",
    "바로구매",
    "x2개",
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
    "페이지",
    "정보",
    "검색",
    "공식",
    "온라인",
    "스토어",
    "전체",
    "바로가기",
    "본문",
    "고객센터",
    "회사소개",
    "이벤트",
    "판매가",
    "소비자가",
    "가격",
    "원",
    "more",
    "shop",
    "best",
    "new",
    "상품요약정보",
    "할인판매가",
    "최적할인가",
}

ASPECTS = {
    "보습/촉촉함": ["보습", "촉촉", "수분", "건조", "당김", "히알루론", "크림", "로션"],
    "진정/장벽": ["진정", "시카", "병풀", "판테놀", "세라마이드", "장벽", "민감", "저자극"],
    "트러블/자극": ["트러블", "여드름", "피지", "모공", "자극", "따가", "붉어", "가려"],
    "사용감": ["발림", "흡수", "산뜻", "끈적", "무겁", "마무리감", "제형", "부드"],
    "향": ["향", "냄새", "은은", "무향", "퍼퓸", "아로마"],
    "가격/혜택": ["할인", "쿠폰", "무료배송", "가성비", "비싸", "저렴", "혜택", "세트", "1+1"],
    "재구매/만족": ["만족", "좋", "좋아", "추천", "재구매", "또 살", "또살", "인생템"],
    "배송/CS": ["배송", "문의", "교환", "반품", "환불", "고객센터", "상담", "출고", "품절"],
}

GROUP_RULES = {
    "장벽/진정/민감 케어": ["진정", "시카", "병풀", "판테놀", "세라마이드", "장벽", "민감", "저자극", "아토", "홍조"],
    "보습/수분/리페어": ["보습", "수분", "촉촉", "히알루론", "알로에", "리페어", "크림", "로션", "건조"],
    "트러블/피지/모공": ["트러블", "여드름", "피지", "모공", "스팟", "티트리", "각질", "아크네"],
    "선케어/아웃도어": ["선크림", "선로션", "선케어", "자외선", "spf", "태닝", "애프터선", "썬", "sun"],
    "미백/잡티/톤업": ["미백", "기미", "잡티", "색소", "멜라닌", "비타민c", "톤업", "화이트닝", "브라이트닝"],
    "안티에이징/탄력/리프팅": ["탄력", "리프팅", "주름", "콜라겐", "레티놀", "펩타이드", "pdrn", "egf", "퍼밍"],
    "클렌징/바디/헤어": ["클렌징", "클렌저", "워시", "샴푸", "바디", "헤어", "트리트먼트", "스크럽", "비누", "세정"],
    "베이비/패밀리/임산부": ["베이비", "아기", "유아", "키즈", "임산부", "맘", "어린이", "신생아", "패밀리"],
    "여성청결/특수케어/의약외품": ["여성청결", "y존", "질", "의약외품", "상처", "제대혈", "의료", "소독", "약국"],
    "프리미엄/향/브랜드 라이프스타일": ["향수", "프래그런스", "퍼퓸", "럭셔리", "프리미엄", "에스테틱", "스파"],
}

POSITIVE_HINTS = {"좋", "만족", "추천", "재구매", "순하", "촉촉", "산뜻", "빠르", "가성비", "편하", "부드", "은은", "저자극", "진정"}
NEGATIVE_HINTS = {"아쉽", "별로", "자극", "트러블", "건조", "끈적", "비싸", "불편", "냄새", "느리", "따가", "붉어", "가려", "품절", "환불"}
NEGATION_PATTERNS = ["없", "않", "안 ", "없이", "아니", "끈적이지", "자극 없", "건조하지", "비싸지"]
PRICE_RE = re.compile(r"\d{1,3}(?:,\d{3})+원|\d{4,7}원")
REVIEW_COUNT_RE = re.compile(r"(?:리뷰|후기|사용후기|상품후기)\s*[\(:]?\s*(\d{1,6})")
RATING_RE = re.compile(r"(?:별점|평점|rating)\s*[:：]?\s*([0-5](?:\.\d)?)|([0-5]\.0)")
WORD_RE = re.compile(r"[가-힣A-Za-z0-9+]{2,}")
SENT_SPLIT_RE = re.compile(r"(?<=[.!?。！？])\s+|[\r\n]+|(?<=다)\s+(?=[가-힣A-Za-z0-9])|(?<=요)\s+(?=[가-힣A-Za-z0-9])")


@dataclass
class TextUnit:
    url: str
    section: str
    source: str
    text: str
    weight: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze cosmetic brand JSON locally without external APIs.")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--prefix", default="ttamtti2_local_review_analysis")
    parser.add_argument("--max-files", type=int, default=0)
    parser.add_argument("--brand", default="", help="Optional single brand/file stem for testing")
    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def norm_space(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").replace("\u00a0", " ")).strip()


def flatten_text(value: Any) -> list[str]:
    out: list[str] = []
    if value is None:
        return out
    if isinstance(value, str):
        text = norm_space(value)
        if text:
            out.append(text)
    elif isinstance(value, list):
        for item in value:
            out.extend(flatten_text(item))
    elif isinstance(value, dict):
        for item in value.values():
            out.extend(flatten_text(item))
    else:
        text = norm_space(value)
        if text:
            out.append(text)
    return out


def domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def extract_homepage(doc: dict[str, Any]) -> str:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    return str(doc.get("homepage") or summary.get("홈페이지 URL") or "")


def source_weight(url: str, homepage: str, source: str, status: str = "") -> float:
    if "수집 실패" in status or "대체 수집 실패" in status:
        return 0.05
    own = domain(homepage)
    got = domain(url)
    if source == "review_analysis":
        base = 1.25
    elif source == "tool_analysis":
        base = 0.75
    else:
        base = 0.5
    if not own or not got:
        return base * 0.75
    if own == got or got.endswith("." + own) or own.endswith("." + got):
        return base
    return base * 0.35


def collect_units(doc: dict[str, Any]) -> list[TextUnit]:
    homepage = extract_homepage(doc)
    units: list[TextUnit] = []

    review_analysis = doc.get("review_analysis") if isinstance(doc.get("review_analysis"), dict) else {}
    for item in review_analysis.get("items") or []:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "")
        status = str(item.get("status") or "")
        weight = source_weight(url, homepage, "review_analysis", status)
        for key, value in item.items():
            if key in {"url", "status"}:
                continue
            for text in flatten_text(value):
                units.append(TextUnit(url=url, section=str(key), source="review_analysis", text=text, weight=weight))

    tool_analysis = doc.get("tool_analysis") if isinstance(doc.get("tool_analysis"), dict) else {}
    for tool_name, records in tool_analysis.items():
        for record in records if isinstance(records, list) else []:
            if not isinstance(record, dict):
                continue
            url = str(record.get("url") or "")
            status = str(record.get("status") or "")
            weight = source_weight(url, homepage, "tool_analysis", status)
            for key in ["FAQ 분석", "후기 수집", "가격", "리뷰수", "별점", "장점", "단점", "랜딩페이지 분석", "경쟁사 상세페이지 분석"]:
                for text in flatten_text(record.get(key)):
                    units.append(TextUnit(url=url, section=key, source=f"tool_analysis:{tool_name}", text=text, weight=weight))
    return units


def is_mostly_irrelevant_language(text: str, brand_name: str) -> bool:
    if not text:
        return True
    korean = len(re.findall(r"[가-힣]", text))
    ascii_letters = len(re.findall(r"[A-Za-z]", text))
    if ascii_letters > 80 and korean < 8 and brand_name.casefold() not in text.casefold():
        return True
    return False


def is_noise_sentence(text: str, brand_name: str = "") -> bool:
    text = norm_space(text)
    if len(text) < 10:
        return True
    lowered = text.casefold()
    if any(term.casefold() in lowered for term in NOISE_TERMS):
        return True
    if is_mostly_irrelevant_language(text, brand_name):
        return True
    nav_count = sum(1 for term in NAV_TERMS if term.casefold() in lowered)
    catalog_count = sum(1 for term in CATALOG_TERMS if term.casefold() in lowered)
    price_count = len(PRICE_RE.findall(text))
    words = WORD_RE.findall(text)
    if nav_count >= 5:
        return True
    if catalog_count >= 3:
        return True
    if len(text) > 120 and price_count >= 3:
        return True
    if len(text) > 260 and (nav_count >= 2 or catalog_count >= 1):
        return True
    if len(text) > 420 and nav_count >= 3:
        return True
    if len(words) > 80 and len(set(words)) / max(len(words), 1) < 0.42:
        return True
    return False


def split_sentences(text: str) -> list[str]:
    text = norm_space(text)
    chunks = SENT_SPLIT_RE.split(text)
    if len(chunks) <= 1 and len(text) > 220:
        chunks = re.split(r"\s{2,}| / | \| |(?<=\))\s+", text)
    out = []
    for chunk in chunks:
        chunk = norm_space(chunk)
        if len(chunk) > 320:
            # Navigation-heavy crawls often arrive as one huge line. Cut into conservative windows.
            parts = re.split(r"(?<=원)\s+|(?<=MORE)\s+|(?=상품요약정보)|(?=소비자가)|(?=판매가)|(?<=니다)\s+", chunk)
            out.extend(norm_space(part)[:320] for part in parts if norm_space(part))
        elif chunk:
            out.append(chunk)
    return out


def tokenize(text: str, kiwi: Any | None) -> list[str]:
    if kiwi is not None:
        try:
            toks = []
            for token in kiwi.tokenize(text):
                if token.tag.startswith(("N", "V", "VA", "XR", "SL")):
                    form = token.form.strip()
                    if len(form) >= 2 and form.casefold() not in STOPWORDS:
                        toks.append(form)
            if toks:
                return toks
        except Exception:
            pass
    return [
        w
        for w in WORD_RE.findall(text)
        if len(w) >= 2
        and w.casefold() not in STOPWORDS
        and not w.isdigit()
        and not PRICE_RE.fullmatch(w)
        and not re.fullmatch(r"\d+(?:ml|g|개|매|종|호|%|원)?", w, flags=re.I)
    ]


def load_sentiment_lexicon() -> dict[str, int]:
    lex: dict[str, int] = {}
    if not KNU_JSON.exists():
        return lex
    try:
        data = json.loads(KNU_JSON.read_text(encoding="utf-8"))
        for row in data:
            word = norm_space(row.get("word"))
            polarity = int(row.get("polarity") or 0)
            if word and polarity:
                # Prefer longer forms where duplicated roots exist.
                lex[word] = polarity
    except Exception:
        return {}
    return lex


def has_negation(text: str) -> bool:
    return any(pattern in text for pattern in NEGATION_PATTERNS)


def sentiment_score(text: str, lexicon: dict[str, int]) -> tuple[float, list[str], list[str]]:
    score = 0.0
    pos_hits: list[str] = []
    neg_hits: list[str] = []
    lowered = text.casefold()

    for word, polarity in lexicon.items():
        if len(word) < 2 or len(word) > 12:
            continue
        if word in text:
            score += polarity * 0.45
            if polarity > 0:
                pos_hits.append(word)
            elif polarity < 0:
                neg_hits.append(word)
            if len(pos_hits) + len(neg_hits) > 12:
                break

    for word in POSITIVE_HINTS:
        if word.casefold() in lowered:
            score += 1.0
            pos_hits.append(word)
    for word in NEGATIVE_HINTS:
        if word.casefold() in lowered:
            if has_negation(text):
                score += 0.6
                pos_hits.append(f"{word}+부정어반전")
            else:
                score -= 1.0
                neg_hits.append(word)
    return score, list(dict.fromkeys(pos_hits))[:8], list(dict.fromkeys(neg_hits))[:8]


def aspect_labels(text: str) -> dict[str, list[str]]:
    labels: dict[str, list[str]] = {}
    lowered = text.casefold()
    for aspect, words in ASPECTS.items():
        hits = [word for word in words if word.casefold() in lowered]
        if hits:
            labels[aspect] = hits
    return labels


def sentiment_bucket(score: float) -> str:
    if score > 0.8:
        return "긍정"
    if score < -0.8:
        return "부정"
    return "중립"


def aspect_sentiment_profile(sentence_rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    examples: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for row in sentence_rows:
        bucket = sentiment_bucket(float(row["sentiment_score"]))
        weight = float(row["weight"])
        for aspect in row["aspects"]:
            counts[aspect][bucket] += weight
            if len(examples[aspect][bucket]) < 2:
                examples[aspect][bucket].append(row["sentence"])

    rows: list[dict[str, Any]] = []
    for aspect, counter in counts.items():
        pos = float(counter["긍정"])
        neg = float(counter["부정"])
        neu = float(counter["중립"])
        total = pos + neg + neu
        if total <= 0:
            continue
        pos_pct = round(pos / total * 100)
        neg_pct = round(neg / total * 100)
        neu_pct = max(0, 100 - pos_pct - neg_pct)
        rows.append(
            {
                "aspect": aspect,
                "positive": round(pos, 2),
                "negative": round(neg, 2),
                "neutral": round(neu, 2),
                "total": round(total, 2),
                "positive_pct": pos_pct,
                "negative_pct": neg_pct,
                "neutral_pct": neu_pct,
                "positive_examples": examples[aspect]["긍정"],
                "negative_examples": examples[aspect]["부정"],
            }
        )

    rows.sort(key=lambda item: (item["total"], item["positive_pct"] - item["negative_pct"]), reverse=True)
    main_appeals = [r for r in rows if r["positive_pct"] >= 55 and r["total"] >= 1]
    caution_aspects = [r for r in rows if r["negative_pct"] >= 25 and r["total"] >= 1]
    mixed_aspects = [r for r in rows if r["positive_pct"] >= 35 and r["negative_pct"] >= 15 and r["total"] >= 1]
    return {
        "rows": rows,
        "main_appeals": main_appeals[:3],
        "caution_aspects": caution_aspects[:3],
        "mixed_aspects": mixed_aspects[:3],
    }


def format_aspect_sentiment(rows: list[dict[str, Any]], limit: int = 6) -> str:
    return " / ".join(
        f"{r['aspect']}:긍정{r['positive_pct']}%,부정{r['negative_pct']}%,중립{r['neutral_pct']}%"
        for r in rows[:limit]
    )


def format_aspect_names(rows: list[dict[str, Any]], limit: int = 3) -> str:
    return " / ".join(f"{r['aspect']}({r['positive_pct']}%+/{r['negative_pct']}%-)" for r in rows[:limit])


def build_absc_basis(profile: dict[str, Any]) -> str:
    main = format_aspect_names(profile["main_appeals"], 2) or "메인 소구 항목 추가 확인"
    caution = format_aspect_names(profile["caution_aspects"], 2) or "뚜렷한 부정 항목 낮음"
    mixed = format_aspect_names(profile["mixed_aspects"], 1) or "호불호 항목 낮음"
    return f"메인 소구는 {main}, 보완 항목은 {caution}, 서브 메시지 검토 항목은 {mixed}입니다."


def compact_key(text: str) -> str:
    return re.sub(r"\W+", "", text).casefold()[:160]


def prepare_sentences(units: list[TextUnit], brand_name: str, kiwi: Any | None, lexicon: dict[str, int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for unit in units:
        for sentence in split_sentences(unit.text):
            sentence = re.sub(r"\bMORE\b\s*", "", sentence, flags=re.I)
            if is_noise_sentence(sentence, brand_name):
                continue
            key = compact_key(sentence)
            if key in seen:
                continue
            seen.add(key)
            toks = tokenize(sentence, kiwi)
            sent_score, pos_hits, neg_hits = sentiment_score(sentence, lexicon)
            labels = aspect_labels(sentence)
            prices = PRICE_RE.findall(sentence)
            review_counts = REVIEW_COUNT_RE.findall(sentence)
            ratings = [m[0] or m[1] for m in RATING_RE.findall(sentence)]
            rows.append(
                {
                    "sentence": sentence,
                    "section": unit.section,
                    "url": unit.url,
                    "source": unit.source,
                    "weight": unit.weight,
                    "tokens": toks,
                    "sentiment_score": sent_score,
                    "positive_hits": pos_hits,
                    "negative_hits": neg_hits,
                    "aspects": labels,
                    "prices": prices,
                    "review_counts": review_counts,
                    "ratings": ratings,
                }
            )
    return rows


def try_krwordrank(sentences: list[str]) -> list[str]:
    if KRWordRank is None or len(sentences) < 5:
        return []
    try:
        extractor = KRWordRank(min_count=2, max_length=10, verbose=False)
        keywords, _, _ = extractor.extract(sentences, beta=0.85, max_iter=10, num_keywords=30)
        return [word for word, _ in sorted(keywords.items(), key=lambda item: -item[1])[:20] if word.casefold() not in STOPWORDS]
    except Exception:
        return []


def keyword_counts(sentence_rows: list[dict[str, Any]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for row in sentence_rows:
        weight = float(row["weight"])
        for token in row["tokens"]:
            if token.casefold() not in STOPWORDS:
                counter[token] += weight
    return counter


def select_representatives(sentence_rows: list[dict[str, Any]], top_keywords: list[str], limit: int = 5) -> list[str]:
    keyword_set = set(top_keywords[:20])
    scored = []
    for row in sentence_rows:
        sent = row["sentence"]
        if len(sent) < 18 or len(sent) > 240:
            continue
        if is_noise_sentence(sent):
            continue
        length_penalty = 0.8 if len(sent) > 190 else 0
        kw_score = sum(1.5 for token in row["tokens"] if token in keyword_set)
        aspect_score = len(row["aspects"]) * 1.2
        section_score = 1.0 if row["section"] in {"후기 수집", "장점", "단점", "FAQ 분석"} else 0
        evidence_score = 0.8 if row["review_counts"] or row["ratings"] else 0
        sentiment_strength = min(abs(float(row["sentiment_score"])), 3) * 0.4
        score = kw_score + aspect_score + section_score + evidence_score + sentiment_strength + float(row["weight"]) - length_penalty
        scored.append((score, sent))
    scored.sort(key=lambda item: item[0], reverse=True)
    selected: list[str] = []
    seen_tokens: list[set[str]] = []
    for _, sent in scored:
        toks = set(WORD_RE.findall(sent))
        compact_sent = compact_key(sent)
        if any(compact_sent in compact_key(prev) or compact_key(prev) in compact_sent for prev in selected):
            continue
        if any(len(toks & prev) / max(len(toks | prev), 1) > 0.72 for prev in seen_tokens):
            continue
        selected.append(sent)
        seen_tokens.append(toks)
        if len(selected) >= limit:
            break
    return selected


def classify_group(all_text: str, aspects: Counter[str]) -> tuple[str, list[str]]:
    lowered = all_text.casefold()
    ranked = []
    for group, words in GROUP_RULES.items():
        hits = [word for word in words if word.casefold() in lowered]
        # Aspect counter adds more trust than stray crawled words.
        aspect_bonus = 0
        if group == "장벽/진정/민감 케어":
            aspect_bonus += aspects.get("진정/장벽", 0)
        if group == "보습/수분/리페어":
            aspect_bonus += aspects.get("보습/촉촉함", 0)
        if group == "트러블/피지/모공":
            aspect_bonus += aspects.get("트러블/자극", 0)
        if group == "클렌징/바디/헤어":
            aspect_bonus += aspects.get("사용감", 0) * 0.2
        ranked.append((len(hits) + aspect_bonus * 0.4, group, hits))
    ranked.sort(key=lambda item: item[0], reverse=True)
    if not ranked or ranked[0][0] <= 0:
        return "검토필요/상품군 불명확", []
    return ranked[0][1], ranked[0][2][:8]


def subtype(aspects: Counter[str], pos_count: int, neg_count: int, faq_count: int, prices: list[str]) -> str:
    if faq_count >= max(2, pos_count + neg_count):
        return "FAQ/CS 보완형"
    if prices and aspects.get("가격/혜택", 0) >= 1:
        return "가격/혜택형"
    if pos_count >= neg_count * 2 and pos_count >= 2:
        return "후기 강점형"
    if neg_count >= 2:
        return "단점/주의 보완형"
    if aspects.get("사용감", 0) >= 2:
        return "사용감 증명형"
    if aspects.get("진정/장벽", 0) + aspects.get("보습/촉촉함", 0) >= 2:
        return "성분/효능 설득형"
    return "기본 제안형"


def recommend_products(group: str, sub: str, evidence_grade: str, aspects: Counter[str]) -> list[str]:
    recs: list[str] = []
    if sub in {"후기 강점형", "사용감 증명형"}:
        recs.append("체험단/숏폼 리뷰 콘텐츠")
    if sub in {"FAQ/CS 보완형", "단점/주의 보완형"} or evidence_grade in {"A", "B"}:
        recs.append("리뷰/FAQ 기반 상세페이지 개선")
    if group != "검토필요/상품군 불명확":
        recs.append("네이버 검색광고/쇼핑 키워드 패키지")
    if sub == "가격/혜택형":
        recs.append("혜택/재구매 CRM 소재")
    if group in {"트러블/피지/모공", "여성청결/특수케어/의약외품"} or sub == "단점/주의 보완형":
        recs.append("화장품 표현 리스크 검수")
    recs.append("제안메일용 PPT/이미지 카드 제작")
    return list(dict.fromkeys(recs))[:3]


def evidence_grade(total: int, clean_count: int, positive: int, negative: int, faq: int, own_ratio: float) -> str:
    if clean_count >= 10 and (positive + negative + faq) >= 5 and own_ratio >= 0.45:
        return "A"
    if clean_count >= 5 and (positive + negative + faq) >= 2:
        return "B"
    if clean_count >= 2:
        return "C"
    return "D"


def analyze_one(path: Path, kiwi: Any | None, lexicon: dict[str, int]) -> dict[str, Any]:
    doc = load_json(path)
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    brand_name = str(doc.get("brand_name") or summary.get("업체") or path.stem)
    homepage = extract_homepage(doc)
    units = collect_units(doc)
    sentence_rows = prepare_sentences(units, brand_name, kiwi, lexicon)
    clean_count = len(sentence_rows)

    aspects_counter: Counter[str] = Counter()
    pos_counter: Counter[str] = Counter()
    neg_counter: Counter[str] = Counter()
    prices: list[str] = []
    review_counts: list[str] = []
    ratings: list[str] = []
    for row in sentence_rows:
        for aspect in row["aspects"]:
            aspects_counter[aspect] += row["weight"]
        pos_counter.update(row["positive_hits"])
        neg_counter.update(row["negative_hits"])
        prices.extend(row["prices"])
        review_counts.extend(row["review_counts"])
        ratings.extend(row["ratings"])

    positive_rows = [r for r in sentence_rows if r["sentiment_score"] > 0.8]
    negative_rows = [r for r in sentence_rows if r["sentiment_score"] < -0.8]
    faq_rows = [r for r in sentence_rows if r["section"] == "FAQ 분석" or "배송/CS" in r["aspects"]]

    own_weight = sum(float(r["weight"]) for r in sentence_rows if float(r["weight"]) >= 0.75)
    total_weight = sum(float(r["weight"]) for r in sentence_rows) or 1
    own_ratio = own_weight / total_weight

    kw_counter = keyword_counts(sentence_rows)
    all_sentences = [row["sentence"] for row in sentence_rows]
    kr_keywords = try_krwordrank(all_sentences)
    fallback_keywords = [word for word, _ in kw_counter.most_common(30)]
    top_keywords = list(dict.fromkeys(kr_keywords + fallback_keywords))[:20]
    reps = select_representatives(sentence_rows, top_keywords, 5)

    all_text = " ".join([brand_name, str(summary.get("대표상품") or ""), str(summary.get("현재밀고있는상품") or ""), " ".join(top_keywords), " ".join(all_sentences[:80])])
    group, group_hits = classify_group(all_text, aspects_counter)
    sub = subtype(aspects_counter, len(positive_rows), len(negative_rows), len(faq_rows), prices)
    grade = evidence_grade(len(units), clean_count, len(positive_rows), len(negative_rows), len(faq_rows), own_ratio)
    recs = recommend_products(group, sub, grade, aspects_counter)
    aspect_profile = aspect_sentiment_profile(sentence_rows)

    caution = []
    if grade in {"C", "D"}:
        caution.append("수집 근거가 약해 발송 전 대표상품/URL 확인 필요")
    if own_ratio < 0.35:
        caution.append("홈페이지 외부 도메인 텍스트 비중이 높음")
    if not reps:
        caution.append("대표 문장 부족")
    if group == "검토필요/상품군 불명확":
        caution.append("상품군 자동 판정 불명확")

    return {
        "brand_name": brand_name,
        "file_name": path.name,
        "homepage": homepage,
        "representative_product": str(summary.get("대표상품") or ""),
        "current_product": str(summary.get("현재밀고있는상품") or ""),
        "raw_text_units": len(units),
        "clean_sentences": clean_count,
        "own_domain_weight_ratio": round(own_ratio, 3),
        "evidence_grade": grade,
        "main_group": group,
        "group_hits": group_hits,
        "subtype": sub,
        "top_keywords": top_keywords[:12],
        "aspect_counts": {k: round(v, 2) for k, v in aspects_counter.most_common()},
        "aspect_sentiment": aspect_profile["rows"],
        "main_appeal_aspects": aspect_profile["main_appeals"],
        "caution_aspects": aspect_profile["caution_aspects"],
        "mixed_aspects": aspect_profile["mixed_aspects"],
        "absc_basis": build_absc_basis(aspect_profile),
        "positive_keywords": [k for k, _ in pos_counter.most_common(10)],
        "negative_keywords": [k for k, _ in neg_counter.most_common(10)],
        "positive_sentence_count": len(positive_rows),
        "negative_sentence_count": len(negative_rows),
        "faq_sentence_count": len(faq_rows),
        "prices": list(dict.fromkeys(prices))[:10],
        "review_counts": list(dict.fromkeys(review_counts))[:10],
        "ratings": list(dict.fromkeys(ratings))[:10],
        "representative_sentences": reps,
        "positive_examples": select_representatives(positive_rows, top_keywords, 3),
        "negative_examples": select_representatives(negative_rows, top_keywords, 3),
        "faq_examples": select_representatives(faq_rows, top_keywords, 3),
        "recommended_sales_products": recs,
        "proposal_brief": build_proposal_brief(brand_name, group, sub, top_keywords, recs, grade),
        "caution_flags": caution,
    }


def build_proposal_brief(brand: str, group: str, sub: str, keywords: list[str], recs: list[str], grade: str) -> str:
    kw = ", ".join(keywords[:4]) if keywords else "핵심 키워드 확인 필요"
    first = recs[0] if recs else "제안메일용 PPT/이미지 카드 제작"
    return f"{brand}은(는) {group} 중 {sub}으로 분류됩니다. 핵심 근거는 {kw}이며, 근거등급 {grade} 기준으로 {first} 중심 제안을 권장합니다."


def csv_row(result: dict[str, Any]) -> dict[str, str]:
    return {
        "브랜드명": result["brand_name"],
        "파일명": result["file_name"],
        "홈페이지": result["homepage"],
        "대표상품": result["representative_product"],
        "현재밀고있는상품": result["current_product"],
        "원본문구수": str(result["raw_text_units"]),
        "정제문장수": str(result["clean_sentences"]),
        "자사도메인가중비율": str(result["own_domain_weight_ratio"]),
        "근거등급": result["evidence_grade"],
        "대표그룹": result["main_group"],
        "그룹근거키워드": ", ".join(result["group_hits"]),
        "세부유형": result["subtype"],
        "상위키워드": ", ".join(result["top_keywords"]),
        "기능라벨분포": " / ".join(f"{k}:{v}" for k, v in result["aspect_counts"].items()),
        "항목별감성분포": format_aspect_sentiment(result["aspect_sentiment"]),
        "메인소구항목": format_aspect_names(result["main_appeal_aspects"]),
        "주의항목": format_aspect_names(result["caution_aspects"]),
        "호불호항목": format_aspect_names(result["mixed_aspects"]),
        "ABSC제안근거": result["absc_basis"],
        "긍정키워드": ", ".join(result["positive_keywords"]),
        "부정주의키워드": ", ".join(result["negative_keywords"]),
        "긍정문장수": str(result["positive_sentence_count"]),
        "부정문장수": str(result["negative_sentence_count"]),
        "FAQ문장수": str(result["faq_sentence_count"]),
        "가격신호": ", ".join(result["prices"]),
        "리뷰수신호": ", ".join(result["review_counts"]),
        "별점신호": ", ".join(result["ratings"]),
        "대표문장": " / ".join(result["representative_sentences"]),
        "긍정예시": " / ".join(result["positive_examples"]),
        "부정예시": " / ".join(result["negative_examples"]),
        "FAQ예시": " / ".join(result["faq_examples"]),
        "추천영업상품": " / ".join(result["recommended_sales_products"]),
        "제안브리프": result["proposal_brief"],
        "주의플래그": " / ".join(result["caution_flags"]),
    }


def write_outputs(results: list[dict[str, Any]], out_dir: Path, prefix: str) -> tuple[Path, Path, Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"{prefix}.csv"
    json_path = out_dir / f"{prefix}.json"
    md_path = out_dir / f"{prefix}.md"
    summary_path = out_dir / f"{prefix}_summary.json"

    rows = [csv_row(r) for r in results]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "brand_count": len(results),
        "evidence_grade_counts": dict(Counter(r["evidence_grade"] for r in results).most_common()),
        "group_counts": dict(Counter(r["main_group"] for r in results).most_common()),
        "subtype_counts": dict(Counter(r["subtype"] for r in results).most_common()),
        "recommended_sales_product_counts": dict(Counter(p for r in results for p in r["recommended_sales_products"]).most_common()),
        "caution_counts": dict(Counter(flag for r in results for flag in r["caution_flags"]).most_common()),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# 로컬 리뷰 분석 결과",
        "",
        f"- 생성일: {summary['generated_at']}",
        f"- 브랜드 수: {summary['brand_count']}",
        "- 방식: API 없이 JSON 텍스트 정제, KNU 감성사전, Kiwi 토큰화, KR-WordRank/TF 키워드, 규칙 기반 라벨링",
        "",
        "## 근거등급",
        "",
        "| 등급 | 브랜드 수 |",
        "|---|---:|",
    ]
    for grade, count in summary["evidence_grade_counts"].items():
        lines.append(f"| {grade} | {count} |")
    lines.extend(["", "## 그룹 분포", "", "| 그룹 | 브랜드 수 |", "|---|---:|"])
    for group, count in summary["group_counts"].items():
        lines.append(f"| {group} | {count} |")
    lines.extend(["", "## 추천 영업상품 분포", "", "| 상품 | 브랜드 수 |", "|---|---:|"])
    for product, count in summary["recommended_sales_product_counts"].items():
        lines.append(f"| {product} | {count} |")
    lines.extend(["", "## 브랜드 샘플", ""])
    for r in results[:60]:
        lines.extend(
            [
                f"### {r['brand_name']}",
                f"- 등급/그룹: {r['evidence_grade']} / {r['main_group']} / {r['subtype']}",
                f"- 키워드: {', '.join(r['top_keywords'][:8]) or '-'}",
                f"- 추천: {' / '.join(r['recommended_sales_products'])}",
                f"- 브리프: {r['proposal_brief']}",
                f"- 대표문장: {' / '.join(r['representative_sentences'][:2]) or '-'}",
                f"- 주의: {' / '.join(r['caution_flags']) or '-'}",
                "",
            ]
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return csv_path, json_path, md_path, summary_path


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input_dir).expanduser().resolve()
    out_dir = Path(args.output_dir).expanduser().resolve()
    files = sorted(input_dir.glob("*.json"), key=lambda p: p.stem.casefold())
    if args.brand:
        wanted = args.brand.casefold().replace(".json", "")
        files = [p for p in files if p.stem.casefold() == wanted or p.name.casefold() == args.brand.casefold()]
    if args.max_files > 0:
        files = files[: args.max_files]
    if not files:
        raise FileNotFoundError(input_dir)

    kiwi = Kiwi() if Kiwi is not None else None
    lexicon = load_sentiment_lexicon()
    results = []
    for idx, path in enumerate(files, start=1):
        try:
            results.append(analyze_one(path, kiwi, lexicon))
        except Exception as exc:
            print(f"skip {path.name}: {exc}")

    csv_path, json_path, md_path, summary_path = write_outputs(results, out_dir, args.prefix)
    print(f"input_files={len(files)}")
    print(f"saved_brands={len(results)}")
    print(f"csv={csv_path}")
    print(f"json={json_path}")
    print(f"markdown={md_path}")
    print(f"summary={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
