# quote-fidelity-v6: preregistered analysis

4 model x language cells, each run without (c) and with (q) the quote-exactly instruction. Analysis set: 63 essays (32 low, 31 high) completed in all 8 runs. Dropped: low 4 not reached, 24 with an unusable reply; high 5 not reached, 24 with an unusable reply.

Without the instruction (c): 980 quotes, 979 with a matched passage. Excluded: 1 not in text, 0 too short, 0 labelled in the text but not placeable.
With the instruction (q): 963 quotes, 962 with a matched passage. Excluded: 1 not in text, 0 too short, 0 labelled in the text but not placeable.

## Primary: exact-quote rate, with minus without the instruction, all cells pooled

- All cells: with the instruction 905 of 962 exact (94%), without 923 of 979 (94%); gap -0.002 [-0.027, +0.022]
- Floor: at least 300 matched quotes in each condition.
- Verdict: no clear effect

## Secondary 1: within each Conventions band

- low band: with the instruction 457 of 489 exact (94%), without 455 of 493 (92%); gap +0.012 [-0.027, +0.047]
- high band: with the instruction 448 of 473 exact (95%), without 468 of 486 (96%); gap -0.016 [-0.046, +0.014]

## Secondary 2: each model x language cell

- llama3.2:3b, English: with the instruction 236 of 239 exact (99%), without 238 of 245 (97%); gap +0.016 [-0.001, +0.036]
- llama3.2:3b, Spanish: with the instruction 251 of 254 exact (99%), without 249 of 251 (99%); gap -0.004 [-0.020, +0.012]
- qwen2.5:3b, English: with the instruction 217 of 241 exact (90%), without 221 of 245 (90%); gap -0.002 [-0.057, +0.053]
- qwen2.5:3b, Spanish: with the instruction 201 of 228 exact (88%), without 215 of 238 (90%); gap -0.022 [-0.087, +0.042]

## Secondary 3: every quote's label, by condition

| Label | Without: quotes | Without: share | With: quotes | With: share |
|---|---|---|---|---|
| Exact | 923 | 94% | 905 | 94% |
| Same words | 22 | 2% | 28 | 3% |
| Changed words | 34 | 4% | 29 | 3% |
| Not found | 1 | 0% | 1 | 0% |
| Too short | 0 | 0% | 0 | 0% |

## Secondary 4: how much the models quote

| Condition | Usable replies | Quotes | Per reply | Matched per reply | Replies with no quote |
|---|---|---|---|---|---|
| Without | 504 | 980 | 1.944 | 1.942 | 0 |
| With | 504 | 963 | 1.911 | 1.909 | 4 |

## Secondary 5: misspelled words kept as the student wrote them

| Condition | Band | Matched quotes | Misspelled words | Kept as written | Not kept | Kept rate |
|---|---|---|---|---|---|---|
| Without | low | 493 | 675 | 659 | 16 | 98% |
| Without | high | 486 | 21 | 21 | 0 | 100% |
| Without | all | 979 | 696 | 680 | 16 | 98% |
| With | low | 489 | 704 | 697 | 7 | 99% |
| With | high | 473 | 22 | 22 | 0 | 100% |
| With | all | 962 | 726 | 719 | 7 | 99% |

## Failures per run

- llama3.2:3b, English/c: 240 requests, 24 failed, 0 unusable replies, 0 with no quote
- llama3.2:3b, English/q: 240 requests, 23 failed, 0 unusable replies, 0 with no quote
- llama3.2:3b, Spanish/c: 234 requests, 4 failed, 0 unusable replies, 0 with no quote
- llama3.2:3b, Spanish/q: 240 requests, 4 failed, 0 unusable replies, 0 with no quote
- qwen2.5:3b, English/c: 222 requests, 5 failed, 0 unusable replies, 0 with no quote
- qwen2.5:3b, English/q: 240 requests, 4 failed, 0 unusable replies, 2 with no quote
- qwen2.5:3b, Spanish/c: 240 requests, 4 failed, 0 unusable replies, 0 with no quote
- qwen2.5:3b, Spanish/q: 236 requests, 7 failed, 0 unusable replies, 4 with no quote
