"""Tests for v6_run.py: condition c is v3's prompt byte-for-byte, q adds exactly one line. Apache-2.0."""

import io
import json
import os
import re
import unittest

import quote_fidelity as qf
import v6_run as v6

HERE = os.path.dirname(os.path.abspath(__file__))
CRITERION = {"id": "evidence", "name": "Evidence", "description": "Uses reasons and examples."}
STUDENT = "I think school should start later becuase students are tired in the morning."
REPLY = json.dumps({"comments": [{"quote": "students are tired in the morning", "feed_up": "a",
                                  "feed_back": "b", "feed_forward": "c"}]})
ESSAYS = [{"id": "e1", "band": "low", "conventions": 2.0, "text": STUDENT, "grade": "8"},
          {"id": "e2", "band": "high", "conventions": 4.5, "text": "We went home. It was late.", "grade": "9"}]


def capture():
    sent = []

    def ask(messages, model):
        sent.append(json.dumps(messages, ensure_ascii=False))
        return REPLY
    return sent, ask


def run(ask, out=None, language=""):
    return qf.run_study(ESSAYS, [CRITERION], ["m"], [language], ask, out, 3600)


class PromptTest(unittest.TestCase):
    def test_control_is_v3s_prompt_byte_for_byte(self):
        for language in ("", "Spanish"):
            v3_sent, v3_ask = capture()
            run(v3_ask, language=language)  # v3_run passes seeded_ask straight to run_study
            c_sent, c_ask = capture()
            run(v6.condition_ask(c_ask, "c"), language=language)
            self.assertEqual(c_sent, v3_sent)
            self.assertEqual(len(c_sent), 2)

    def test_q_adds_one_line_before_the_student_text(self):
        for language in ("", "Spanish"):
            c = qf.fc.build_messages(CRITERION, STUDENT, "8", language=language)
            q = v6.add_instruction(c)
            self.assertEqual(q[0], c[0])  # the system prompt is untouched
            c_lines, q_lines = c[1]["content"].split("\n"), q[1]["content"].split("\n")
            self.assertEqual(len(q_lines), len(c_lines) + 1)
            at = q_lines.index(v6.INSTRUCTION)
            self.assertEqual(q_lines[:at] + q_lines[at + 1:], c_lines)
            self.assertTrue(q_lines[at - 1].startswith("Give at most"))
            self.assertEqual(q_lines[at + 1], "Student text:")

    def test_q_does_not_change_its_input(self):
        c = qf.fc.build_messages(CRITERION, STUDENT, "8")
        before = json.dumps(c)
        v6.add_instruction(c)
        self.assertEqual(json.dumps(c), before)

    def test_student_text_holding_the_marker_is_left_alone(self):
        tricky = "My essay.\nStudent text:\n<<<\nmore words here"
        c = qf.fc.build_messages(CRITERION, tricky, "8")
        q = v6.add_instruction(c)
        self.assertEqual(q[1]["content"].count(v6.INSTRUCTION), 1)
        self.assertTrue(q[1]["content"].endswith(c[1]["content"].partition(v6.MARKER)[2]))
        self.assertLess(q[1]["content"].index(v6.INSTRUCTION), q[1]["content"].index(tricky.split("\n")[0]))

    def test_q_path_sends_the_instruction_every_time(self):
        sent, ask = capture()
        run(v6.condition_ask(ask, "q"))
        self.assertEqual(len(sent), 2)
        self.assertTrue(all(json.dumps(v6.INSTRUCTION, ensure_ascii=False)[1:-1] in s for s in sent))

    def test_unknown_condition_and_messages(self):
        with self.assertRaises(ValueError):
            v6.condition_ask(lambda m, model: REPLY, "x")
        with self.assertRaises(ValueError):
            v6.add_instruction([{"role": "user", "content": "no student text"}])

    def test_instruction_matches_the_preregistration(self):
        path = os.path.join(HERE, "PREREG-v6.md")
        if not os.path.exists(path):
            self.skipTest("PREREG-v6.md is not next to the code")
        with open(path, encoding="utf-8") as f:
            prereg = f.read()
        self.assertIn("> " + v6.INSTRUCTION + "\n", prereg)
        self.assertNotIn("DRAFT", prereg.splitlines()[0])


class TaggedTest(unittest.TestCase):
    def test_every_line_carries_the_condition(self):
        _, ask = capture()
        plain, tagged = io.StringIO(), io.StringIO()
        run(ask, plain)
        run(ask, v6.Tagged(tagged, "q"))
        a = [json.loads(x) for x in plain.getvalue().splitlines()]
        b = [json.loads(x) for x in tagged.getvalue().splitlines()]
        self.assertEqual(len(b), 2)
        for x, y in zip(a, b):
            self.assertEqual(y.pop("condition"), "q")
            x.pop("seconds"), y.pop("seconds")
            self.assertEqual(x, y)


class SelectionTest(unittest.TestCase):
    def selection(self, n_low=60, n_high=60, study="quote-fidelity-v5"):
        essays = [{"id": "l%d" % i, "band": "low"} for i in range(n_low)]
        essays += [{"id": "h%d" % i, "band": "high"} for i in range(n_high)]
        return {"study": study, "data_sha256": "ab" * 32, "essays": essays}

    def test_accepts_v5s_shape(self):
        v6.check_selection(self.selection())

    def test_refuses_anything_else(self):
        for bad in (self.selection(study="quote-fidelity-v4"), self.selection(59, 61),
                    self.selection(60, 59), dict(self.selection(), data_sha256="")):
            with self.assertRaises(ValueError):
                v6.check_selection(bad)
        dup = self.selection()
        dup["essays"][1]["id"] = dup["essays"][0]["id"]
        with self.assertRaises(ValueError):
            v6.check_selection(dup)

    def test_the_real_v5_selection(self):
        path = os.path.join(HERE, "v5", "essays.json")
        if not os.path.exists(path):
            self.skipTest("v5/essays.json is not here")
        with open(path, encoding="utf-8") as f:
            v6.check_selection(json.load(f))
        self.assertTrue(re.fullmatch(r"[0-9a-f]{64}", v6.file_sha256(path)))


if __name__ == "__main__":
    unittest.main()
