import time
from datetime import datetime
import gradio as gr
import nltk
from openai import OpenAI
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

nltk.download('stopwords')
nltk.download('punkt')
nltk.download('punkt_tab')

nvidia_client = None
github_client = None
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
GITHUB_BASE_URL = "https://models.github.ai/inference"


def set_nvidia_token(token):
    global nvidia_client
    token = (token or "").strip()
    if not token:
        nvidia_client = None
        return "No Nvidia API key"
    nvidia_client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=token, max_retries=0)
    return "Nvidia API key entered"


def set_github_token(token):
    global github_client
    token = (token or "").strip()
    if not token:
        github_client = None
        return "No Github token"
    github_client = OpenAI(base_url=GITHUB_BASE_URL, api_key=token, max_retries=0)
    return "Github token entered"


MODEL_ROUTES = {
    'meta/llama-3.1-8b-instruct': {'provider': 'nvidia', 'model_id': 'meta/llama-3.1-8b-instruct'},
    'openai/gpt-oss-20b': {'provider': 'nvidia', 'model_id': 'openai/gpt-oss-20b'},
    'microsoft/phi-4-mini-instruct': {'provider': 'github', 'model_id': 'microsoft/Phi-4-mini-instruct'},
}
MODELS = list(MODEL_ROUTES.keys())
SELECTED_MODEL = MODELS[0]
U_LOGS = ""
F_LOGS = ""


def add_log(which, message):
    global U_LOGS, F_LOGS
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message}\n"
    if which == 'u':
        U_LOGS += entry
        return U_LOGS
    else:
        F_LOGS += entry
        return F_LOGS


def change_model(model_input):
    global SELECTED_MODEL, U_LOGS, F_LOGS
    SELECTED_MODEL = model_input
    U_LOGS = ""
    F_LOGS = ""
    return [], [], "", "", ""


def remove_stopwords(text):
    stop_words = set(stopwords.words('english'))
    tokens = word_tokenize(text)
    filtered_tokens = [word for word in tokens if word.lower() not in stop_words]
    return ' '.join(filtered_tokens)


def build_messages_from_history(history):
    messages = []
    for item in history or []:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            user_msg, assistant_msg = item[0], item[1]
            if isinstance(user_msg, list) and len(user_msg) > 0:
                user_text = user_msg[0].get("text", "") if isinstance(user_msg[0], dict) else str(user_msg[0])
            else:
                user_text = str(user_msg)
            messages.append({"role": "user", "content": user_text})
            if assistant_msg is not None:
                if isinstance(assistant_msg, list) and len(assistant_msg) > 0:
                    assistant_text = assistant_msg[0].get("text", "") if isinstance(assistant_msg[0], dict) else str(assistant_msg[0])
                else:
                    assistant_text = str(assistant_msg)
                messages.append({"role": "assistant", "content": assistant_text})
    return messages


def call_api_chat(messages):
    route = MODEL_ROUTES[SELECTED_MODEL]
    if route['provider'] == 'github':
        if github_client is None:
            raise RuntimeError("No GitHub token set. Enter your token above and click Save Token.")
        active_client = github_client
    else:
        if nvidia_client is None:
            raise RuntimeError("No NVIDIA API key set. Enter your key above and click Save Token.")
        active_client = nvidia_client
    if(SELECTED_MODEL == "microsoft/phi-4-mini-instruct"):
        response = active_client.chat.completions.create(
            model=route['model_id'],
            messages=messages,
            max_tokens=256,
            temperature=0.7,
        )
    else:
        response = active_client.chat.completions.create(
            model=route['model_id'],
            messages=messages,
            max_tokens=1024,
            temperature=0.7,
        )
    return response


def chatai_unfiltered(message, history):
    try:
        messages = build_messages_from_history(history)
        messages.append({"role": "user", "content": message})
        message_tokens = len(word_tokenize(message))
        start = time.time()
        response = call_api_chat(messages)
        end = time.time()
        reply_text = response.choices[0].message.content or "(model returned no content — likely ran out of token budget while reasoning; try increasing max_tokens)"
        resp_text = str(response)
        response_tokens = len(word_tokenize(reply_text))
        logs = add_log('u', f"User: {message} ({message_tokens} tokens) -> Response: {resp_text} ({response_tokens} tokens, took {end-start:.2f}s)")
        return reply_text, logs
    except Exception as e:
        return f"Error: {str(e)}", U_LOGS


