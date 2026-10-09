"""Client for the Data Asset Score API at https://www.selldatatoai.com/api/"""
import time

import requests

__all__ = ["DataAssetScoreClient", "SellDataToAIError", "BATCH_MAX"]

VERSION = "1.0.0"
DEFAULT_BASE = "https://www.selldatatoai.com/api/v1"
USER_AGENT = "selldatatoai-python/%s (+https://www.selldatatoai.com)" % VERSION
BATCH_MAX = 100


class SellDataToAIError(Exception):
    """Raised for any non-2xx answer. `status` is the HTTP code, `code` the API error string."""

    def __init__(self, status, code=None, message=None, body=None):
        super().__init__(message or code or "HTTP %s" % status)
        self.status = status
        self.code = code
        self.body = body


class DataAssetScoreClient:
    def __init__(self, api_key, base_url=DEFAULT_BASE, timeout=60, session=None):
        if not api_key:
            raise ValueError("An API key is required. Plans: https://www.selldatatoai.com/pricing/")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update({"X-API-Key": api_key, "User-Agent": USER_AGENT, "Accept": "application/json"})

    def _request(self, method, path, params=None, json=None):
        r = self.session.request(method, self.base_url + path, params=params, json=json, timeout=self.timeout)
        try:
            data = r.json()
        except ValueError:
            data = None
        if 200 <= r.status_code < 300 and data is not None:
            return data
        code = data.get("error") if isinstance(data, dict) else None
        msg = data.get("message") if isinstance(data, dict) else None
        raise SellDataToAIError(r.status_code, code, msg or "HTTP %s" % r.status_code, data if data is not None else r.text)

    def score(self, domain):
        """Score one company domain. Full URLs are accepted."""
        if not domain:
            raise ValueError("domain is required")
        return self._request("GET", "/score", params={"domain": str(domain).strip()})

    def submit_batch(self, domains):
        """Submit up to 100 domains; returns the batch dict (id, status, results...)."""
        domains = list(domains)
        if not domains:
            raise ValueError("domains must not be empty")
        if len(domains) > BATCH_MAX:
            raise ValueError("a batch takes at most %d domains" % BATCH_MAX)
        return self._request("POST", "/score/batch", json={"domains": domains})

    def get_batch(self, batch_id):
        """Poll a batch. Polling does not use lookups."""
        return self._request("GET", "/score/batch", params={"id": batch_id})

    def wait_for_batch(self, batch_id, interval=5, max_wait=300):
        start = time.time()
        while True:
            b = self.get_batch(batch_id)
            if b.get("status") == "done":
                return b
            if time.time() - start > max_wait:
                raise SellDataToAIError(0, "batch_timeout", "batch %s still processing after %ss" % (batch_id, max_wait), b)
            time.sleep(interval)

    def score_many(self, domains, interval=5, max_wait=300, on_batch=None):
        """Score any number of domains in batches of 100; returns result items in input order."""
        domains = list(domains)
        out = []
        for i in range(0, len(domains), BATCH_MAX):
            sent = self.submit_batch(domains[i:i + BATCH_MAX])
            done = sent if sent.get("status") == "done" else self.wait_for_batch(sent["id"], interval, max_wait)
            out.extend(done["results"])
            if on_batch:
                on_batch(done)
        return out

    def usage(self):
        """Plan, lookups used this month and lookups remaining."""
        return self._request("GET", "/usage")
