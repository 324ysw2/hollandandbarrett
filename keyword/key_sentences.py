# This Python file uses the following encoding: utf-8
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd
from krwordrank.sentence import MaxScoreTokenizer, keysentence, make_vocab_score
from krwordrank.word import KRWordRank
from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "cosmetic_reviews.csv"
DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / f"cosmetic_keysentences_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
)

PRODUCT_ID_CANDIDATES = [
    "PRODUCT_ID",
    "product_id",
    "상품ID",
    "상품번호",
    "제품ID",
    "item_id",
    "id",
]
PRODUCT_NAME_CANDIDATES = [
    "PRODUCT_NAME",
    "product_name",
    "상품명",
    "제품명",
    "품명",
    "name",
]
BRAND_CANDIDATES = [
    "BRAND_NAME",
    "brand_name",
    "BRAND",
    "brand",
    "브랜드명",
    "브랜드",
]
CATEGORY_CANDIDATES = [
    "CATEGORY",
    "category",
    "카테고리",
    "분류",
    "대분류",
    "소분류",
]
REVIEW_CANDIDATES = [
    "REVIEW_TEXT",
    "review_text",
    "REVIEW",
    "review",
    "리뷰",
    "리뷰내용",
    "후기",
    "상품평",
    "내용",
    "comment",
    "COMMENT",
]

COSMETIC_STOPWORDS = {
    "제품",
    "상품",
    "사용",
    "구매",
    "주문",
    "배송",
    "리뷰",
    "후기",
    "정말",
    "너무",
    "아주",
    "매우",
    "완전",
    "그냥",
    "조금",
    "많이",
    "계속",
    "항상",
    "바로",
    "일단",
    "진짜",
    "생각",
    "느낌",
    "괜찮",
    "좋아",
    "좋은",
    "좋고",
    "좋다",
    "좋음",
    "좋아요",
    "좋네요",
    "좋았",
    "만족",
    "추천",
    "재구매",
    "처음",
    "다시",
    "자주",
    "같아",
    "같아요",
    "것",
    "거",
    "때",
    "수",
    "좀",
    "더",
    "제",
    "저",
    "제가",
    "저는",
    "피부",
    "얼굴",
    "화장품",
    "스킨케어",
    "케어",
    "바르고",
    "발라",
    "발랐",
    "바르면",
    "써보",
    "써봤",
    "사용해",
    "사용했",
    "사용감",
    "용량",
    "가격",
    "향",
    "냄새",
    "크림",
    "토너",
    "앰플",
    "세럼",
    "로션",
    "마스크",
    "팩",
    "선크림",
    "쿠션",
    "파운데이션",
    "클렌징",
    "샴푸",
    "브랜드",
    "이번",
    "요즘",
    "아침",
    "저녁",
    "하루",
    "며칠",
    "한번",
    "두번",
    "입니다",
    "합니다",
    "있습니다",
    "없습니다",
    "했어요",
    "했는데",
    "있어서",
    "없어서",
    "그리고",
    "하지만",
    "그래서",
    "ㅎㅎ",
    "ㅋㅋ",
    "ㅠㅠ",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract cosmetic review key sentences and keywords per product."
    )
    parser.add_argument("--input", default=str(DEFAULT_INPUT_PATH), help="Cosmetic review CSV path")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Output CSV path")
    parser.add_argument("--encoding", default="utf-8-sig", help="Input CSV encoding")
    parser.add_argument("--product-id-col", default="", help="Product id column. Auto-detected when empty.")
    parser.add_argument("--product-name-col", default="", help="Product name column. Auto-detected when empty.")
    parser.add_argument("--brand-col", default="", help="Brand column. Auto-detected when empty.")
    parser.add_argument("--category-col", default="", help="Category column. Auto-detected when empty.")
    parser.add_argument("--review-col", default="", help="Review text column. Auto-detected when empty.")
    parser.add_argument("--min-reviews", type=int, default=5, help="Minimum reviews needed per product")
    parser.add_argument("--topk-sentences", type=int, default=5, help="Key sentences per product")
    parser.add_argument("--num-keywords", type=int, default=10, help="Keywords saved per product")
    parser.add_argument("--min-count", type=int, default=3, help="KRWordRank minimum word count")
    parser.add_argument("--max-length", type=int, default=10, help="KRWordRank maximum word length")
    parser.add_argument("--beta", type=float, default=0.85, help="KRWordRank PageRank decay factor")
    parser.add_argument("--max-iter", type=int, default=10, help="KRWordRank max iterations")
    return parser.parse_args()


def resolve_column(df: pd.DataFrame, explicit: str, candidates: Iterable[str], label: str, required: bool) -> str | None:
    if explicit:
        if explicit not in df.columns:
            raise ValueError(f"{label} column not found: {explicit}")
        return explicit

    lowered = {str(column).strip().casefold(): column for column in df.columns}
    for candidate in candidates:
        column = lowered.get(candidate.casefold())
        if column is not None:
            return str(column)

    if required:
        raise ValueError(f"Could not auto-detect {label} column. Use --{label.replace('_', '-')}-col.")
    return None


