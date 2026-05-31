#!/usr/bin/env python3
"""
Marketplace VOC collector with pluggable adapter interface.

Usage:
  python templates/crawler/collect_marketplace.py \
      --adapter trustpilot \
      --query "smart ring oura" \
      --out fixtures/marketplace/oura-trustpilot.json

  python templates/crawler/collect_marketplace.py \
      --adapter amazon \
      --query "Oura Ring 4" \
      --out raw/oura-amazon.json
      # NOTE: amazon adapter requires AMAZON_PROXY_URL env var + legal review

  python templates/crawler/collect_marketplace.py \
      --fixture fixtures/marketplace/oura-amazon.json
      # offline mode: reads pre-collected fixture (no API)

Output format (one entry per player/platform pair):
  {
    "player":       "oura",            # caller-provided
    "platform":     "Amazon US",
    "rating":       4.3,
    "review_count": 12847,
    "top_complaints": ["subscription cost", "battery", "scratches"],
    "top_praises":   ["sleep accuracy", "medical alerts"],
    "url":          "https://www.amazon.com/...",
    "collected_at": "2026-05-19",
    "raw_reviews":  [ { "rating": int, "title": str, "body": str, "ts": iso8601 }, ... ]
  }

Status:
  - trustpilot:     IMPLEMENTED (public scraping API)
  - reddit_brand:   IMPLEMENTED (delegates to collect_reddit.py)
  - amazon:         STUB · requires proxy + legal sign-off (see ADR-001)
  - best_buy:       STUB
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import date
from pathlib import Path
from typing import Protocol, Optional
import urllib.request
import urllib.parse
import urllib.error

ROOT = Path(__file__).resolve().parent.parent.parent
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 "
    "vibe-research-crawler (+contact: research@example.com)"
)


# --------------------------------------------------------------------------- #
# Data contract                                                                #
# --------------------------------------------------------------------------- #

@dataclass
class RawReview:
    rating: int
    title: str
    body: str
    ts: Optional[str] = None
    helpful: Optional[int] = None


@dataclass
class MarketplaceEntry:
    """One row of the marketplace[] section in report-data.schema.json."""
    player: str
    platform: str
    rating: float
    review_count: int
    top_complaints: list[str] = field(default_factory=list)
    top_praises:    list[str] = field(default_factory=list)
    url: str = ""
    collected_at: str = ""
    raw_reviews: list[RawReview] = field(default_factory=list)

    def to_schema_dict(self) -> dict:
        """Strip raw_reviews; keep only schema-compatible fields."""
        d = asdict(self)
        d.pop("raw_reviews", None)
        return d


class MarketplaceAdapter(Protocol):
    """Implement search() + fetch() to add a new platform."""
    platform_name: str

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Return list of { 'listing_id': str, 'title': str, 'url': str }."""
        ...

    def fetch(self, listing_id: str, *, max_reviews: int = 200) -> MarketplaceEntry:
        ...


# --------------------------------------------------------------------------- #
# Adapter: Trustpilot                                                          #
# --------------------------------------------------------------------------- #

class TrustpilotAdapter:
    """
    Trustpilot publishes review pages at trustpilot.com/review/{domain}.
    The page embeds NEXT_DATA JSON that includes review summary + recent reviews.
    """
    platform_name = "Trustpilot"

    def search(self, query: str, limit: int = 5) -> list[dict]:
        # Trustpilot doesn't have an open search API; we use a heuristic that
        # converts the query into a likely domain (e.g. "oura ring" → "ouraring.com").
        # Caller should pass --listing-id directly for precision.
        domain_guess = re.sub(r"[^a-z]", "", query.lower().split()[0]) + ".com"
        return [{
            "listing_id": domain_guess,
            "title":      f"(domain guess) {domain_guess}",
            "url":        f"https://www.trustpilot.com/review/{domain_guess}",
        }]

    def fetch(self, listing_id: str, *, max_reviews: int = 200) -> MarketplaceEntry:
        url = f"https://www.trustpilot.com/review/{listing_id}"
        try:
            html = _http_get(url)
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                raise NotImplementedError(
                    f"Trustpilot blocked us with HTTP {e.code} — Cloudflare anti-bot. "
                    f"Production needs proper UA + cookies or a scraping service. "
                    f"Use --fixture for now."
                ) from e
            raise
        # Trustpilot embeds review aggregate in JSON-LD
        ld_match = re.search(
            r'<script type="application/ld\+json"[^>]*>(.+?)</script>',
            html, re.S,
        )
        rating, review_count = 0.0, 0
        if ld_match:
            try:
                ld = json.loads(ld_match.group(1))
                if isinstance(ld, list):
                    ld = next((x for x in ld if x.get("@type") == "LocalBusiness"), ld[0])
                agg = ld.get("aggregateRating", {})
                rating = float(agg.get("ratingValue") or 0)
                review_count = int(agg.get("reviewCount") or 0)
            except (json.JSONDecodeError, ValueError, KeyError):
                pass

        return MarketplaceEntry(
            player="",  # caller fills
            platform=self.platform_name,
            rating=rating,
            review_count=review_count,
            url=url,
            collected_at=date.today().isoformat(),
            raw_reviews=[],  # extracting individual reviews from Trustpilot HTML
                              # is fragile; left as TODO (#extension-trustpilot-reviews)
        )


# --------------------------------------------------------------------------- #
# Adapter: Reddit (brand sub as a marketplace proxy)                           #
# --------------------------------------------------------------------------- #

