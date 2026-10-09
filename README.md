# selldatatoai for Python

`selldatatoai` scores companies for AI data deals from Python. You pass a website; the API answers with a 0 to 100 [Data Asset Score](https://www.selldatatoai.com/data-asset-score/), a grade, the data the company likely holds and how long it has been online.

```bash
pip install selldatatoai
```

Requires Python 3.7 or newer and `requests`. The package also installs a `selldatatoai` command for scoring a text file of domains into a CSV.

The service behind it is [selldatatoai.com](https://www.selldatatoai.com/), which keeps an index of 102 million domains, 99.99% of the active internet, together with each domain's history.

## Who this is for

- **Data brokers** who source data partners for AI labs and need to know which companies are worth a call.
- **Data companies** that resell records and want to rank prospects by the data they hold.
- **Referral partners** in data programs who screen companies before they introduce them.
- **Analysts** who study which sectors hold the operational records that AI training buys.

If you are new to the trade itself, the step-by-step guide on [how to sell data to AI companies](https://www.selldatatoai.com/how-to-sell-data-to-ai-companies/) covers the deal from first contact to delivery.

## Five lines to a score

```python
import os
from selldatatoai import DataAssetScoreClient

client = DataAssetScoreClient(os.environ["SDA_API_KEY"])
s = client.score("example.com")
print(s["data_asset_score"], s["grade"], [a["label"] for a in s["likely_data_assets"]])
```

The result is a plain `dict` with the API field names. A trimmed real answer looks like this:

```json
{
  "domain": "promega.com",
  "data_asset_score": 88,
  "grade": "A",
  "status": "active",
  "verified_active": true,
  "iab_category": "Business and Finance > Industries > Pharmaceutical Industry",
  "country": "United States",
  "history": {"first_seen_year": 1993, "years_online": 33, "founded_year": null, "pre_ai_years": 30},
  "pre_ai_archive_likely": true,
  "data_systems": [
    {"system": "Jira / Confluence", "data_type": "Work tickets and internal wiki", "type": "work_tickets"},
    {"system": "Webex", "data_type": "Calls and meetings", "type": "calls"}
  ],
  "likely_data_assets": [
    {"type": "support_tickets", "label": "Support tickets and chat transcripts"},
    {"type": "knowledge_base", "label": "Knowledge base, SOPs and documentation"}
  ],
  "data_coverage": "full",
  "cached": true
}
```

## API surface

| Python call | Endpoint | Cost |
|---|---|---|
| `client.score(domain)` | `GET /api/v1/score` | 1 lookup |
| `client.submit_batch(domains)` | `POST /api/v1/score/batch` | 1 lookup per valid, unique domain |
| `client.get_batch(batch_id)` | `GET /api/v1/score/batch?id=` | free |
| `client.wait_for_batch(batch_id, interval=5, max_wait=300)` | polls `get_batch` | free |
| `client.score_many(domains, interval=5, max_wait=300, on_batch=None)` | batches of 100 | 1 lookup per valid, unique domain |
| `client.usage()` | `GET /api/v1/usage` | free |

Constructor:

```python
DataAssetScoreClient(api_key, base_url="https://www.selldatatoai.com/api/v1", timeout=60, session=None)
```

Pass your own `requests.Session` if you need retries, a proxy or connection pooling shared with other code. The key travels in the `X-API-Key` header only.

Every field is described in the [REST API reference](https://www.selldatatoai.com/api/).

## Handling failures

All HTTP errors raise `SellDataToAIError`. It carries `.status` (HTTP code), `.code` (the API error string) and `.body` (the decoded answer).

```python
from selldatatoai import SellDataToAIError

def safe_score(client, domain):
    try:
        return client.score(domain)
    except SellDataToAIError as e:
        if e.code == "invalid_domain":
            return None                      # bad input, skip it
        if e.code == "monthly_limit_reached":
            raise SystemExit("Out of lookups until the 1st (UTC)")
        raise                                # 401, network trouble, anything else
```

Codes you can meet:

- `missing_api_key`, `invalid_api_key` (401): no key, or the plan is not active.
- `invalid_domain` (400): not a valid domain.
- `no_domains`, `too_many_domains` (400): a batch needs 1 to 100 entries.
- `monthly_limit_reached` (429): limits reset on the first day of each month, UTC.
- `batch_busy` (429): three of your batches are still open.
- `batch_not_found` (404): unknown id, or older than 7 days.
- `not_available` (410): company lists are not served by the API.

## Recipes

### Recipe 1: score a spreadsheet with pandas

```python
import os
import pandas as pd
from selldatatoai import DataAssetScoreClient

client = DataAssetScoreClient(os.environ["SDA_API_KEY"])
df = pd.read_csv("prospects.csv")                    # needs a 'website' column

items = client.score_many(df["website"].dropna().tolist())
rows = []
for it in items:
    r = it.get("result") or {}
    rows.append({
        "website": it["input"],
        "score": r.get("data_asset_score"),
        "grade": r.get("grade"),
        "status": r.get("status", it["status"]),
        "pre_ai_years": (r.get("history") or {}).get("pre_ai_years"),
        "systems": ", ".join(s["system"] for s in r.get("data_systems", [])),
    })

scored = df.merge(pd.DataFrame(rows), on="website", how="left")
scored.sort_values("score", ascending=False).to_csv("prospects_scored.csv", index=False)
```

### Recipe 2: a FastAPI route for a partner form

```python
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from selldatatoai import DataAssetScoreClient, SellDataToAIError

app = FastAPI()
sda = DataAssetScoreClient(os.environ["SDA_API_KEY"])

class Signup(BaseModel):
    company: str
    website: str

@app.post("/signup")
def signup(body: Signup):
    try:
        s = sda.score(body.website)
    except SellDataToAIError as e:
        if e.status == 400:
            raise HTTPException(422, "That website does not look valid")
        raise HTTPException(503, "Scoring is unavailable, try again shortly")
    tier = "priority" if s["grade"] in ("A", "B") and s["verified_active"] else "standard"
    return {"company": body.company, "tier": tier, "score": s["data_asset_score"]}
```

The client is synchronous. Inside an async framework, FastAPI runs plain `def` routes in a thread pool, which is what you want here.

### Recipe 3: parallel single lookups with a thread pool

Batches are the better tool for big lists. For a few dozen domains where you want each answer as soon as it is ready, a small pool works well:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

domains = ["example-one.com", "example-two.com", "example-three.com"]
with ThreadPoolExecutor(max_workers=4) as pool:
    futures = {pool.submit(client.score, d): d for d in domains}
    for f in as_completed(futures):
        d = futures[f]
        try:
            print(d, f.result()["data_asset_score"])
        except SellDataToAIError as e:
            print(d, "failed:", e.code)
```

Keep the pool small. Each worker is one open request, and every call still counts against your monthly lookups.

### Recipe 4: the command line

```bash
export SDA_API_KEY=xxxx
selldatatoai score example.com          # JSON for one company
selldatatoai usage                      # plan and remaining lookups
selldatatoai file domains.txt out.csv   # one domain per line, '#' lines skipped
```

`python -m selldatatoai` works the same way if the script directory is not on your `PATH`. The CSV has one row per input line, in input order, with score, grade, company status, years online, pre-AI years, systems and likely data assets.

## How batches behave

1. You send up to 100 domains.
2. Lookups are charged right away: one per valid, unique domain.
3. Domains scored in the last 30 days are `done` in the first answer.
4. The rest finish in the background, usually within a minute.
5. You poll with the batch id. Polling is free.
6. Results stay in the order you sent and are kept for 7 days.

You can hold three open batches per key. `score_many` sends them one after another, so it never trips that limit.

## Making sense of the numbers

The score gathers several factor groups into one number. The [how the Data Asset Score works](https://www.selldatatoai.com/how-the-data-asset-score-works/) page describes the data behind each group. The exact weights are not published.

A few reading tips:

- **Grade first, score second.** Two companies at 71 and 74 are in the same band. A and B grades are where most buyers start.
- **Check `status`.** A high score on a `winding_down_or_acquired` company means the records may still exist, but the seller has changed.
- **Look at `pre_ai_years`.** Records written before 2023 are free of AI-generated text, which some buyers value highly.
- **Read `data_coverage`.** `limited` means fewer signals were available, so the score is less certain.

Sector context helps too. Life sciences companies tend to hold lab, study and R&D records, which is why buyers of [AI training data companies](https://www.selldatatoai.com/ai-training-data-companies/) research often start with that sector. A ready file of the top 3,000 US firms in that space is described on the [list of biotech companies](https://www.selldatatoai.com/list-of-biotech-companies/) page.

## Grouping companies by the data they hold

Buyers rarely ask for "data". They ask for a type: support conversations, engineering tickets, recorded calls, contracts, design files. The `type` keys in `data_systems` and `likely_data_assets` let you build those groups in a few lines.

```python
from collections import defaultdict

by_type = defaultdict(list)
for it in items:                                   # items from score_many()
    r = it.get("result")
    if not r or not r["verified_active"]:
        continue
    for a in r["likely_data_assets"]:
        by_type[a["type"]].append((r["data_asset_score"], r["domain"]))

for t, rows in sorted(by_type.items()):
    top = sorted(rows, reverse=True)[:10]
    print(t, len(rows), "companies, top:", ", ".join(d for _, d in top))
```

Two keys deserve a note:

- `data_systems` lists systems the company is seen to run, each mapped to the data type it stores. It is the stronger signal, because a running system means the records exist and can be exported.
- `likely_data_assets` lists what the company probably holds based on its sector and footprint. Use it to widen a search, not to promise a buyer anything.

When a buyer asks for one data type across a whole market, the website also sells ready lists by data type next to the sector lists.

## Plans

Paid plans only, from $99 a month: Basic $99 for 5,000 lookups, Pro $299 for 25,000 with batch scoring, Scale $799 for 100,000 with batch scoring. The website demo allows 5 checks a day if you want to see the output before you subscribe. Your key appears in your dashboard as soon as the payment completes.

Company lists are not part of any API plan. They are one-time files of the top 3,000 US companies per sector, from $249 a list, delivered by email links that work for 30 days.

## FAQ

### What does the selldatatoai package do?

The selldatatoai package is the Python client for the Data Asset Score API at selldatatoai.com. It scores a company website from 0 to 100 for the data AI buyers want and returns the grade, status, data systems, likely data assets and web history.

### Does it support asyncio?

Not directly. Run calls in a thread pool (`asyncio.to_thread` on Python 3.9+) or use the batch endpoint, which does the parallel work on the server.

### What counts as a lookup?

Each scored domain, fresh or cached. A batch counts each valid, unique domain once. Usage and polling calls are free.

### Can I pass full URLs?

Yes. `https://www.example.com/contact` and `example.com` score the same company.

### Are results stored?

A result is reused for 30 days, then the domain is scored again. Batches are deleted after 7 days.

### Is there a sandbox key?

No. Plans are paid, and the demo on the website is the only free access.

## Links

- Homepage: https://www.selldatatoai.com/
- Source code: https://github.com/explainableaixai/selldatatoai-python
- Python packaging guide: [packaging.python.org](https://packaging.python.org/en/latest/tutorials/installing-packages/)
- Thread pools in the standard library: [docs.python.org](https://docs.python.org/3/library/concurrent.futures.html)

## License

MIT, Copyright (c) 2026 Alpha Quantum. Questions: info@alpha-quantum.com
