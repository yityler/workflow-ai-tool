import gradio as gr
from dotenv import load_dotenv
import os
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from google import genai
from google.genai import types


load_dotenv()
nltk.download('stopwords')
nltk.download('punkt')
nltk.download('punkt_tab')

# Creates Gemini Client using API Key
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Sets common stopwords of English language like "the," "is," "and"
stop_words = set(stopwords.words('english'))

# Google Search Grounding (RAG): retrieves relevant context from the web and passes it to LLM
google_search_tool = types.Tool(google_search=types.GoogleSearch())


def ask_gemini(question):
    tokens = word_tokenize(question.lower())
    filtered_tokens = [word for word in tokens if word not in stop_words]
    filtered_question = " ".join(filtered_tokens)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=filtered_question,
        config = types.GenerateContentConfig(
            tools=[google_search_tool]
        )
    )

    # collects response data for input/output token display
    usage = response.usage_metadata
    token_info = (
        f"**Input tokens:** {usage.prompt_token_count}  \n"
        f"**Output tokens:** {usage.candidates_token_count}  \n"
    )

    return response.text, token_info


demo = gr.Interface(
    fn=ask_gemini,
    inputs=gr.Textbox(label="Ask anything", placeholder="Type your question here..."),
    outputs=
    [
        gr.Textbox(label="Gemini's Response"),
        gr.Markdown(label="Token Usage")
    ],
    title="Gemini AI",
)

demo.launch()
