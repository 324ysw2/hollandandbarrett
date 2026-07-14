from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX_NAME = "cosmetic_reviews"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bulk index cosmetic review vectors into Elasticsearch.")
    parser.add_argument("--input", default="", help="Input JSON from elastic_util/csv2json.py")
    parser.add_argument("--index-name", default=DEFAULT_INDEX_NAME)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=9200)
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--recreate", action="store_true", help="Delete and recreate index before indexing")
    return parser.parse_args()


def find_latest_input() -> Path:
    candidates = sorted((PROJECT_ROOT / "data" / "posts").glob("cosmetic_posts_*.json"))
    if not candidates:
        raise FileNotFoundError(
            "No input JSON found. Pass --input or run elastic_util/csv2json.py first."
        )
    return candidates[-1]


def build_index_body() -> dict[str, Any]:
    return {
        "settings": {
            "index": {
                "analysis": {
                    "analyzer": {
                        "korean_analyzer": {
                            "type": "custom",
                            "tokenizer": "nori_tokenizer",
                        }
                    }
                }
            }
        },
        "mappings": {
            "dynamic": "true",
            "properties": {
                "id": {"type": "keyword"},
                "product_id": {"type": "keyword"},
                "brand_name": {
                    "type": "text",
                    "analyzer": "korean_analyzer",
                    "fields": {"keyword": {"type": "keyword"}},
                },
                "product_name": {
                    "type": "text",
                    "analyzer": "korean_analyzer",
                    "fields": {"keyword": {"type": "keyword"}},
                },
                "category": {
                    "type": "text",
                    "analyzer": "korean_analyzer",
                    "fields": {"keyword": {"type": "keyword"}},
                },
                "review": {
                    "type": "text",
                    "analyzer": "korean_analyzer",
                },
                "keywords": {
                    "type": "keyword",
                    "fields": {
                        "nori": {
                            "type": "text",
                            "analyzer": "korean_analyzer",
                        }
                    },
                },
                "review_count": {"type": "integer"},
                "review_vector": {
                    "type": "dense_vector",
                    "dims": 768,
                },
            },
        },
    }


def create_index(es: Elasticsearch, index_name: str, recreate: bool) -> None:
    exists = es.indices.exists(index=index_name)
    if exists and recreate:
        es.indices.delete(index=index_name)
        exists = False

    if not exists:
        es.indices.create(index=index_name, body=build_index_body())
        print(f"Created index: {index_name}")
    else:
        print(f"Index already exists: {index_name}")


def make_actions(index_name: str, docs: list[dict[str, Any]]):
    for sequence, doc in enumerate(docs, start=1):
        doc_id = doc.get("id") or sequence
        yield {
            "_index": index_name,
            "_id": str(doc_id),
            "_source": doc,
        }


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve() if args.input else find_latest_input()
    if not input_path.exists():
        raise FileNotFoundError(f"Input JSON not found: {input_path}")

    es = Elasticsearch([{"host": args.host, "port": args.port}])
    create_index(es, args.index_name, args.recreate)

    docs = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(docs, list):
        raise ValueError(f"Input JSON must be a list of documents: {input_path}")

    success_count, errors = bulk(
        es,
        make_actions(args.index_name, docs),
        chunk_size=args.batch_size,
        raise_on_error=False,
    )

    print(f"Input: {input_path}")
    print(f"Indexed docs: {success_count}")
    if errors:
        print(f"Bulk errors: {len(errors)}")
        print(errors[:3])
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