def text_value(row: pd.Series, column: str | None) -> str:
    if not column:
        return ""
    value = row.get(column, "")
    if pd.isna(value):
        return ""
    return str(value).strip()


def clean_reviews(values: Iterable[object]) -> list[str]:
    texts: list[str] = []
    for value in values:
        if pd.isna(value):
            continue
        text = str(value).strip()
        if not text:
            continue
        texts.append(text)
    return texts


def get_wordrank_keywords(
    texts: list[str],
    min_count: int,
    max_length: int,
    beta: float,
    max_iter: int,
) -> dict[str, float]:
    wordrank_extractor = KRWordRank(
        min_count=min_count,
        max_length=max_length,
        verbose=False,
    )
    keywords, _, _ = wordrank_extractor.extract(texts, beta, max_iter, num_keywords=50)
    return keywords


def prune_keywords(keywords: dict[str, float], stopwords: set[str], limit: int) -> list[str]:
    pruned: list[str] = []
    for keyword in keywords:
        normalized = keyword.strip()
        if not normalized:
            continue
        if normalized in stopwords:
            continue
        if any(normalized.startswith(stopword) and len(normalized) <= len(stopword) + 1 for stopword in stopwords):
            continue
        pruned.append(normalized)
        if len(pruned) >= limit:
            break
    return pruned


def extract_key_sentences(
    texts: list[str],
    keywords: dict[str, float],
    stopwords: set[str],
    topk: int,
) -> list[str]:
    vocab_score = make_vocab_score(keywords, stopwords, scaling=lambda _: 1)
    if not vocab_score:
        return texts[:topk]

    tokenizer = MaxScoreTokenizer(vocab_score)
    penalty = lambda sentence: 0 if 8 <= len(sentence) <= 120 else 1
    return keysentence(
        vocab_score,
        texts,
        tokenizer.tokenize,
        penalty=penalty,
        diversity=0.35,
        topk=topk,
    )


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    data = pd.read_csv(input_path, encoding=args.encoding)
    product_id_col = resolve_column(data, args.product_id_col, PRODUCT_ID_CANDIDATES, "product_id", False)
    product_name_col = resolve_column(data, args.product_name_col, PRODUCT_NAME_CANDIDATES, "product_name", True)
    brand_col = resolve_column(data, args.brand_col, BRAND_CANDIDATES, "brand", False)
    category_col = resolve_column(data, args.category_col, CATEGORY_CANDIDATES, "category", False)
    review_col = resolve_column(data, args.review_col, REVIEW_CANDIDATES, "review", True)

    selected_columns = [column for column in [product_id_col, product_name_col, brand_col, category_col, review_col] if column]
    review_data = data[selected_columns].dropna(subset=[product_name_col, review_col])

    group_column = product_id_col or product_name_col
    rows: list[dict[str, object]] = []

    print(f"Input rows: {len(data)}")
    print(f"Usable review rows: {len(review_data)}")
    print(f"Group column: {group_column}")
    print(f"Review column: {review_col}")

    for _, product_df in tqdm(review_data.groupby(group_column), desc="extract key sentences"):
        texts = clean_reviews(product_df[review_col])
        if len(texts) < args.min_reviews:
            continue

        first_row = product_df.iloc[0]
        try:
            keywords = get_wordrank_keywords(
                texts=texts,
                min_count=args.min_count,
                max_length=args.max_length,
                beta=args.beta,
                max_iter=args.max_iter,
            )
            key_sentences = extract_key_sentences(
                texts=texts,
                keywords=keywords,
                stopwords=COSMETIC_STOPWORDS,
                topk=args.topk_sentences,
            )
            keyword_list = prune_keywords(keywords, COSMETIC_STOPWORDS, args.num_keywords)
        except Exception as exc:
            print(f"Skip product={text_value(first_row, product_name_col)}: {exc}")
            continue

        for sentence in key_sentences:
            rows.append(
                {
                    "PRODUCT_ID": text_value(first_row, product_id_col),
                    "BRAND_NAME": text_value(first_row, brand_col),
                    "PRODUCT_NAME": text_value(first_row, product_name_col),
                    "CATEGORY": text_value(first_row, category_col),
                    "KEY_COMMENT": sentence,
                    "KEY_WORDS": keyword_list,
                    "REVIEW_COUNT": len(texts),
                }
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        rows,
        columns=[
            "PRODUCT_ID",
            "BRAND_NAME",
            "PRODUCT_NAME",
            "CATEGORY",
            "KEY_COMMENT",
            "KEY_WORDS",
            "REVIEW_COUNT",
        ],
    ).to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"Saved rows: {len(rows)}")
    print(f"Output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
