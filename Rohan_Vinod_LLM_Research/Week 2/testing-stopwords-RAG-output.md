# Output of testing-stopwords-RAG.py
**Experiment 1: "What is the current stock price of Apple and why has it moved recently?"**

| Stopwords Filtered | RAG (Search) | Input Tokens | Output Tokens | Total Tokens | Cost |
|---|---|---|---|---|---|
| False | False | 16 | 631 | 2158 | $0.005703 
| False | True  | 16 | 534 | 931  | $0.004830
| True  | False | 8  | 371 | 1448 | $0.003351
| True  | True  | 8  | 222 | 499  | $0.002010

**Experiment 2: "What are the latest developments in AI regulation in the US?"**

| Stopwords Filtered | RAG (Search) | Input Tokens | Output Tokens | Total Tokens | Cost |
|---|---|---|---|---|---|
| False | False | 13 | 1643 | 2893 | $0.0148065
| False | True  | 13 | 1242 | 2207 | $0.0111975
| True  | False | 7  | 1336 | 2678 | $0.0120345
| True  | True  | 7  | 1071 | 1634 | $0.0096495

**Experiment 3: As an AI language model, your task is to assist a renowned historian in their research on the cultural impact of the Renaissance period. The historian is particularly interested in understanding how the artistic and intellectual movements of this era influenced society and shaped future generations. Your role is to provide a detailed analysis, drawing connections between various Renaissance figures, their works, and the broader societal implications. Elaborate on the key themes and ideas that emerged during this period and their lasting legacy."**

| Stopword Removal | RAG (Search) | Input Tokens | Output Tokens | Cost |
|------------------|----------|-------------:|--------------:|-------------:| 
| False | False | 93 | 2750 | $0.0248895 | 
| False | True | 93 | 1291 | $0.0117585 |
| True | False | 55 | 2412 | $0.0217905 |
| True | True | 55 | 1247 | $0.0113055 |

| Time without stopwords | Time with stopwords |
|---------|--------|
| 18.2 s | 18.6 s |
