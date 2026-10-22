# quote-fidelity-v3: preregistered analysis

4 cells. Analysis set: 75 essays (34 low, 41 high) completed in every cell. Dropped: low 0 not reached, 14 with an unusable reply; high 0 not reached, 7 with an unusable reply.

## Primary: exact-quote rate, low band minus high band, all cells pooled

- Low band: 480 of 534 quotes exact. High band: 577 of 637.
- Gap with 95% essay-bootstrap interval: -0.007 [-0.059, +0.039]
- Verdict (clear only if the whole interval is below zero): not clear

## Secondary 1: the same gap in each cell

- llama3.2:3b, English: +0.031 [-0.023, +0.089]
- llama3.2:3b, Spanish: -0.006 [-0.093, +0.068]
- qwen2.5:3b, English: -0.022 [-0.113, +0.075]
- qwen2.5:3b, Spanish: -0.031 [-0.146, +0.083]

## Secondary 2: edit types in altered quotes

| Band | Edit type | Edits | Quotes with one |
|---|---|---|---|
| low | spelling | 28 | 18 |
| low | apostrophe | 2 | 2 |
| low | join | 6 | 6 |
| low | split | 1 | 1 |
| low | inflection | 13 | 10 |
| low | real_word | 16 | 11 |
| low | inserted | 11 | 9 |
| low | dropped | 4 | 4 |
| low | other | 1 | 1 |
| high | spelling | 3 | 3 |
| high | apostrophe | 1 | 1 |
| high | join | 2 | 2 |
| high | split | 1 | 1 |
| high | inflection | 4 | 4 |
| high | real_word | 8 | 4 |
| high | inserted | 9 | 9 |
| high | dropped | 9 | 9 |
| high | other | 7 | 4 |
| all | spelling | 31 | 21 |
| all | apostrophe | 3 | 3 |
| all | join | 8 | 8 |
| all | split | 2 | 2 |
| all | inflection | 17 | 14 |
| all | real_word | 24 | 15 |
| all | inserted | 20 | 18 |
| all | dropped | 13 | 13 |
| all | other | 8 | 5 |

## Secondary 3: exact-quote rate by quote length (cut points [18, 32] words)

| Band | Length | Quotes | Exact |
|---|---|---|---|
| low | short | 193 | 94% |
| low | middle | 156 | 92% |
| low | long | 185 | 84% |
| high | short | 223 | 93% |
| high | middle | 238 | 91% |
| high | long | 176 | 87% |

## Secondary 4: misspelled words kept as the student wrote them, all cells

- low band: 527 of 557 (95%)
- high band: 71 of 75 (95%)
- all band: 598 of 632 (95%)

## Failures per cell

- llama3.2:3b, English: 192 requests, 18 failed, 0 unusable replies, 0 with no quote
- llama3.2:3b, Spanish: 192 requests, 1 failed, 0 unusable replies, 1 with no quote
- qwen2.5:3b, English: 192 requests, 2 failed, 0 unusable replies, 1 with no quote
- qwen2.5:3b, Spanish: 192 requests, 1 failed, 0 unusable replies, 1 with no quote
