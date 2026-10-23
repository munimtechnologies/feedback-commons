# quote-fidelity-v4: preregistered analysis

4 cells. Analysis set: 29 essays (12 low, 17 high) completed in every cell. Dropped: low 30 not reached, 18 with an unusable reply; high 30 not reached, 13 with an unusable reply.

455 quotes, 453 with a matched passage. Excluded: 2 not in text, 0 too short, 0 labelled in the text but not placeable.

## Primary: exact-quote rate, misspelled minus clean passages, all cells pooled

- All cells: misspelled 110 of 122 exact (90%), clean 314 of 331 (95%); gap -0.047 [-0.125, +0.036]
- Floor: at least 150 quotes of each kind.
- Verdict: underpowered (fewer than 150 quotes of a passage kind): the sign is not interpreted

## Secondary 1: within each Conventions band

- low band: misspelled 72 of 81 exact (89%), clean 103 of 106 (97%); gap -0.083 [-0.192, +0.014]
- high band: misspelled 38 of 41 exact (93%), clean 211 of 225 (94%); gap -0.011 [-0.092, +0.094]

## Secondary 2: each cell

- llama3.2:3b, English: misspelled 21 of 25 exact (84%), clean 84 of 90 (93%); gap -0.093 [-0.292, +0.071]
- llama3.2:3b, Spanish: misspelled 31 of 32 exact (97%), clean 77 of 82 (94%); gap +0.030 [-0.061, +0.120]
- qwen2.5:3b, English: misspelled 26 of 32 exact (81%), clean 77 of 80 (96%); gap -0.150 [-0.346, +0.036]
- qwen2.5:3b, Spanish: misspelled 32 of 33 exact (97%), clean 76 of 79 (96%); gap +0.008 [-0.077, +0.083]

## Secondary 3: misspelled passages and misspelled words kept

| Band | Matched quotes | Misspelled passages | Share | Misspelled words | Kept as written | Not kept |
|---|---|---|---|---|---|---|
| low | 187 | 81 | 43% | 205 | 177 | 28 |
| high | 266 | 41 | 15% | 51 | 49 | 2 |
| all | 453 | 122 | 27% | 256 | 226 | 30 |

## Failures per cell

- llama3.2:3b, English: 202 requests, 28 failed, 0 unusable replies, 1 with no quote
- llama3.2:3b, Spanish: 176 requests, 5 failed, 0 unusable replies, 0 with no quote
- qwen2.5:3b, English: 120 requests, 10 failed, 0 unusable replies, 1 with no quote
- qwen2.5:3b, Spanish: 192 requests, 10 failed, 0 unusable replies, 1 with no quote
