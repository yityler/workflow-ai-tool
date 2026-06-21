import os
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from google import genai
from google.genai import types
from dotenv import load_dotenv
import pandas as pd

load_dotenv()
nltk.download('stopwords')
nltk.download('punkt')
nltk.download('punkt_tab')

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
stop_words = set(stopwords.words('english'))
google_search_tool = types.Tool(google_search=types.GoogleSearch())

def filter_stopwords(question):
    tokens = word_tokenize(question.lower())
    filtered = [w for w in tokens if w not in stop_words]
    return " ".join(filtered)

def run_test(question, use_stopword_filter, use_rag):
    text = filter_stopwords(question) if use_stopword_filter else question

    config_kwargs = {}
    if use_rag:
        config_kwargs["tools"] = [google_search_tool]

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=text,
        config=types.GenerateContentConfig(**config_kwargs)
    )

    usage = response.usage_metadata
    return {
        "Stopwords Filtered": use_stopword_filter,
        "RAG (Search)": use_rag,
        "Input Tokens": usage.prompt_token_count,
        "Tool/Search Tokens": getattr(usage, "tool_use_prompt_token_count", 0) or 0,
        "Output Tokens": usage.candidates_token_count,
        "Total Tokens": usage.total_token_count,
        "Sent Text": text
    }

questions = [
    "What is the current stock price of Apple and why has it moved recently?",
    "What are the latest developments in AI regulation in the US?"
]

results = []

for q in questions:
    for use_stopwords in [False, True]:
        for use_rag in [False, True]:
            print(f"Running: '{q[:30]}...' | stopwords={use_stopwords} | rag={use_rag}")
            results.append(run_test(q, use_stopwords, use_rag))

df = pd.DataFrame(results)
print(df.to_string(index=False))
df.to_csv("token_comparison.csv", index=False)
