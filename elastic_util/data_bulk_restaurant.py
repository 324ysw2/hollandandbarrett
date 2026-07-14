from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterator

import ijson
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX_NAME = "restaurant_reviews"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bulk index restaurant review JSON files into Elasticsearch.")
    parser.add_argument("--input", action="append", default=[], help="Input JSON file. Can repeat.")
    parser.add_argument("--index-name", default=DEFAULT_INDEX_NAME)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=9200)
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--recreate", action="store_true", help="Delete and recreate index before indexing.")
    parser.add_argument("--limit", type=int, default=0, help="Index only first N docs per file for testing.")
    return parser.parse_args()


def default_inputs() -> list[Path]:
    return sorted((PROJECT_ROOT / "data" / "posts").glob("posts_*.json"))


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
                "res_id": {"type": "keyword"},
                "res_name": {
                    "type": "text",
                    "analyzer": "korean_analyzer",
                    "fields": {"keyword": {"type": "keyword"}},
                },
                "adress": {
                    "type": "text",
                    "analyzer": "korean_analyzer",
                    "fields": {"keyword": {"type": "keyword"}},
                },
                "comment": {"type": "text", "analyzer": "korean_analyzer"},
                "pro_comment": {"type": "text", "analyzer": "korean_analyzer"},
                "keywords": {
                    "type": "keyword",
                    "fields": {"nori": {"type": "text", "analyzer": "korean_analyzer"}},
                },
                "comment_vector": {"type": "dense_vector", "dims": 768},
                "source_file": {"type": "keyword"},
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


def normalize_doc(raw: dict[str, Any], source_file: str, sequence: int) -> dict[str, Any]:
    doc = dict(raw)
    doc["id"] = str(doc.get("id") or f"{source_file}:{sequence}")
    doc["source_file"] = source_file

    vector = doc.get("comment_vector")
    if isinstance(vector, list) and len(vector) != 768:
        doc.pop("comment_vector", None)
    elif not isinstance(vector, list):
        doc.pop("comment_vector", None)

    if "keywords" in doc and not isinstance(doc["keywords"], list):
        doc["keywords"] = [str(doc["keywords"])]
    return doc


def iter_json_array(path: Path, limit: int) -> Iterator[dict[str, Any]]:
    with path.open("rb") as input_file:
        for index, item in enumerate(ijson.items(input_file, "item"), start=1):
            if limit and index > limit:
                break
            if isinstance(item, dict):
                yield normalize_doc(item, path.name, index)


def make_actions(index_name: str, paths: list[Path], limit: int) -> Iterator[dict[str, Any]]:
    for path in paths:
        print(f"Reading: {path}")
        for doc in tqdm(iter_json_array(path, limit), desc=path.name):
            yield {"_index": index_name, "_id": doc["id"], "_source": doc}


def main() -> int:
    args = parse_args()
    paths = [Path(item).expanduser().resolve() for item in args.input] if args.input else default_inputs()
    paths = [path for path in paths if path.exists()]
    if not paths:
        raise FileNotFoundError("No input JSON files found.")

    es = Elasticsearch([{"host": args.host, "port": args.port}], timeout=60, max_retries=3, retry_on_timeout=True)
    create_index(es, args.index_name, args.recreate)

    success_count, errors = bulk(
        es,
        make_actions(args.index_name, paths, args.limit),
        chunk_size=args.batch_size,
        request_timeout=120,
        raise_on_error=False,
    )
    print(f"Indexed docs: {success_count}")
    if errors:
        print(f"Bulk errors: {len(errors)}")
        print(json.dumps(errors[:3], ensure_ascii=False, indent=2)[:4000])
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
