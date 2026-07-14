from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "brand_json_summaries"
DEFAULT_OUTPUT_JSON = DATA_DIR / "meta_ads_library_results.json"
DEFAULT_OUTPUT_CSV = DATA_DIR / "meta_ads_library_results.csv"


def build_query_params(search_terms: str, countries: list[str] | None = None, limit: int = 20) -> dict[str, Any]:
    params: dict[str, Any] = {
        "search_terms": search_terms,
        "ad_type": "ALL",
        "fields": "id,ad_creation_time,ad_creative_body,ad_creative_link_title,ad_creative_link_description,ad_snapshot_url",
        "limit": limit,
    }
    if countries:
        params["ad_reached_countries"] = countries
    return params


def build_request_url(api_version: str = "v22.0") -> str:
    return f"https://graph.facebook.com/{api_version}/ads_archive"


def normalize_ads(payload: dict[str, Any], search_terms: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in payload.get("data", []) or []:
        rows.append(
            {
                "id": item.get("id", ""),
                "created_time": item.get("ad_creation_time", ""),
                "body": item.get("ad_creative_body", ""),
                "title": item.get("ad_creative_link_title", ""),
                "description": item.get("ad_creative_link_description", ""),
                "snapshot_url": item.get("ad_snapshot_url", ""),
                "search_terms": search_terms,
            }
        )
    return rows


def write_outputs(rows: list[dict[str, Any]], output_json: Path, output_csv: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    fieldnames = ["id", "created_time", "body", "title", "description", "snapshot_url", "search_terms"]
    with output_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def fetch_ads(search_terms: str, countries: list[str] | None = None, limit: int = 20, access_token: str | None = None) -> list[dict[str, Any]]:
    token = access_token or os.getenv("META_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("META_ACCESS_TOKEN is required")

    params = build_query_params(search_terms=search_terms, countries=countries, limit=limit)
    params["access_token"] = token
    response = requests.get(build_request_url(), params=params, timeout=60)
    response.raise_for_status()
    payload = response.json()
    return normalize_ads(payload, search_terms=search_terms)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch public Meta Ads Library results")
    parser.add_argument("--search-terms", default="스킨케어")
    parser.add_argument("--countries", nargs="*", default=["KR"])
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--output-csv", default=str(DEFAULT_OUTPUT_CSV))
    args = parser.parse_args()

    rows = fetch_ads(args.search_terms, countries=args.countries, limit=args.limit)
    write_outputs(rows, Path(args.output_json), Path(args.output_csv))
    print(f"Wrote {len(rows)} ad rows to {args.output_json} and {args.output_csv}")


if __name__ == "__main__":
    main()
