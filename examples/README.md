# Examples

The three essays in `essays/` are **made-up sample essays written with AI** for trying out Feedback Commons. They're not real students' work, so you can use them freely to test the tool before trying it on your own class.

```
python feedback_commons.py draft sample_rubric.json examples/essays --grade 8 --out drafts.json
python feedback_commons.py serve drafts.json --log events.jsonl
python feedback_commons.py summary drafts.json --log events.jsonl --rubric sample_rubric.json
python feedback_commons.py eval sample_rubric.json examples/essays --models llama3.2:3b --out eval.json
```
