#!/usr/bin/env python3
"""
סקריפט לשליפת "הטיסות הזולות ביותר מכל מקום" מטיילאביב, דרך ה-API
'Flights Scraper Sky' ב-RapidAPI (host: flights-sky.p.rapidapi.com).
"""
import json
import os
import sys
import urllib.parse
from datetime import datetime, timezone

import requests

HOST = "flights-sky.p.rapidapi.com"
ENDPOINT = f"https://{HOST}/flights/search-everywhere"
OUTPUT_FILE = "skyscanner_deals.json"

FROM_ENTITY_ID = "TLV"
PARAMS = {
    "fromEntityId": FROM_ENTITY_ID,
    "type": "oneway",
    "market": "US",
    "locale": "en-US",
    "currency": "USD",
}


def fetch_everywhere():
    api_key = os.environ.get("RAPIDAPI_KEY")
    if not api_key:
        print("שגיאה: משתנה הסביבה RAPIDAPI_KEY לא מוגדר", file=sys.stderr)
        sys.exit(1)

    headers = {
        "x-rapidapi-host": HOST,
        "x-rapidapi-key": api_key,
    }

    resp = requests.get(ENDPOINT, headers=headers, params=PARAMS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def extract_deals(raw: dict) -> list:
    deals = []
    try:
        results = (
            raw.get("data", {})
            .get("everywhereDestination", {})
            .get("results", [])
        )
    except AttributeError:
        results = []

    for item in results:
        try:
            location = item.get("content", {}).get("location", {})
            destination = location.get("name")
            sky_code = location.get("skyCode")
            price = (
                item.get("content", {})
                .get("flightQuotes", {})
                .get("cheapest", {})
                .get("rawPrice")
            )
            if destination and price:
                if sky_code:
                    url = f"https://www.skyscanner.net/transport/flights/{FROM_ENTITY_ID.lower()}/{sky_code.lower()}/"
                else:
                    query = urllib.parse.quote(f"Flights from Tel Aviv to {destination}")
                    url = f"https://www.google.com/travel/flights?q={query}"
                deals.append({
                    "destination": destination,
                    "price_usd": price,
                    "url": url,
                })
        except AttributeError:
            continue

    return deals


def main():
    try:
        raw = fetch_everywhere()
    except requests.RequestException as e:
        print(f"שגיאה בקריאה ל-API: {e}", file=sys.stderr)
        sys.exit(1)

    deals = extract_deals(raw)

    output = {
        "source": "Skyscanner (via Flights Scraper Sky API)",
        "from": FROM_ENTITY_ID,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "deals_count": len(deals),
        "deals": sorted(deals, key=lambda d: d["price_usd"]),
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    if not deals:
        with open("skyscanner_raw_debug.json", "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        print("לא נמצאו דילים - נשמר קובץ debug גולמי", file=sys.stderr)

    print(f"נשמרו {len(deals)} דילים ל-{OUTPUT_FILE}")


if __name__ == "__main__":
    main()
