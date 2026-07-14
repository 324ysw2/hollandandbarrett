from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_INPUT_DIR = Path(r"C:\projects\db\땀띠화장품2")
DEFAULT_OUTPUT = Path(r"C:\projects\db\final_project\reports\cosmetic_brand_review_viewer.html")


def iter_text(value: Any) -> list[str]:
    texts: list[str] = []
    if isinstance(value, str):
        text = re.sub(r"\s+", " ", value).strip()
        if text:
            texts.append(text)
    elif isinstance(value, list):
        for item in value:
            texts.extend(iter_text(item))
    elif isinstance(value, dict):
        for item in value.values():
            texts.extend(iter_text(item))
    return texts


def short(text: str, limit: int = 700) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def load_brand(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw, dict):
        raw = {}

    display_name = path.stem
    homepage = str(raw.get("homepage") or "")
    emails = raw.get("emails") if isinstance(raw.get("emails"), list) else []
    phones = raw.get("phones") if isinstance(raw.get("phones"), list) else []
    media = raw.get("current_media") if isinstance(raw.get("current_media"), list) else []
    evidence = raw.get("evidence_urls") if isinstance(raw.get("evidence_urls"), list) else []

    review_analysis = raw.get("review_analysis") if isinstance(raw.get("review_analysis"), dict) else {}
    items = review_analysis.get("items") if isinstance(review_analysis.get("items"), list) else []

    sections: dict[str, list[dict[str, str]]] = {}
    source_urls: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        source_url = str(item.get("url") or "")
        if source_url:
            source_urls.append(source_url)
        for key, value in item.items():
            if key in {"url", "status"}:
                continue
            texts = [short(text) for text in iter_text(value)]
            if not texts:
                continue
            bucket = sections.setdefault(str(key), [])
            for text in texts:
                bucket.append({"url": source_url, "text": text})

    section_counts = {key: len(value) for key, value in sections.items()}
    total_texts = sum(section_counts.values())
    return {
        "name": display_name,
        "file": path.name,
        "homepage": homepage,
        "emails": emails,
        "phones": phones,
        "media": media,
        "evidence": evidence[:8],
        "source_urls": sorted(set(source_urls)),
        "sections": sections,
        "section_counts": section_counts,
        "total_texts": total_texts,
    }


def tag(value: str) -> str:
    return f"<span class=\"tag\">{html.escape(value)}</span>"


def render_brand(brand: dict[str, Any]) -> str:
    name = html.escape(brand["name"])
    search_blob = " ".join(
        [
            brand["name"],
            brand["homepage"],
            " ".join(map(str, brand["emails"])),
            " ".join(map(str, brand["phones"])),
            " ".join(map(str, brand["media"])),
            " ".join(brand["sections"].keys()),
        ]
    )
    contact_parts = []
    if brand["homepage"]:
        url = html.escape(brand["homepage"])
        contact_parts.append(f"<a href=\"{url}\" target=\"_blank\">홈페이지</a>")
    contact_parts.extend(tag(str(item)) for item in brand["emails"][:3])
    contact_parts.extend(tag(str(item)) for item in brand["phones"][:3])
    contact_parts.extend(tag(str(item)) for item in brand["media"][:5])
    contacts = "\n".join(contact_parts) or "<span class=\"muted\">연락처/매체 정보 없음</span>"

    source_urls = "\n".join(
        f"<li><a href=\"{html.escape(url)}\" target=\"_blank\">{html.escape(url)}</a></li>"
        for url in brand["source_urls"][:8]
    )
    if not source_urls:
        source_urls = "<li class=\"muted\">수집 URL 없음</li>"

    section_html = []
    for section, rows in sorted(brand["sections"].items(), key=lambda item: len(item[1]), reverse=True):
        escaped_section = html.escape(section)
        cards = []
        for row in rows[:20]:
            url = row["url"]
            url_html = (
                f"<a class=\"source\" href=\"{html.escape(url)}\" target=\"_blank\">source</a>"
                if url
                else ""
            )
            cards.append(
                "<div class=\"quote\">"
                f"<div>{html.escape(row['text'])}</div>"
                f"{url_html}"
                "</div>"
            )
        if len(rows) > 20:
            cards.append(f"<div class=\"muted more\">외 {len(rows) - 20}개 문구는 원본 JSON/Elasticsearch에서 확인</div>")
        section_html.append(
            "<details class=\"section\">"
            f"<summary>{escaped_section} <span>{len(rows)}</span></summary>"
            + "\n".join(cards)
            + "</details>"
        )
    if not section_html:
        section_html.append("<p class=\"muted\">리뷰 분석 텍스트가 없습니다.</p>")

    return f"""
    <article class="brand" id="brand-{html.escape(brand['file'])}" data-search="{html.escape(search_blob.lower())}">
      <div class="brand-head">
        <div>
          <h2>{name}</h2>
          <p class="muted">{html.escape(brand['file'])} · 분석 문구 {brand['total_texts']:,}개</p>
        </div>
        <div class="contact">{contacts}</div>
      </div>
      <details class="sources">
        <summary>수집 URL 보기</summary>
        <ul>{source_urls}</ul>
      </details>
      {''.join(section_html)}
    </article>
    """


