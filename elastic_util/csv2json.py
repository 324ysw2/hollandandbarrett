# This Python file uses the following encoding: utf-8
from __future__ import annotations

import argparse
import ast
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from sentence_transformers import SentenceTransformer  # noqa: E402


DEFAULT_MODEL_PATH = (
    PROJECT_ROOT
    / "model"
    / "training_stsbenchmark_skt_kobert_model_-2021-03-28_05-25-43_best"
)
DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "posts"
    / f"cosmetic_posts_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert cosmetic key sentence CSV to vectorized Elasticsearch JSON."
    )
    parser.add_argument("--input", default="", help="Input CSV from keyword/key_sentences.py")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Output JSON path")
    parser.add_argument("--model-path", default=str(DEFAULT_MODEL_PATH), help="SentenceTransformer model path")
    parser.add_argument("--encoding", default="utf-8-sig", help="Input CSV encoding")
    parser.add_argument("--max-text-length", type=int, default=500)
    parser.add_argument("--text-col", default="KEY_COMMENT")
    parser.add_argument("--keywords-col", default="KEY_WORDS")
    return parser.parse_args()


def find_latest_input() -> Path:
    candidates = sorted((PROJECT_ROOT / "data").glob("cosmetic_keysentences_*.csv"))
    if not candidates:
        raise FileNotFoundError(
            "No input CSV found. Pass --input or run keyword/key_sentences.py first."
        )
    return candidates[-1]


def parse_keywords(value: str) -> list[str]:
    value = (value or "").strip()
    if not value:
        return []
    try:
        parsed = ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return [item.strip() for item in value.split(",") if item.strip()]

    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    return [str(parsed).strip()] if str(parsed).strip() else []


def clean_text(value: Any) -> str:
    return str(value or "").strip()


def should_skip_text(text: str, max_text_length: int) -> bool:
    if not text:
        return True
    if text.isspace():
        return True
    if len(text) > max_text_length:
        return True
    return False


def int_or_zero(value: str) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve() if args.input else find_latest_input()
    output_path = Path(args.output).expanduser().resolve()
    model_path = Path(args.model_path).expanduser().resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Model path not found: {model_path}")

    embedder = SentenceTransformer(str(model_path))
    docs: list[dict[str, Any]] = []

    with input_path.open("r", encoding=args.encoding, newline="") as input_file:
        reader = csv.DictReader(input_file)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {input_path}")
        if args.text_col not in reader.fieldnames:
            raise ValueError(f"Text column not found: {args.text_col}")

        for row_index, row in enumerate(tqdm(reader, desc="vectorize cosmetic reviews"), start=1):
            review = clean_text(row.get(args.text_col))
            if should_skip_text(review, args.max_text_length):
                continue

            vector = embedder.encode(review, convert_to_numpy=True).tolist()
            docs.append(
                {
                    "id": str(row_index),
                    "product_id": clean_text(row.get("PRODUCT_ID")),
                    "brand_name": clean_text(row.get("BRAND_NAME")),
                    "product_name": clean_text(row.get("PRODUCT_NAME")),
                    "category": clean_text(row.get("CATEGORY")),
                    "review": review,
                    "keywords": parse_keywords(clean_text(row.get(args.keywords_col))),
                    "review_count": int_or_zero(clean_text(row.get("REVIEW_COUNT"))),
                    "review_vector": vector,
                }
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(docs, ensure_ascii=False), encoding="utf-8")

    print(f"Input: {input_path}")
    print(f"Saved docs: {len(docs)}")
    print(f"Output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
