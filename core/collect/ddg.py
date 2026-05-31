#!/usr/bin/env python3
"""
collect_ddg.py — web search via DuckDuckGo HTML (no API key).

Gives the LLM "eyes": runs several search queries, returns title + snippet +
real URL per result. Works through proxies and is NOT IP-banned like Reddit's
API, while still surfacing Reddit threads, review sites, and media in results.

    python3 core/collect/ddg.py --queries "smart pet feeder review" \\
        "smart pet feeder reddit" --out evidence/web.jsonl

Output JSONL: { title, text(snippet), url, score(rank proxy), source:"web", query }
Stdlib only; uses curl when available (proxy/TLS reliability), else urllib.
"""
import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def _http(url: str) -> str:
    # curl first (handles proxy/TLS where urllib is flaky), then urllib.
    if shutil.which("curl"):
        try:
            out = subprocess.run(["curl", "-s", "-m", "20", "-A", UA, url],
                                 capture_output=True, timeout=25)
            if out.returncode == 0 and out.stdout:
                return out.stdout.decode("utf-8", "replace")
        except Exception:
            pass
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "replace")


def _decode_url(href: str) -> str:
    """DDG HTML wraps links as //duckduckgo.com/l/?uddg=<encoded>. Unwrap it."""
    if "uddg=" in href:
        m = re.search(r"uddg=([^&]+)", href)
        if m:
            return urllib.parse.unquote(m.group(1))
    if href.startswith("//"):
        return "https:" + href
    return href


# DDG HTML result block: <a ... class="result__a" href="...">TITLE</a>
# ... <a class="result__snippet" ...>SNIPPET</a>
RESULT_A = re.compile(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S)
SNIPPET = re.compile(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', re.S)


def _strip_tags(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def search(query: str, max_results: int = 10):
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    sys.stderr.write(f"[ddg] {query}\n")
    try:
        page = _http(url)
    except Exception as e:
        sys.stderr.write(f"[ddg] query failed: {e}\n")
        return []
    titles = RESULT_A.findall(page)
    snippets = SNIPPET.findall(page)
    out = []
    for i, (href, title_html) in enumerate(titles[:max_results]):
        title = _strip_tags(title_html)
        snippet = _strip_tags(snippets[i]) if i < len(snippets) else ""
        if not title:
            continue
        out.append({
            "source": "web",
            "query": query,
            "title": title,
            "text": snippet,
            "url": _decode_url(href),
            # rank proxy so downstream node sizing has variation (no real upvotes)
            "score": max(5, 100 - i * 8),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", nargs="+", required=True)
    ap.add_argument("--max-results", type=int, default=10)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sleep", type=float, default=0.8)
    args = ap.parse_args()

    seen = set()
    n = 0
    with open(args.out, "w", encoding="utf-8") as f:
        for q in args.queries:
            for rec in search(q, args.max_results):
                if rec["url"] in seen:
                    continue
                seen.add(rec["url"])
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n += 1
            time.sleep(args.sleep)
    sys.stderr.write(f"[ddg] done. {n} unique results -> {args.out}\n")


if __name__ == "__main__":
    main()
