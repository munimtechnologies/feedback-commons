# quote-fidelity-v5: preregistered analysis

4 cells. Analysis set: 91 essays (44 low, 47 high) completed in every cell. Dropped: low 0 not reached, 16 with an unusable reply; high 0 not reached, 13 with an unusable reply.

1421 quotes, 1416 with a matched passage. Excluded: 5 not in text, 0 too short, 0 labelled in the text but not placeable.

## Primary: exact-quote rate, misspelled minus clean passages, all cells pooled

- All cells: misspelled 366 of 403 exact (91%), clean 948 of 1013 (94%); gap -0.028 [-0.066, +0.011]
- Floor: at least 150 quotes of each kind.
- Verdict: no clear difference

## Secondary 1: within each Conventions band

- low band: misspelled 307 of 337 exact (91%), clean 319 of 342 (93%); gap -0.022 [-0.068, +0.024]
- high band: misspelled 59 of 66 exact (89%), clean 629 of 671 (94%); gap -0.043 [-0.157, +0.036]

## Secondary 2: each cell

- llama3.2:3b, English: misspelled 90 of 92 exact (98%), clean 250 of 261 (96%); gap +0.020 [-0.021, +0.058]
- llama3.2:3b, Spanish: misspelled 92 of 96 exact (96%), clean 257 of 266 (97%); gap -0.008 [-0.057, +0.038]
- qwen2.5:3b, English: misspelled 82 of 99 exact (83%), clean 234 of 257 (91%); gap -0.082 [-0.183, +0.009]
- qwen2.5:3b, Spanish: misspelled 102 of 116 exact (88%), clean 207 of 229 (90%); gap -0.025 [-0.110, +0.059]

## Secondary 3: misspelled passages and misspelled words kept

| Band | Matched quotes | Misspelled passages | Share | Misspelled words | Kept as written | Not kept |
|---|---|---|---|---|---|---|
| low | 679 | 337 | 50% | 779 | 756 | 23 |
| high | 737 | 66 | 9% | 83 | 80 | 3 |
| all | 1416 | 403 | 28% | 862 | 836 | 26 |

## Failures per cell

- llama3.2:3b, English: 240 requests, 24 failed, 0 unusable replies, 0 with no quote
- llama3.2:3b, Spanish: 240 requests, 5 failed, 0 unusable replies, 0 with no quote
- qwen2.5:3b, English: 240 requests, 1 failed, 0 unusable replies, 1 with no quote
- qwen2.5:3b, Spanish: 240 requests, 2 failed, 0 unusable replies, 0 with no quote
