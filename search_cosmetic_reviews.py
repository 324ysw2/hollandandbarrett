from __future__ import annotations

import argparse
import sys

from elasticsearch import Elasticsearch


INDEX_NAME = "cosmetic_brand_review_analysis"


def safe_print(value: object) -> None:
    text = str(value)
    print(text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Search indexed cosmetic brand review-analysis documents.")
    parser.add_argument("query", help="Korean query text, for example 피부, 진정, 가려움, 여드름.")
    parser.add_argument("--index-name", default=INDEX_NAME)
    parser.add_argument("--size", type=int, default=5)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=9200)
    args = parser.parse_args()

    es = Elasticsearch([{"host": args.host, "port": args.port}])
    result = es.search(
        index=args.index_name,
        body={
            "query": {"match": {"text": args.query}},
            "_source": ["brand_name", "section", "source_url", "text"],
            "size": args.size,
        },
    )
    total = result["hits"]["total"]["value"] if isinstance(result["hits"]["total"], dict) else result["hits"]["total"]
    safe_print(f"hits: {total}")
    for index, hit in enumerate(result["hits"]["hits"], start=1):
        source = hit["_source"]
        safe_print(f"\n[{index}] {source.get('brand_name')} / {source.get('section')}")
        if source.get("source_url"):
            safe_print(source["source_url"])
        text = (source.get("text") or "").replace("\n", " ")
        safe_print(text[:500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
