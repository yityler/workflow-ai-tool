# Output of testing-stopwords-RAG.py
**Experiment 1: "What is the current stock price of Apple and why has it moved recently?"**

| Stopwords Filtered | RAG (Search) | Input Tokens | Output Tokens | Total Tokens |
|---|---|---|---|---|
| False | False | 16 | 631 | 2158 |
| False | True  | 16 | 534 | 931  |
| True  | False | 8  | 371 | 1448 |
| True  | True  | 8  | 222 | 499  |

**Experiment 2: "What are the latest developments in AI regulation in the US?"**

| Stopwords Filtered | RAG (Search) | Input Tokens | Output Tokens | Total Tokens |
|---|---|---|---|---|
| False | False | 13 | 1643 | 2893 |
| False | True  | 13 | 1242 | 2207 |
| True  | False | 7  | 1336 | 2678 |
| True  | True  | 7  | 1071 | 1634 |


