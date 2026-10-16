# Exploratory: quote fidelity where there are misspellings to fix

Declared before results (see README.md). 337 quotes, 335 of them placed in the essay. A passage counts as misspelled when pyspellchecker does not know at least one of its words.

| Model | Language | Band | Passage | Quotes | Verbatim |
|---|---|---|---|---|---|
| llama3.2:3b | English | low | misspelled | 15 | 100% |
| llama3.2:3b | English | low | clean | 28 | 93% |
| llama3.2:3b | English | high | misspelled | 5 | 80% |
| llama3.2:3b | English | high | clean | 39 | 100% |
| llama3.2:3b | English | all | misspelled | 20 | 95% |
| llama3.2:3b | English | all | clean | 67 | 97% |
| llama3.2:3b | Spanish | low | misspelled | 12 | 92% |
| llama3.2:3b | Spanish | low | clean | 32 | 97% |
| llama3.2:3b | Spanish | high | misspelled | 5 | 80% |
| llama3.2:3b | Spanish | high | clean | 39 | 100% |
| llama3.2:3b | Spanish | all | misspelled | 17 | 88% |
| llama3.2:3b | Spanish | all | clean | 71 | 99% |
| qwen2.5:3b | English | low | misspelled | 15 | 93% |
| qwen2.5:3b | English | low | clean | 22 | 96% |
| qwen2.5:3b | English | high | misspelled | 5 | 100% |
| qwen2.5:3b | English | high | clean | 39 | 100% |
| qwen2.5:3b | English | all | misspelled | 20 | 95% |
| qwen2.5:3b | English | all | clean | 61 | 98% |
| qwen2.5:3b | Spanish | low | misspelled | 17 | 100% |
| qwen2.5:3b | Spanish | low | clean | 22 | 100% |
| qwen2.5:3b | Spanish | high | misspelled | 7 | 100% |
| qwen2.5:3b | Spanish | high | clean | 33 | 100% |
| qwen2.5:3b | Spanish | all | misspelled | 24 | 100% |
| qwen2.5:3b | Spanish | all | clean | 55 | 100% |

## Verbatim rate, misspelled minus clean passages (95% essay bootstrap)

- llama3.2:3b, English: -0.020 [-0.152, +0.066]
- llama3.2:3b, Spanish: -0.104 [-0.272, +0.027]
- qwen2.5:3b, English: -0.034 [-0.167, +0.048]
- qwen2.5:3b, Spanish: +0.000 [+0.000, +0.000]

## Misspelled words the quote kept as the student wrote them

- llama3.2:3b, English, low band: 41 of 41 (100%)
- llama3.2:3b, English, high band: 5 of 6 (83%)
- llama3.2:3b, English, all band: 46 of 47 (98%)
- llama3.2:3b, Spanish, low band: 23 of 23 (100%)
- llama3.2:3b, Spanish, high band: 5 of 6 (83%)
- llama3.2:3b, Spanish, all band: 28 of 29 (97%)
- qwen2.5:3b, English, low band: 28 of 31 (90%)
- qwen2.5:3b, English, high band: 5 of 5 (100%)
- qwen2.5:3b, English, all band: 33 of 36 (92%)
- qwen2.5:3b, Spanish, low band: 52 of 52 (100%)
- qwen2.5:3b, Spanish, high band: 8 of 8 (100%)
- qwen2.5:3b, Spanish, all band: 60 of 60 (100%)

## Words the spell checker does not know, mean share per essay

- high band: 11 essays, 0.8%
- low band: 11 essays, 2.8%