def chatai_filtered(message, history):
    try:
        filtered = remove_stopwords(message)
        original_tokens = len(word_tokenize(message))
        filtered_tokens = len(word_tokenize(filtered))
        messages = build_messages_from_history(history)
        messages.append({"role": "user", "content": filtered})
        start = time.time()
        response = call_api_chat(messages)
        end = time.time()
        reply_text = response.choices[0].message.content or "(model returned no content — likely ran out of token bud   while reasoning; try increasing max_tokens)"
        resp_text = str(response)
        response_tokens = len(word_tokenize(reply_text))
        logs = add_log('f', f"Original: {message} ({original_tokens} tokens) | Filtered: {filtered} ({filtered_tokens} tokens) -> Response: {resp_text} ({response_tokens} tokens, took {end-start:.2f}s)")
        return reply_text, logs
    except Exception as e:
        return f"Error: {str(e)}", F_LOGS


def send_to_both(message, u_history, f_history):
    if message is None or str(message).strip() == "":
        return u_history or [], f_history or [], U_LOGS, F_LOGS, ""

    u_response, _ = chatai_unfiltered(message, u_history)
    f_response, _ = chatai_filtered(message, f_history)

    u_history = (u_history or []) + [{"role": "user", "content": message}, {"role": "assistant", "content": u_response}]
    f_history = (f_history or []) + [{"role": "user", "content": message}, {"role": "assistant", "content": f_response}]
    return u_history, f_history, U_LOGS, F_LOGS, ""


with gr.Blocks() as demo:
    title = gr.Markdown("# AI Chatbot (NVIDIA NIM + GitHub Models)")

    with gr.Row():
        nvidia_token_input = gr.Textbox(
            label="NVIDIA API Key (Llama 3.1, gpt-oss-20b)",
            placeholder="nvapi-xxxxxxxxxxxxxxxxxxxx",
            type="password",
            interactive=True,
            scale=4,
        )
        save_nvidia_button = gr.Button("Save", scale=1)
    nvidia_token_status = gr.Markdown("Enter a Nvidia API token")

    with gr.Row():
        github_token_input = gr.Textbox(
            label="GitHub Token (Phi-4-mini-instruct)",
            placeholder="github_pat_xxxxxxxxxxxxxxxxxxxx",
            type="password",
            interactive=True,
            scale=4,
        )
        save_github_button = gr.Button("Save", scale=1)
    github_token_status = gr.Markdown("Enter a Github PAT token")

    model = gr.Dropdown(
        label="Model",
        choices=MODELS,
        value=SELECTED_MODEL,
        interactive=True,
    )

    user_input = gr.Textbox(label="Input", interactive=True, lines=2)
    send_button = gr.Button("Send")
    with gr.Row():
        with gr.Column():
            u_logs = gr.Textbox(label="Unfiltered Logs", interactive=False, lines=20)
            u_chatbot = gr.Chatbot(label="Unfiltered AI")

        with gr.Column():
            f_logs = gr.Textbox(label="Filtered Logs", interactive=False, lines=20)
            f_chatbot = gr.Chatbot(label="Filtered AI")

    save_nvidia_button.click(
        fn=set_nvidia_token,
        inputs=[nvidia_token_input],
        outputs=[nvidia_token_status],
    )

    save_github_button.click(
        fn=set_github_token,
        inputs=[github_token_input],
        outputs=[github_token_status],
    )

    send_button.click(
        fn=send_to_both,
        inputs=[user_input, u_chatbot, f_chatbot],
        outputs=[u_chatbot, f_chatbot, u_logs, f_logs, user_input],
    )

    model.change(fn=change_model, inputs=model, outputs=[u_chatbot, f_chatbot, u_logs, f_logs, user_input])


demo.launch(share=True)