def render_html(brands: list[dict[str, Any]]) -> str:
    total_docs = sum(brand["total_texts"] for brand in brands)
    section_counter: Counter[str] = Counter()
    for brand in brands:
        section_counter.update(brand["section_counts"])
    section_summary = " ".join(tag(f"{key} {value}") for key, value in section_counter.most_common(10))
    nav_items = "\n".join(
        f"<a href=\"#brand-{html.escape(brand['file'])}\" data-search=\"{html.escape(brand['name'].lower())}\">{html.escape(brand['name'])}<span>{brand['total_texts']}</span></a>"
        for brand in brands
    )
    brand_html = "\n".join(render_brand(brand) for brand in brands)
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>홀렌드앤바렛을 위한 리뷰분석 뷰어</title>
  <style>
    :root {{
      --bg: #f7f8fa;
      --panel: #ffffff;
      --text: #20242a;
      --muted: #6b7280;
      --line: #dfe3ea;
      --accent: #0f766e;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: "Segoe UI", "Malgun Gothic", Arial, sans-serif; background: var(--bg); color: var(--text); }}
    header {{ position: sticky; top: 0; z-index: 3; background: var(--panel); border-bottom: 1px solid var(--line); padding: 18px 24px; }}
    h1 {{ margin: 0 0 8px; font-size: 24px; letter-spacing: 0; }}
    .stats {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; color: var(--muted); font-size: 14px; }}
    .layout {{ display: grid; grid-template-columns: 300px minmax(0, 1fr); min-height: calc(100vh - 92px); }}
    aside {{ position: sticky; top: 91px; align-self: start; max-height: calc(100vh - 91px); overflow: auto; border-right: 1px solid var(--line); background: #fbfcfd; padding: 14px; }}
    main {{ padding: 18px 24px 48px; }}
    input {{ width: 100%; height: 42px; border: 1px solid var(--line); border-radius: 6px; padding: 0 12px; font-size: 15px; }}
    nav {{ display: grid; gap: 4px; margin-top: 12px; }}
    nav a {{ display: flex; justify-content: space-between; gap: 12px; padding: 8px 10px; color: var(--text); text-decoration: none; border-radius: 6px; font-size: 14px; }}
    nav a:hover {{ background: #e8f3f1; }}
    nav span {{ color: var(--muted); }}
    .brand {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; margin: 0 0 14px; padding: 18px; }}
    .brand-head {{ display: flex; justify-content: space-between; gap: 24px; align-items: flex-start; border-bottom: 1px solid var(--line); padding-bottom: 14px; margin-bottom: 12px; }}
    h2 {{ margin: 0; font-size: 22px; letter-spacing: 0; }}
    .muted {{ color: var(--muted); font-size: 13px; }}
    .contact {{ display: flex; flex-wrap: wrap; gap: 6px; justify-content: flex-end; max-width: 55%; }}
    .tag, .contact a {{ display: inline-flex; align-items: center; min-height: 26px; border: 1px solid #c9dedb; background: #f0fdfa; color: #115e59; padding: 3px 8px; border-radius: 999px; font-size: 12px; text-decoration: none; }}
    details {{ border-radius: 6px; }}
    summary {{ cursor: pointer; user-select: none; font-weight: 700; }}
    .sources {{ margin: 10px 0 12px; color: var(--muted); }}
    .sources ul {{ margin: 8px 0 0; padding-left: 20px; overflow-wrap: anywhere; }}
    .section {{ border: 1px solid var(--line); margin-top: 10px; background: #fff; }}
    .section summary {{ display: flex; justify-content: space-between; padding: 12px; }}
    .section summary span {{ color: var(--accent); }}
    .quote {{ border-top: 1px solid var(--line); padding: 12px; line-height: 1.58; font-size: 14px; white-space: normal; }}
    .source {{ display: inline-block; margin-top: 8px; color: var(--accent); font-size: 12px; }}
    .more {{ padding: 12px; border-top: 1px solid var(--line); }}
    .hidden {{ display: none !important; }}
    @media (max-width: 900px) {{
      .layout {{ grid-template-columns: 1fr; }}
      aside {{ position: static; max-height: none; border-right: 0; border-bottom: 1px solid var(--line); }}
      .brand-head {{ display: block; }}
      .contact {{ max-width: none; justify-content: flex-start; margin-top: 10px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>홀렌드앤바렛을 위한 리뷰분석 뷰어</h1>
    <div class="stats">
      <span>브랜드 {len(brands):,}개</span>
      <span>분석 문구 {total_docs:,}개</span>
      {section_summary}
    </div>
  </header>
  <div class="layout">
    <aside>
      <input id="search" placeholder="브랜드명, URL, 섹션 검색">
      <nav id="brandNav">{nav_items}</nav>
    </aside>
    <main id="brands">{brand_html}</main>
  </div>
  <script>
    const input = document.querySelector('#search');
    const brands = [...document.querySelectorAll('.brand')];
    const navs = [...document.querySelectorAll('#brandNav a')];
    input.addEventListener('input', () => {{
      const q = input.value.trim().toLowerCase();
      brands.forEach(el => {{
        el.classList.toggle('hidden', q && !el.dataset.search.includes(q));
      }});
      navs.forEach(el => {{
        el.classList.toggle('hidden', q && !el.dataset.search.includes(q));
      }});
    }});
  </script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a static HTML viewer for brand review JSON files.")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    input_dir = Path(args.input_dir).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    paths = sorted(input_dir.glob("*.json"), key=lambda item: item.stem.lower())
    if not paths:
        raise FileNotFoundError(f"No JSON files found in {input_dir}.")

    brands = [load_brand(path) for path in paths]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_html(brands), encoding="utf-8")
    print(output)
    print(f"brands={len(brands)} texts={sum(brand['total_texts'] for brand in brands)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
