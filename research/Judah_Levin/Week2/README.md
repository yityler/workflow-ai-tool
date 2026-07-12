# Prompt Sifter

A Gradio interface that removes conversational filler from prompt boundaries, sends the cleaned prompt to DeepSeek, ChatGPT models through the OpenAI API, or Gemini, and displays actual input/output token usage with USD cost estimates.

The request settings let you choose an AI provider and model for every prompt:

- DeepSeek: V4 Flash, V4 Pro, Chat, or Reasoner
- ChatGPT / OpenAI: GPT-5.5, GPT-5.4, or GPT-5.4 mini
- Gemini: Gemini 3.5 Flash or Gemini 3.1 Flash-Lite

Local website: [http://127.0.0.1:7860](http://127.0.0.1:7860)

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Once the app is running, open [http://127.0.0.1:7860](http://127.0.0.1:7860) in your browser.

Keep that Terminal window open while using the site. Press `Ctrl+C` in Terminal to stop the server.

## Using the app

1. Enter a prompt.
2. Choose DeepSeek, ChatGPT / OpenAI, or Gemini.
3. Choose a model.
4. Leave the API-key field blank for a local input-cost estimate, or enter that provider's API key to send the prompt and receive a response.

Enter a key in the password field to make a real request. The key stays in the Gradio session and is sent only to the selected provider. If the key field is blank, the app does not contact the provider: it cleans the prompt, estimates its token count locally, and calculates an estimated input cost for the selected model. A ChatGPT subscription does not include OpenAI API usage; API billing is separate.

## Developer Layout Lab

The website also has a password-protected **Developer Layout Lab** tab.

- Developer password: `sifter-dev-2026`
- The developer page uses LangChain retrieval over the local project files, then asks the selected LLM to produce a safe `layout_config.json` proposal.
- You can use DeepSeek, ChatGPT / OpenAI, or Gemini for the developer LLM call.
- Review the generated JSON before clicking **Apply proposed layout**.
- After applying a layout, restart the Gradio server so the full website loads the new layout.

The layout tool only saves a constrained JSON config, not arbitrary Python code. It can change the title, subtitle, button text, accent color, page width, prompt/output heights, column balance, and limited custom CSS.

## Troubleshooting

If the address does not load, return to the project folder and restart the server:

```bash
source .venv/bin/activate
python app.py
```

Wait until Terminal displays `Running on local URL: http://127.0.0.1:7860`, then refresh the browser. The address only works on the computer running the Python process.

## Notes

- Prompt cleanup uses the `stop-words` 2025.11.4 English dataset to identify low-information greetings, request particles, courtesies, and honorifics at prompt boundaries. It deliberately does not remove every stop word, which would damage meaningful questions.
- Direct-address wrappers such as “Hello John,” and “Dear Dr. Smith,” and request particles such as “Could you please” are removed while occurrences inside the meaningful prompt are preserved.
- With an API key, token counts come from the selected provider's response.
- When no key is supplied, the app estimates tokens by splitting the cleaned prompt into word, number, and punctuation pieces and approximating subword splits. This is only a guess; provider tokenizers may differ.
- Prices are constants in `app.py` and should be checked against each provider's current pricing before production use.
