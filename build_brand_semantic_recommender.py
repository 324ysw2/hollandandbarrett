from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "brand_json_summaries"
DEFAULT_INPUT = DATA_DIR / "ttamtti2_local_review_analysis.csv"
DEFAULT_PREFIX = "ttamtti2_semantic_brand_recommendations"

WORD_RE = re.compile(r"[가-힣A-Za-z0-9+.#%]{2,}")
KOREAN_RE = re.compile(r"[가-힣]{2,}")

STOPWORDS = {
    "네이버",
    "페이",
    "구매평",
    "등록된",
    "리뷰",
    "후기",
    "상품",
    "제품",
    "사용",
    "브랜드",
    "공식",
    "상세",
    "페이지",
    "가격",
    "할인",
    "배송",
    "문의",
    "이벤트",
    "로그인",
    "회원가입",
    "장바구니",
    "SHIPPING",
    "TO",
    "USD",
    "KRW",
    "JPY",
    "LV",
    "ABOUT",
    "REVIEW",
    "LOGIN",
    "CART",
}

NOISY_HINTS = {
    "SHIPPING TO",
    "WORLD SHIPPING",
    "회사소개",
    "이용약관",
    "개인정보",
    "대표이사",
    "서울특별시",
    "닫기 닫기",
    "사이트 작동 방식",
}

GROUP_WEIGHT = 0.12
SUBTYPE_WEIGHT = 0.05
CAUTION_PENALTY = 0.12


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def split_list(value: str) -> list[str]:
    if not value:
        return []
    parts: list[str] = []
    for chunk in re.split(r"\s*/\s*|,\s*", value):
        chunk = " ".join(chunk.strip().split())
        if chunk:
            parts.append(chunk)
    return parts


def split_sales_products(value: str) -> list[str]:
    if not value:
        return []
    return [" ".join(part.strip().split()) for part in value.split(" / ") if part.strip()]


def clean_text(text: str) -> str:
    text = text or ""
    text = re.sub(r"\([^)]*등록된 네이버 페이 구매평\)", " ", text)
    text = re.sub(r"\d{4}[-.]\d{1,2}[-.]\d{1,2}(?:\s+\d{1,2}:\d{2}:\d{2})?", " ", text)
    text = re.sub(r"[A-Za-z가-힣]\*{2,}", " ", text)
    text = re.sub(r"\b\d{1,3}(?:,\d{3})*원\b", " ", text)
    text = re.sub(r"\b\d+(?:ml|g|개|종|호)\b", " ", text, flags=re.I)
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    return " ".join(text.split())


def is_noisy(row: dict[str, str]) -> bool:
    flags = row.get("주의플래그", "")
    text = " ".join([row.get("대표문장", ""), row.get("상위키워드", ""), row.get("FAQ예시", "")])
    upper = text.upper()
    if "상품군 자동 판정 불명확" in flags:
        return True
    return any(hint.upper() in upper for hint in NOISY_HINTS)


def build_brand_document(row: dict[str, str]) -> str:
    weighted_parts: list[str] = []

    def add(value: str, repeat: int = 1) -> None:
        value = clean_text(value)
        if value:
            weighted_parts.extend([value] * repeat)

    add(row.get("브랜드명", ""), 5)
    add(row.get("대표상품", ""), 3)
    add(row.get("현재밀고있는상품", ""), 3)
    add(row.get("대표그룹", ""), 4)
    add(row.get("세부유형", ""), 3)
    add(row.get("그룹근거키워드", ""), 4)
    add(row.get("상위키워드", ""), 4)
    add(row.get("기능라벨분포", ""), 3)
    add(row.get("긍정키워드", ""), 3)
    add(row.get("부정주의키워드", ""), 2)
    add(row.get("대표문장", ""), 2)
    add(row.get("긍정예시", ""), 2)
    add(row.get("부정예시", ""), 2)
    add(row.get("FAQ예시", ""), 1)
    add(row.get("추천영업상품", ""), 3)
    return " ".join(weighted_parts)


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for word in WORD_RE.findall(text):
        if word in STOPWORDS or word.upper() in STOPWORDS:
            continue
        if word.isdigit():
            continue
        tokens.append(word.casefold())

    # Korean character n-grams work well enough without installing a tokenizer.
    for chunk in KOREAN_RE.findall(text):
        if len(chunk) < 3:
            continue
        for n in (2, 3, 4):
            if len(chunk) >= n:
                tokens.extend(chunk[i : i + n] for i in range(len(chunk) - n + 1))
    return tokens