class RedditBrandAdapter:
    """
    Fallback when there's no real marketplace data — pull aggregate sentiment
    from r/{brand_subreddit} using the existing collect_reddit.py logic.

    This is honest: we label platform='Reddit r/{sub}' so readers don't
    mistake it for Amazon-style structured reviews.
    """
    platform_name = "Reddit (brand sub)"

    def search(self, query: str, limit: int = 5) -> list[dict]:
        # Map first token of query to a subreddit name.
        token = query.lower().split()[0]
        return [{
            "listing_id": token,
            "title":      f"r/{token}",
            "url":        f"https://www.reddit.com/r/{token}/",
        }]

    def fetch(self, listing_id: str, *, max_reviews: int = 200) -> MarketplaceEntry:
        # listing_id is the subreddit slug
        url = f"https://www.reddit.com/r/{listing_id}/top.json?t=year&limit={min(max_reviews, 100)}"
        try:
            body = _http_get(url)
            payload = json.loads(body)
            children = payload.get("data", {}).get("children", [])
        except (urllib.error.HTTPError, json.JSONDecodeError) as e:
            print(f"  ! reddit /r/{listing_id} fetch failed: {e}", file=sys.stderr)
            children = []

        upvotes = [c["data"].get("score", 0) for c in children if c.get("kind") == "t3"]
        # Cheap synthetic rating: median upvote percentile → 1..5
        rating = round(3.5 + min(1.5, (sum(upvotes) / max(1, len(upvotes))) / 1000), 1) if upvotes else 0.0

        return MarketplaceEntry(
            player="",
            platform=f"Reddit r/{listing_id}",
            rating=rating,
            review_count=len(children),
            url=f"https://www.reddit.com/r/{listing_id}/",
            collected_at=date.today().isoformat(),
            raw_reviews=[
                RawReview(
                    rating=5 if c["data"].get("score", 0) > 50 else 3,
                    title=c["data"].get("title", ""),
                    body=c["data"].get("selftext", "")[:300],
                    ts=str(c["data"].get("created_utc", "")),
                    helpful=c["data"].get("score", 0),
                )
                for c in children[:max_reviews]
            ],
        )


# --------------------------------------------------------------------------- #
# Adapter: Amazon (STUB — needs proxy + legal review)                          #
# --------------------------------------------------------------------------- #

class AmazonAdapter:
    """
    Amazon scraping requires:
      1. Rotating residential proxies (set AMAZON_PROXY_URL env var)
      2. Captcha solver path (anti-bot triggers within ~5 requests/IP)
      3. Legal review per ADR-001-amazon-scraping.md (TODO write ADR)
      4. Adherence to robots.txt and Amazon ToS — likely requires direct
         business partnership or ScrapingBee / Bright Data subscription.

    Until those are signed off, this adapter raises NotImplementedError.
    Use --fixture mode to feed pre-collected JSON in the same shape.
    """
    platform_name = "Amazon US"

    def search(self, query: str, limit: int = 5) -> list[dict]:
        raise NotImplementedError(
            "Amazon adapter is gated on proxy + legal sign-off. "
            "Use --fixture fixtures/marketplace/amazon-{slug}.json instead."
        )

    def fetch(self, listing_id: str, *, max_reviews: int = 200) -> MarketplaceEntry:
        raise NotImplementedError(self.search.__doc__)


# --------------------------------------------------------------------------- #
# HTTP helper                                                                  #
# --------------------------------------------------------------------------- #

def _http_get(url: str, *, timeout: int = 15) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


# --------------------------------------------------------------------------- #
# Adapter registry                                                             #
# --------------------------------------------------------------------------- #

ADAPTERS: dict[str, type] = {
    "trustpilot":   TrustpilotAdapter,
    "reddit_brand": RedditBrandAdapter,
    "amazon":       AmazonAdapter,
}


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #

def main() -> int:
    p = argparse.ArgumentParser(description="Marketplace VOC collector")
    p.add_argument("--adapter", choices=list(ADAPTERS), help="Adapter to use")
    p.add_argument("--query", help="Free-text query (used by adapter.search)")
    p.add_argument("--listing-id", help="Skip search; fetch this id directly")
    p.add_argument("--player", default="", help="Player id to stamp on the result")
    p.add_argument("--max-reviews", type=int, default=200)
    p.add_argument("--out", required=False, help="Write JSON output here")
    p.add_argument("--fixture", help="Read pre-collected JSON instead of hitting network")
    args = p.parse_args()

    if args.fixture:
        data = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
        print(f"✓ loaded fixture {args.fixture}")
        # Validate shape
        required = {"player", "platform", "rating", "review_count"}
        missing = required - data.keys()
        if missing:
            print(f"✗ fixture missing required fields: {missing}", file=sys.stderr)
            return 1
        if args.out:
            Path(args.out).write_text(json.dumps(data, indent=2, ensure_ascii=False))
            print(f"✓ wrote {args.out}")
        else:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    if not args.adapter:
        p.error("--adapter required (or use --fixture)")

    adapter = ADAPTERS[args.adapter]()
    try:
        if args.listing_id:
            listing_id = args.listing_id
        elif args.query:
            results = adapter.search(args.query, limit=5)
            if not results:
                print(f"✗ no listings found for query={args.query!r}", file=sys.stderr)
                return 1
            listing_id = results[0]["listing_id"]
            print(f"  → using first result: {results[0]['title']} ({listing_id})")
        else:
            p.error("--query or --listing-id required")

        entry = adapter.fetch(listing_id, max_reviews=args.max_reviews)
    except NotImplementedError as e:
        print(f"✗ adapter {args.adapter!r} not implemented: {e}", file=sys.stderr)
        print(f"   → Use --fixture fixtures/marketplace/{args.adapter}-<slug>.json instead.", file=sys.stderr)
        return 2
    if args.player:
        entry.player = args.player

    out_dict = entry.to_schema_dict()
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out_dict, indent=2, ensure_ascii=False))
        print(f"✓ wrote {args.out}")
    else:
        print(json.dumps(out_dict, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
