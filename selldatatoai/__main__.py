"""python -m selldatatoai score example.com | python -m selldatatoai file domains.txt out.csv | python -m selldatatoai usage

The key is read from the SDA_API_KEY environment variable.
"""
import csv
import json
import os
import sys

from .client import DataAssetScoreClient, SellDataToAIError

FIELDS = ["input", "domain", "status", "data_asset_score", "grade", "company_status", "verified_active",
          "iab_category", "country", "years_online", "pre_ai_years", "data_systems", "likely_data_assets"]


def _row(item):
    r = item.get("result") or {}
    h = r.get("history") or {}
    return {
        "input": item.get("input"), "domain": item.get("domain"), "status": item.get("status"),
        "data_asset_score": r.get("data_asset_score"), "grade": r.get("grade"), "company_status": r.get("status"),
        "verified_active": r.get("verified_active"), "iab_category": r.get("iab_category"), "country": r.get("country"),
        "years_online": h.get("years_online"), "pre_ai_years": h.get("pre_ai_years"),
        "data_systems": "; ".join(s["system"] for s in r.get("data_systems") or []),
        "likely_data_assets": "; ".join(a["label"] for a in r.get("likely_data_assets") or []),
    }


def main(argv):
    key = os.environ.get("SDA_API_KEY")
    if not key or len(argv) < 1:
        print(__doc__)
        return 2
    c = DataAssetScoreClient(key)
    try:
        if argv[0] == "score" and len(argv) > 1:
            print(json.dumps(c.score(argv[1]), indent=2))
        elif argv[0] == "usage":
            print(json.dumps(c.usage(), indent=2))
        elif argv[0] == "file" and len(argv) > 2:
            with open(argv[1], encoding="utf-8") as f:
                domains = [l.strip() for l in f if l.strip() and not l.startswith("#")]
            items = c.score_many(domains, on_batch=lambda b: print("batch %s done" % b["id"], file=sys.stderr))
            with open(argv[2], "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=FIELDS)
                w.writeheader()
                for it in items:
                    w.writerow(_row(it))
            print("wrote %d rows to %s" % (len(items), argv[2]))
        else:
            print(__doc__)
            return 2
    except SellDataToAIError as e:
        print("error %s %s: %s" % (e.status, e.code, e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


def _entry():
    sys.exit(main(sys.argv[1:]))