def build_tfidf(docs: list[str], max_features: int = 12000) -> tuple[list[dict[int, float]], list[str]]:
    term_counts = [Counter(tokenize(doc)) for doc in docs]
    df: Counter[str] = Counter()
    for counter in term_counts:
        df.update(counter.keys())

    usable = [(term, freq) for term, freq in df.items() if 2 <= freq <= max(3, int(len(docs) * 0.72))]
    usable.sort(key=lambda item: (item[1], len(item[0])), reverse=True)
    vocab_terms = [term for term, _ in usable[:max_features]]
    vocab = {term: idx for idx, term in enumerate(vocab_terms)}
    idf = {
        term: math.log((1 + len(docs)) / (1 + df[term])) + 1.0
        for term in vocab_terms
    }

    vectors: list[dict[int, float]] = []
    for counter in term_counts:
        vec: dict[int, float] = {}
        total = sum(counter.values()) or 1
        for term, count in counter.items():
            idx = vocab.get(term)
            if idx is None:
                continue
            vec[idx] = (count / total) * idf[term]
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        vectors.append({idx: value / norm for idx, value in vec.items()})
    return vectors, vocab_terms


def cosine_sparse(a: dict[int, float], b: dict[int, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(value * b.get(idx, 0.0) for idx, value in a.items())


def evidence_multiplier(row: dict[str, str]) -> float:
    grade = row.get("근거등급", "D")
    grade_weight = {"A": 1.0, "B": 0.92, "C": 0.82, "D": 0.68}.get(grade, 0.75)
    if is_noisy(row):
        grade_weight -= CAUTION_PENALTY
    try:
        clean_count = int(float(row.get("정제문장수", "0") or 0))
    except ValueError:
        clean_count = 0
    count_bonus = min(clean_count / 100, 0.12)
    return max(0.45, min(1.08, grade_weight + count_bonus))


def blended_similarity(row_a: dict[str, str], row_b: dict[str, str], cosine: float) -> float:
    score = cosine
    if row_a.get("대표그룹") and row_a.get("대표그룹") == row_b.get("대표그룹"):
        score += GROUP_WEIGHT
    if row_a.get("세부유형") and row_a.get("세부유형") == row_b.get("세부유형"):
        score += SUBTYPE_WEIGHT
    score *= evidence_multiplier(row_b)
    a_noisy = is_noisy(row_a)
    b_noisy = is_noisy(row_b)
    if b_noisy and not a_noisy:
        score *= 0.35
    elif b_noisy and a_noisy:
        score *= 0.55
    return max(0.0, min(score, 1.0))


def recommended_from_neighbors(target: dict[str, str], neighbors: list[dict[str, Any]]) -> list[str]:
    votes: defaultdict[str, float] = defaultdict(float)
    for product in split_sales_products(target.get("추천영업상품", "")):
        votes[product] += 0.55
    for item in neighbors:
        score = float(item["score"])
        for product in split_sales_products(item["recommended_sales_products"]):
            votes[product] += score
    ordered = sorted(votes.items(), key=lambda item: item[1], reverse=True)
    return [name for name, _ in ordered[:4]]


def top_keywords_from_neighbors(target: dict[str, str], neighbors: list[dict[str, Any]]) -> list[str]:
    counter: Counter[str] = Counter()
    for field in ["그룹근거키워드", "상위키워드", "긍정키워드", "부정주의키워드"]:
        for word in split_list(target.get(field, "")):
            if word not in STOPWORDS and word.upper() not in STOPWORDS and len(word) >= 2:
                counter[word] += 3
    for item in neighbors:
        weight = max(1, int(float(item["score"]) * 10))
        for word in split_list(item.get("keywords", "")):
            if word not in STOPWORDS and word.upper() not in STOPWORDS and len(word) >= 2:
                counter[word] += weight
    return [word for word, _ in counter.most_common(10)]


def recommendation_reason(target: dict[str, str], neighbors: list[dict[str, Any]], products: list[str]) -> str:
    neighbor_names = ", ".join(n["brand_name"] for n in neighbors[:3])
    kw = ", ".join(top_keywords_from_neighbors(target, neighbors)[:5])
    return (
        f"{target['브랜드명']}은(는) {target.get('대표그룹','')} / {target.get('세부유형','')} 신호가 있고, "
        f"의미상 가까운 브랜드({neighbor_names})와 {kw} 키워드를 공유합니다. "
        f"따라서 {' + '.join(products[:2])} 중심 제안이 우선입니다."
    )


def build_outputs(rows: list[dict[str, str]], vectors: list[dict[int, float]], top_k: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        scored = []
        for j, other in enumerate(rows):
            if i == j:
                continue
            cos = cosine_sparse(vectors[i], vectors[j])
            score = blended_similarity(row, other, cos)
            if score <= 0:
                continue
            scored.append((score, cos, other))
        scored.sort(key=lambda item: item[0], reverse=True)
        neighbors = [
            {
                "brand_name": other["브랜드명"],
                "score": round(score, 4),
                "semantic_cosine": round(cos, 4),
                "main_group": other.get("대표그룹", ""),
                "subtype": other.get("세부유형", ""),
                "evidence_grade": other.get("근거등급", ""),
                "keywords": other.get("상위키워드", ""),
                "recommended_sales_products": other.get("추천영업상품", ""),
            }
            for score, cos, other in scored[:top_k]
        ]
        products = recommended_from_neighbors(row, neighbors)
        out.append(
            {
                "brand_name": row["브랜드명"],
                "file_name": row.get("파일명", ""),
                "main_group": row.get("대표그룹", ""),
                "subtype": row.get("세부유형", ""),
                "evidence_grade": row.get("근거등급", ""),
                "clean_sentence_count": row.get("정제문장수", ""),
                "original_sales_products": split_sales_products(row.get("추천영업상품", "")),
                "semantic_sales_products": products,
                "shared_keywords": top_keywords_from_neighbors(row, neighbors),
                "nearest_brands": neighbors,
                "reason": recommendation_reason(row, neighbors, products),
                "caution_flags": row.get("주의플래그", ""),
                "noisy_input": is_noisy(row),
            }
        )
    return out


def write_csv(path: Path, results: list[dict[str, Any]]) -> None:
    fields = [
        "브랜드명",
        "대표그룹",
        "세부유형",
        "근거등급",
        "정제문장수",
        "의미기반추천영업상품",
        "기존추천영업상품",
        "유사브랜드",
        "유사도",
        "공유키워드",
        "추천근거",
        "주의플래그",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in results:
            writer.writerow(
                {
                    "브랜드명": r["brand_name"],
                    "대표그룹": r["main_group"],
                    "세부유형": r["subtype"],
                    "근거등급": r["evidence_grade"],
                    "정제문장수": r["clean_sentence_count"],
                    "의미기반추천영업상품": " / ".join(r["semantic_sales_products"]),
                    "기존추천영업상품": " / ".join(r["original_sales_products"]),
                    "유사브랜드": " / ".join(n["brand_name"] for n in r["nearest_brands"]),
                    "유사도": " / ".join(str(n["score"]) for n in r["nearest_brands"]),
                    "공유키워드": ", ".join(r["shared_keywords"][:10]),
                    "추천근거": r["reason"],
                    "주의플래그": r["caution_flags"],
                }
            )


def write_md(path: Path, results: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    lines = [
        "# 논문 기반 브랜드 의미 유사도 추천 결과",
        "",
        "## 적용 방식",
        "- 논문: 상품명/설명을 BERT 벡터로 만들고 nearest neighbor로 유사 상품을 추천",
        "- 적용: 브랜드 리뷰/FAQ/장점/단점/키워드를 브랜드 문서로 만들고 로컬 TF-IDF 벡터로 유사 브랜드 추천",
        "- 이유: 현재 환경에서는 API 없이 안정적으로 295개 브랜드를 돌리는 것이 우선이며, 추후 BERT 임베딩으로 교체 가능",
        "",
        "## 요약",
        f"- 브랜드 수: {summary['brand_count']}",
        f"- 평균 최고 유사도: {summary['avg_top_score']}",
        f"- 노이즈 주의 브랜드: {summary['noisy_count']}",
        "",
        "## 샘플",
    ]
    for r in results[:30]:
        lines.extend(
            [
                f"### {r['brand_name']}",
                f"- 그룹: {r['main_group']} / {r['subtype']} / 근거 {r['evidence_grade']}",
                f"- 의미기반 추천: {' / '.join(r['semantic_sales_products'])}",
                f"- 유사 브랜드: {' / '.join(n['brand_name'] for n in r['nearest_brands'][:3])}",
                f"- 공유 키워드: {', '.join(r['shared_keywords'][:6])}",
                f"- 근거: {r['reason']}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    top_scores = [r["nearest_brands"][0]["score"] for r in results if r["nearest_brands"]]
    product_counts = Counter()
    for r in results:
        product_counts.update(r["semantic_sales_products"])
    return {
        "brand_count": len(results),
        "avg_top_score": round(sum(top_scores) / max(len(top_scores), 1), 4),
        "noisy_count": sum(1 for r in results if r["noisy_input"]),
        "semantic_sales_product_counts": dict(product_counts.most_common()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a local paper-inspired semantic brand recommender.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--prefix", default=DEFAULT_PREFIX)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--max-features", type=int, default=12000)
    args = parser.parse_args()

    rows = read_rows(args.input)
    docs = [build_brand_document(row) for row in rows]
    vectors, vocab_terms = build_tfidf(docs, args.max_features)
    results = build_outputs(rows, vectors, args.top_k)
    summary = summarize(results)
    summary["vocab_size"] = len(vocab_terms)
    summary["method"] = "local_tfidf_word_and_korean_char_ngrams_nearest_neighbor"

    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / f"{args.prefix}.csv"
    json_path = args.output_dir / f"{args.prefix}.json"
    md_path = args.output_dir / f"{args.prefix}.md"
    summary_path = args.output_dir / f"{args.prefix}_summary.json"

    write_csv(csv_path, results)
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    write_md(md_path, results, summary)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"brands={len(results)}")
    print(f"vocab={len(vocab_terms)}")
    print(f"csv={csv_path}")
    print(f"json={json_path}")
    print(f"markdown={md_path}")
    print(f"summary={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
