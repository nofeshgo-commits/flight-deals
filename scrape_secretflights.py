#!/usr/bin/env python3
"""
סקריפט לשליפת דילי טיסות מהעמוד הציבורי של secretflights.co.il
רץ אוטומטית דרך GitHub Actions (ראה deals-workflow.yml) ושומר deals.json בריפו.
"""
import json
import re
import sys
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

URL = "https://secretflights.co.il/flight-deals/"
OUTPUT_FILE = "deals.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
}

PRICE_RE = re.compile(r"\$\s?(\d{2,5})")

STOP_WORDS = {
    "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני", "יולי", "אוגוסט",
    "ספטמבר", "אוקטובר", "נובמבר", "דצמבר", "מגוון", "חודשים",
}


def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.text


def extract_destination(text: str):
    words = text.split()
    try:
        start = next(i for i, w in enumerate(words) if w.startswith(("טיסות", "טיסה")))
    except StopIteration:
        return None

    dest_words = []
    for w in words[start + 1:]:
        if w in STOP_WORDS or w.startswith("$") or w[0].isdigit():
            break
        dest_words.append(w)
        if len(dest_words) >= 2:
            break

    if not dest_words:
        return None

    destination = " ".join(dest_words)
    if destination.startswith("ל") and len(destination) > 1:
        destination = destination[1:]
    return destination


def parse_deals(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    deals = []

    for link in soup.find_all("a", href=True):
        text = " ".join(link.get_text(separator=" ", strip=True).split())
        if "$" not in text:
            continue

        price_match = PRICE_RE.search(text)
        if not price_match:
            continue

        price = int(price_match.group(1))
        href = link["href"]
        destination = extract_destination(text)

        deals.append({
            "raw_text": text,
            "destination": destination,
            "price_usd": price,
            "url": href,
        })

    seen = set()
    unique_deals = []
    for d in deals:
        if d["url"] not in seen:
            seen.add(d["url"])
            unique_deals.append(d)

    return unique_deals


def main():
    try:
        html = fetch_html(URL)
    except requests.RequestException as e:
        print(f"שגיאה בשליפת העמוד: {e}", file=sys.stderr)
        sys.exit(1)

    deals = parse_deals(html)

    output = {
        "source": URL,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "deals_count": len(deals),
        "deals": sorted(deals, key=lambda d: d["price_usd"]),
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"נשמרו {len(deals)} דילים ל-{OUTPUT_FILE}")


if __name__ == "__main__":
    main()
