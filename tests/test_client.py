import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from selldatatoai import DataAssetScoreClient, SellDataToAIError

RESULT = {"domain": "example-labs.com", "data_asset_score": 82, "grade": "A", "status": "active"}


class Stub(BaseHTTPRequestHandler):
    polls = 0

    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if self.headers.get("X-API-Key") != "k":
            return self._send(401, {"error": "invalid_api_key"})
        if u.path == "/v1/score":
            if q.get("domain") == ["bad"]:
                return self._send(400, {"error": "invalid_domain", "message": "Pass a domain"})
            return self._send(200, RESULT)
        if u.path == "/v1/usage":
            return self._send(200, {"plan": "pro", "remaining": 7})
        if u.path == "/v1/score/batch":
            Stub.polls += 1
            if Stub.polls < 2:
                return self._send(200, {"id": "b_1", "status": "processing", "results": []})
            return self._send(200, {"id": "b_1", "status": "done", "results": [{"input": "a.com", "status": "done", "result": RESULT}]})
        self._send(404, {"error": "unknown_endpoint"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n))
        self._send(202, {"id": "b_1", "status": "processing", "total": len(body["domains"]), "results": []})


class ClientTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), Stub)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = "http://127.0.0.1:%d/v1" % cls.srv.server_port

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_score_usage(self):
        c = DataAssetScoreClient("k", base_url=self.base)
        self.assertEqual(c.score("example-labs.com")["grade"], "A")
        self.assertEqual(c.usage()["remaining"], 7)

    def test_errors(self):
        c = DataAssetScoreClient("k", base_url=self.base)
        with self.assertRaises(SellDataToAIError) as e:
            c.score("bad")
        self.assertEqual((e.exception.status, e.exception.code), (400, "invalid_domain"))
        with self.assertRaises(SellDataToAIError) as e:
            DataAssetScoreClient("x", base_url=self.base).usage()
        self.assertEqual(e.exception.status, 401)

    def test_score_many(self):
        c = DataAssetScoreClient("k", base_url=self.base)
        items = c.score_many(["a.com"], interval=0.01)
        self.assertEqual(items[0]["result"]["data_asset_score"], 82)


if __name__ == "__main__":
    unittest.main()
