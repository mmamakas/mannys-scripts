#!/usr/bin/env python3
"""Enrich NYC building addresses with HPD Building ID and Violation Count.

Reads a TSV or CSV of buildings and appends two columns by querying NYC Open Data:
  - HPD Building ID        (HPD Registrations dataset, tesw-yqqr)
  - HPD Violation Count    (HPD Violations dataset, csn4-vhvf)

Non-NYC addresses (e.g. Yonkers, New Rochelle) are skipped and left blank.

Usage:
    python3 enrich_hpd.py input.tsv output.csv
    python3 enrich_hpd.py input.csv output.csv --delimiter ,

Requires Python 3.8+ (stdlib only). No API key needed, but setting an app
token via the NYC_APP_TOKEN env var raises the rate limit.
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

REG_URL = "https://data.cityofnewyork.us/resource/tesw-yqqr.json"
VIO_URL = "https://data.cityofnewyork.us/resource/csn4-vhvf.json"

BOROUGHS = {
    "manhattan": 1,
    "new york": 1,
    "ny": 1,
    "bronx": 2,
    "brooklyn": 3,
    "queens": 4,
    "astoria": 4,
    "long island city": 4,
    "flushing": 4,
    "jamaica": 4,
    "rockaway beach": 4,
    "staten island": 5,
}

STREET_ABBREV = {
    "AVENUE": "AVE", "AVE.": "AVE",
    "STREET": "ST", "ST.": "ST",
    "ROAD": "RD", "RD.": "RD",
    "PLACE": "PL", "PL.": "PL",
    "DRIVE": "DR", "DR.": "DR",
    "BOULEVARD": "BLVD", "BLVD.": "BLVD",
    "PARKWAY": "PKWY", "PKWY.": "PKWY",
    "TERRACE": "TER", "TER.": "TER",
    "LANE": "LN", "LN.": "LN",
    "COURT": "CT", "CT.": "CT",
    "HIGHWAY": "HWY",
    "EXPRESSWAY": "EXPY", "EXPWY": "EXPY",
    "TURNPIKE": "TPKE", "TPKE.": "TPKE",
    "CRESCENT": "CRES",
    "NORTH": "N",
    "SOUTH": "S",
    "EAST": "E",
    "WEST": "W",
}

ORDINAL_RE = re.compile(r"\b(\d+)(ST|ND|RD|TH)\b", re.IGNORECASE)


def normalize_street(s: str) -> str:
    s = s.upper().strip()
    s = ORDINAL_RE.sub(r"\1", s)
    return " ".join(STREET_ABBREV.get(w, w) for w in re.split(r"\s+", s))


def parse_address(addr: str):
    m = re.match(r"^\s*(\S+)\s+(.+?)\s*$", addr)
    if not m:
        return None, None
    return m.group(1).upper(), normalize_street(m.group(2))


def soda_get(url: str, params: dict):
    token = os.environ.get("NYC_APP_TOKEN")
    if token:
        params = {**params, "$$app_token": token}
    full = f"{url}?{urlencode(params)}"
    req = Request(full, headers={
        "Accept": "application/json",
        "User-Agent": "nyc-hpd-enrich/1.0",
    })
    with urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def soql_escape(v: str) -> str:
    return v.replace("'", "''")


def find_building_id(house: str, street: str, boroid: int, zip_code: str):
    # Exact match first
    try:
        data = soda_get(REG_URL, {
            "$select": "buildingid,housenumber,streetname,boroid,zip",
            "$where": (
                f"housenumber='{soql_escape(house)}' AND "
                f"upper(streetname)='{soql_escape(street)}' AND "
                f"boroid='{boroid}'"
            ),
            "$limit": "5",
        })
        if data:
            return data[0].get("buildingid")
    except Exception as e:
        print(f"    registrations error: {e}", file=sys.stderr)

    # Fallback: zip + street, then match by low/high range
    if not zip_code:
        return None
    try:
        data = soda_get(REG_URL, {
            "$select": "buildingid,housenumber,lowhousenumber,highhousenumber,streetname,zip",
            "$where": f"upper(streetname)='{soql_escape(street)}' AND zip='{soql_escape(zip_code)}'",
            "$limit": "100",
        })
    except Exception as e:
        print(f"    registrations fallback error: {e}", file=sys.stderr)
        return None

    if not data:
        return None
    for r in data:
        if (r.get("housenumber") or "").upper() == house:
            return r.get("buildingid")

    def num(s):
        digits = re.sub(r"\D", "", (s or "").split("-")[-1])
        return int(digits) if digits else None

    h = num(house)
    if h is None:
        return None
    for r in data:
        lo, hi = num(r.get("lowhousenumber")), num(r.get("highhousenumber"))
        if lo is not None and hi is not None and lo <= h <= hi:
            return r.get("buildingid")
    return None


def count_violations(building_id):
    try:
        data = soda_get(VIO_URL, {
            "$select": "count(*) AS cnt",
            "$where": f"buildingid='{soql_escape(str(building_id))}'",
        })
        if data:
            return int(data[0].get("cnt", 0))
    except Exception as e:
        print(f"    violations error: {e}", file=sys.stderr)
    return None


def resolve_boroid(city: str, zip_code: str):
    if city and city.lower() in BOROUGHS:
        return BOROUGHS[city.lower()]
    if zip_code:
        z = zip_code[:5]
        if z.startswith("100") or z.startswith("101") or z.startswith("102"):
            return 1
        if z.startswith("104"):
            return 2
        if z.startswith("112"):
            return 3
        if z.startswith("113") or z.startswith("114") or z.startswith("116"):
            return 4
        if z.startswith("103"):
            return 5
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--delimiter", default="\t", help="Input delimiter (default: tab)")
    ap.add_argument("--sleep", type=float, default=0.2, help="Seconds between requests")
    ap.add_argument("--street-col", default="Building Street")
    ap.add_argument("--city-col", default="Building City")
    ap.add_argument("--zip-col", default="Building Zip")
    args = ap.parse_args()

    with open(args.input, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=args.delimiter)
        reader.fieldnames = [fn.strip() for fn in reader.fieldnames]
        rows = list(reader)
        fieldnames = list(reader.fieldnames) + ["HPD Building ID", "HPD Violation Count"]

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i, row in enumerate(rows, 1):
            row = {k.strip() if isinstance(k, str) else k: (v or "").strip() for k, v in row.items()}
            street_raw = row.get(args.street_col, "")
            city = row.get(args.city_col, "")
            zip_code = row.get(args.zip_col, "").split("-")[0]

            boroid = resolve_boroid(city, zip_code)
            bid, vcount = "", ""
            label = f"[{i}/{len(rows)}] {street_raw}, {city} {zip_code}"
            if not boroid:
                print(f"{label}  SKIP (not NYC)")
            else:
                house, street = parse_address(street_raw)
                if house and street:
                    print(label)
                    b = find_building_id(house, street, boroid, zip_code)
                    if b:
                        bid = b
                        c = count_violations(b)
                        vcount = c if c is not None else ""
                        print(f"    -> BID={bid}, violations={vcount}")
                    else:
                        print(f"    -> BID not found")
                    time.sleep(args.sleep)
                else:
                    print(f"{label}  SKIP (unparseable address)")

            row["HPD Building ID"] = bid
            row["HPD Violation Count"] = vcount
            writer.writerow(row)

    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
