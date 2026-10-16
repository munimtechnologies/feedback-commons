"""Offline tests for the v3 runner and analysis. No model or network needed: a local stub stands in for Ollama."""

import csv
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v3_run as v3r  # noqa: E402
import v3_select as v3s  # noqa: E402


def row(i, conventions, words=200):
    text = " ".join(("alpha%d beta gamma delta epsilon" % i).split() * (words // 5))
    return {"text_id_kaggle": "E%03d" % i, "full_text": text, "Conventions": str(conventions), "grade": "9"}


ROWS = [row(i, 2.0) for i in range(40)] + [row(100 + i, 4.5) for i in range(30)] + [row(200, 3.0)]
CELLS = [("m:1", "English"), ("m:1", "Spanish"), ("m:2", "English"), ("m:2", "Spanish")]


def known(word):
    return "zzz" not in word


def write_csv(d):
    path = os.path.join(d, "train.csv")
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["text_id_kaggle", "full_text", "Conventions", "grade"])
        w.writeheader()
        w.writerows(ROWS)
    return path


def selection_for(path, per_band=8):
    chosen = v3s.select_v3(ROWS, per_band, 5, 4, 1)[1]
    return {"study": "quote-fidelity-v3", "data_sha256": v3s.sha256(path),
            "essays": [{"id": e["id"], "band": e["band"]} for e in chosen]}


def fake_ask(fail_word):
    """Low-band essays get one exact and one altered quote, high-band essays two exact ones.

    The essay whose first word is fail_word fails for model m:1 in Spanish."""
    def ask(messages, model):
        text = messages[-1]["content"].split("<<<\n", 1)[1].rsplit("\n>>>", 1)[0]
        words = text.split()
        if words[0] == fail_word and model == "m:1" and "in Spanish" in messages[-1]["content"]:
            raise v3r.RequestFailed("URLError: stub")
        second = ([words[0], words[1], "zzz"] + words[3:5]) if int(words[0][5:]) < 100 else words[1:6]
        return json.dumps({"comments": [{"quote": " ".join(q), "feed_forward": "next"}
                                        for q in (words[:5], second)]})
    return ask


class Stub(BaseHTTPRequestHandler):
    bodies, status = [], 200

    def _send(self, code, data):
        raw = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        Stub.bodies.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
        self._send(Stub.status, {"message": {"content": '{"comments": []}'}})

    def do_GET(self):
        self._send(200, {"/api/version": {"version": "0.0.1"},
                         "/api/tags": {"models": [{"name": "m:1", "digest": "abc123"}]}}[self.path])

    def log_message(self, *args):
        pass


class OllamaTests(unittest.TestCase):
    def setUp(self):
        Stub.bodies, Stub.status = [], 200
        self.server = HTTPServer(("127.0.0.1", 0), Stub)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.host = "http://127.0.0.1:%d" % self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_request_has_the_preregistered_seed_and_temperature(self):
        reply = v3r.seeded_ask(self.host)([{"role": "user", "content": "hi"}], "m:1")
        self.assertEqual(reply, '{"comments": []}')
        body = Stub.bodies[0]
        self.assertEqual(body["options"], {"temperature": 0.2, "seed": 1})
        self.assertEqual((body["format"], body["stream"], body["model"]), ("json", False, "m:1"))

    def test_server_errors_are_request_failures(self):
        Stub.status = 500
        with self.assertRaises(v3r.RequestFailed):
            v3r.seeded_ask(self.host)([{"role": "user", "content": "hi"}], "m:1")

    def test_server_info_records_digest_and_version(self):
        info = v3r.server_info(self.host, "m:1")
        self.assertEqual((info["digest"], info["ollama_version"]), ("abc123", "0.0.1"))
        self.assertIsNone(v3r.server_info(self.host, "m:9")["digest"])


class DataTests(unittest.TestCase):
    def test_wrong_sha_stops(self):
        with tempfile.TemporaryDirectory() as d:
            sel = dict(selection_for(write_csv(d)), data_sha256="0" * 64)
            with self.assertRaises(ValueError):
                v3r.load_essays(d, sel)

    def test_essays_rebuilt_in_order(self):
        with tempfile.TemporaryDirectory() as d:
            sel = selection_for(write_csv(d))
            got = v3r.load_essays(d, sel)
            self.assertEqual([e["id"] for e in got], [e["id"] for e in sel["essays"]])


def rec(essay, band, cell, criterion="x", usable=True, kinds=("exact",)):
    return {"essay": essay, "band": band, "model": cell[0], "language": cell[1], "criterion": criterion,
            "usable": usable, "comments": [{"kind": k, "quote": "a b c"} for k in kinds] if usable else []}


class AnalysisTests(unittest.TestCase):
    def test_analysis_set_reasons(self):
        sel = {"essays": [{"id": "A", "band": "low"}, {"id": "B", "band": "high"},
                          {"id": "C", "band": "low"}, {"id": "D", "band": "high"}]}
        two = CELLS[:2]
        records = ([rec("A", "low", c) for c in two] + [rec("B", "high", two[0])]
                   + [rec("C", "low", two[0]), rec("C", "low", two[1], usable=False)])
        keep, dropped = v3r.analysis_set(records, sel, ["x"])
        self.assertEqual(keep, ["A"])
        self.assertEqual(dropped, {"low": {"not_reached": 0, "unusable": 1},
                                   "high": {"not_reached": 2, "unusable": 0}})

    def test_small_bands_are_descriptive_only(self):
        sel = {"essays": [{"id": "A", "band": "low"}, {"id": "B", "band": "high"}]}
        records = [rec("A", "low", CELLS[0], kinds=("exact", "altered")), rec("B", "high", CELLS[0])]
        p = v3r.primary(records, sel, ["A", "B"])
        self.assertTrue(p["verdict"].startswith("underpowered"))
        self.assertEqual((p["low"]["exact_rate"], p["high"]["exact_rate"]), (0.5, 1.0))

    def test_length_tertiles(self):
        records = [{"band": "low", "comments": [{"kind": "exact", "quote": " ".join("w" * n)}
                                                for n in range(1, 7)]}]
        t = v3r.length_tertiles(records)
        self.assertEqual(t["cut_points_words"], [2, 4])
        self.assertEqual([r["quotes"] for r in t["rows"] if r["band"] == "low"], [2, 2, 2])


class CommandTests(unittest.TestCase):
    def test_four_cells_then_analysis(self):
        with tempfile.TemporaryDirectory() as d:
            sel = selection_for(write_csv(d))
            essays = os.path.join(d, "essays.json")
            with open(essays, "w", encoding="utf-8") as f:
                json.dump(sel, f)
            rubric = os.path.join(d, "rubric.json")
            with open(rubric, "w", encoding="utf-8") as f:
                json.dump({"criteria": [{"id": "evidence", "name": "Evidence"},
                                        {"id": "conventions", "name": "Conventions"}]}, f)
            failing = "alpha%d" % int(sel["essays"][0]["id"][1:])
            saved = (v3r.seeded_ask, v3r.server_info, v3r.MIN_PER_BAND)
            v3r.seeded_ask = lambda host=None: fake_ask(failing)
            v3r.server_info = lambda host, model: {"model": model, "digest": "d", "ollama_version": "v"}
            v3r.MIN_PER_BAND = 5
            try:
                paths = []
                for i, (model, language) in enumerate(CELLS):
                    out = os.path.join(d, "cell%d" % i)
                    v3r.main(["run", "--essays", essays, "--data-dir", d, "--out-dir", out, "--model",
                              model, "--language", language, "--rubric", rubric])
                    paths.append(os.path.join(out, "requests.jsonl"))
                v3r.main(["analyze", "--essays", essays, "--data-dir", d, "--out-dir",
                          os.path.join(d, "analysis")] + paths, known=known)
            finally:
                v3r.seeded_ask, v3r.server_info, v3r.MIN_PER_BAND = saved
            with open(os.path.join(d, "cell1", "summary.json"), encoding="utf-8") as f:
                cell = json.load(f)
            self.assertEqual(cell["meta"]["request_seed"], 1)
            self.assertEqual(cell["failures"][0]["request_failed"], 2)
            with open(os.path.join(d, "analysis", "analysis.json"), encoding="utf-8") as f:
                raw = f.read()
            s = json.loads(raw)
            self.assertEqual(s["analysis_set"]["essays"], 15)
            self.assertEqual(s["analysis_set"]["dropped"]["low"]["unusable"], 1)
            p = s["primary"]
            self.assertEqual((p["low"]["exact_rate"], p["high"]["exact_rate"]), (0.5, 1.0))
            self.assertEqual(p["exact_rate_gap"]["low_minus_high"], -0.5)
            self.assertEqual(p["verdict"], "clear")
            self.assertEqual(len(s["secondary_cells"]["gaps"]), 4)
            low_other = [t for t in s["secondary_edit_types"]["types"]
                         if (t["band"], t["type"]) == ("low", "other")][0]
            self.assertEqual(low_other["quotes"], 7 * 2 * 4)
            self.assertNotIn("alpha", raw)  # no essay text or quotes
            self.assertNotIn("beta gamma", raw)
            self.assertTrue(os.path.exists(os.path.join(d, "analysis", "analysis.md")))

    def test_run_stops_on_wrong_data(self):
        with tempfile.TemporaryDirectory() as d:
            essays = os.path.join(d, "essays.json")
            with open(essays, "w", encoding="utf-8") as f:
                json.dump(dict(selection_for(write_csv(d)), data_sha256="0" * 64), f)
            with self.assertRaises(SystemExit):
                v3r.main(["run", "--essays", essays, "--data-dir", d, "--out-dir", os.path.join(d, "o"),
                          "--model", "m:1", "--language", "English"])


if __name__ == "__main__":
    unittest.main()
