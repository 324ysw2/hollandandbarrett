from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterator

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from tqdm import tqdm


DEFAULT_INPUT_DIR = Path(r"C:\projects\db\땀띠화장품2")
DEFAULT_INDEX_NAME = "cosmetic_brand_review_analysis"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bulk index brand review-analysis JSON files into Elasticsearch.")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR), help="Directory containing brand JSON files.")
    parser.add_argument("--index-name", default=DEFAULT_INDEX_NAME)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=9200)
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--recreate", action="store_true", help="Delete and recreate index before indexing.")
    parser.add_argument("--limit-files", type=int, default=0, help="Index only first N files for testing.")
    return parser.parse_args()


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
                "doc_id": {"type": "keyword"},
                "brand_name": {
                    "type": "text",
                    "analyzer": "korean_analyzer",
                    "fields": {"keyword": {"type": "keyword"}},
                },
                "source_file": {"type": "keyword"},
                "source_url": {"type": "keyword"},
                "section": {
                    "type": "text",
                    "analyzer": "korean_analyzer",
                    "fields": {"keyword": {"type": "keyword"}},
                },
                "text": {"type": "text", "analyzer": "korean_analyzer"},
                "emails": {"type": "keyword"},
                "phones": {"type": "keyword"},
                "homepage": {"type": "keyword"},
                "status": {"type": "keyword"},
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


def iter_strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        text = value.strip()
        if text:
            yield text
    elif isinstance(value, list):
        for item in value:
            yield from iter_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_strings(item)


def review_items(raw: dict[str, Any]) -> list[dict[str, Any]]:
    analysis = raw.get("review_analysis")
    if not isinstance(analysis, dict):
        return []
    items = analysis.get("items")
    return items if isinstance(items, list) else []


def make_brand_summary_doc(raw: dict[str, Any], source_file: Path) -> dict[str, Any]:
    summary = raw.get("summary") if isinstance(raw.get("summary"), dict) else {}
    text_parts = []
    for key in ("status", "homepage"):
        if raw.get(key):
            text_parts.append(str(raw[key]))
    text_parts.extend(iter_strings(summary))
    return {
        "doc_id": f"{source_file.stem}:summary",
        "brand_name": raw.get("brand_name") or source_file.stem,
        "source_file": source_file.name,
        "source_url": raw.get("homepage") or "",
        "section": "brand_summary",
        "text": "\n".join(dict.fromkeys(text_parts)),
        "emails": raw.get("emails") if isinstance(raw.get("emails"), list) else [],
        "phones": raw.get("phones") if isinstance(raw.get("phones"), list) else [],
        "homepage": raw.get("homepage") or "",
        "status": raw.get("status") or "",
    }


def iter_docs(path: Path) -> Iterator[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw, dict):
        return

    yield make_brand_summary_doc(raw, path)

    brand_name = raw.get("brand_name") or path.stem
    for item_index, item in enumerate(review_items(raw), start=1):
        if not isinstance(item, dict):
            continue
        source_url = str(item.get("url") or "")
        status = str(item.get("status") or "")
        for section, value in item.items():
            if section in {"url", "status"}:
                continue
            for text_index, text in enumerate(iter_strings(value), start=1):
                yield {
                    "doc_id": f"{path.stem}:item{item_index}:{section}:{text_index}",
                    "brand_name": brand_name,
                    "source_file": path.name,
                    "source_url": source_url,
                    "section": str(section),
                    "text": text,
                    "emails": raw.get("emails") if isinstance(raw.get("emails"), list) else [],
                    "phones": raw.get("phones") if isinstance(raw.get("phones"), list) else [],
                    "homepage": raw.get("homepage") or "",
                    "status": status,
                }


def make_actions(index_name: str, paths: list[Path]) -> Iterator[dict[str, Any]]:
    for path in tqdm(paths, desc="files"):
        for doc in iter_docs(path):
            yield {"_index": index_name, "_id": doc["doc_id"], "_source": doc}


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input_dir).expanduser().resolve()
    paths = sorted(input_dir.glob("*.json"))
    if args.limit_files:
        paths = paths[: args.limit_files]
    if not paths:
        raise FileNotFoundError(f"No JSON files found in {input_dir}.")

    es = Elasticsearch([{"host": args.host, "port": args.port}], timeout=60, max_retries=3, retry_on_timeout=True)
    create_index(es, args.index_name, args.recreate)

    success_count, errors = bulk(
        es,
        make_actions(args.index_name, paths),
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
