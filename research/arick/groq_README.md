# Groq Chat — Student Startup Guide

This guide helps you run **groq_chat** on your own computer, even if you have never written code before. Follow the steps in order. If something fails, use the [Troubleshooting](#troubleshooting) section at the end.

---

## What is this project?

**groq_chat** is a small program that opens a **chat window in your web browser** (like a simple ChatGPT-style page). You type a question, pick an **AI model**, and the program sends your text to **Groq** over the internet. Groq runs the model in the cloud and sends back an answer, which appears on the same page.

You do **not** need to edit any code to use it. You only need to install a few free tools, add a **free API key** (a secret password that lets the app talk to Groq on your behalf), and run one command.

**What the pieces mean (in plain language):**

| Term | What it is |
|------|------------|
| **Python** | A programming language. This project is written in Python, and your computer needs Python installed to run it. |
| **groq_chat.py** | The main file for this app. It is the “recipe” that builds the browser chat page. |
| **Gradio** | A library that creates the web page (text boxes, buttons) automatically so you do not have to build a website by hand. |
| **Groq** | A company that offers fast access to several AI models through an **API** (a way for programs to ask for AI answers over the internet). |
| **API key** | A long string Groq gives you. It identifies your free account. **Keep it private** and never paste it into public chats or put it in a public GitHub file. |

---

## What you need

1. A computer (Mac, Windows, or Linux) with **admin rights** to install software (or use a school computer that already has Python).
2. A stable **internet** connection.
3. About **20–30 minutes** the first time (installing Python and packages).

---

## Step 1: Install Python

Python is free. You want **Python 3.10 or newer** (3.12 or 3.13 is fine).

- **Windows:** Download the installer from [https://www.python.org/downloads/](https://www.python.org/downloads/).  
  - During install, check **“Add python.exe to PATH”** (important).  
  - Then finish the installation.
- **Mac:** Install from [python.org](https://www.python.org/downloads/) or use the official **Python.org** macOS installer.  
  - Alternatively, if a teacher set up **Homebrew** for you, you can use that—follow your course instructions.

**Check that it works:**  
Open a **terminal** (Mac/Linux: *Terminal*; Windows: *PowerShell* or *Command Prompt*) and type:

```bash
python --version
```

or, on some systems:

```bash
python3 --version
```

You should see something like `Python 3.12.x`. If the command is not found, Python is not on your PATH; retry installation or ask for help with “Python not found in terminal.”

---

## Step 2: Get the project on your computer

**Option A — Git (if you use Git or GitHub):**  
In the folder where you keep projects, run:

```bash
git clone <PASTE-YOUR-REPO-URL-HERE>
cd <FOLDER-NAME-OF-REPO>
```

Replace `<PASTE-YOUR-REPO-URL-HERE>` with the HTTPS URL from the green “Code” button on GitHub, and `<FOLDER-NAME-OF-REPO>` with the folder that was created.

**Option B — No Git:**  
On the GitHub page, use **Code → Download ZIP**, unzip the folder, and in the next steps, open a terminal **inside** that unzipped folder (the folder that contains `groq_chat.py` and `requirements.txt`).

---

## Step 3: Open a terminal in the project folder

The terminal must be “inside” the folder that contains `groq_chat.py`.

- **Mac/Linux:** In *Terminal*, type `cd ` (with a space), then **drag the project folder** into the window and press Enter. That pastes the full path and changes into that folder.
- **Windows:** In File Explorer, open the project folder, click the address bar, type `cmd` and press Enter, or *Shift+right-click* → *Open in Terminal*.

If you are in the right place, listing files should show `groq_chat.py` (and usually `requirements.txt`):

```bash
# Mac/Linux
ls

# Windows (PowerShell)
dir
```

---

## Step 4: Create a virtual environment (recommended)

A **virtual environment** is a private box for this project’s Python packages so they do not clash with other projects.

**Mac / Linux (bash or zsh):**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**

```bash
python -m venv .venv
.venv\Scripts\activate.bat
```

After this, your prompt may start with `(.venv)`—that means the environment is active. **Keep this terminal window open** for the next steps.

---

## Step 5: Install dependencies

The project needs the packages listed in `requirements.txt` (including **gradio** and the **groq** client). With the virtual environment **activated** and your terminal still in the project folder, run:

```bash
pip install -r requirements.txt
```

If `pip` is not found, try `python -m pip install -r requirements.txt`.

Wait until the install finishes without red error text. A lot of “Collecting …” and “Installing …” lines is normal.

---

## Step 6: Get a free Groq API key

1. Open [https://console.groq.com](https://console.groq.com) in a browser.
2. Sign up or log in.
3. Go to the **API keys** section and **create a new key**.
4. **Copy** the key and store it somewhere safe (password manager or a private note). You usually cannot see the full key again after you leave the page.

---

## Step 7: Set the API key in your terminal

The program reads your key from an **environment variable** named `GROQ_API_KEY`. That is a name your operating system uses to hand a value to the program when it starts.

**Mac / Linux (same terminal where you will run the app, after `source .venv/bin/activate`):**

```bash
export GROQ_API_KEY="paste-your-actual-key-here"
```

**Windows PowerShell (same session you will use to run the app):**

```powershell
$env:GROQ_API_KEY="paste-your-actual-key-here"
```

**Windows Command Prompt:**

```cmd
set GROQ_API_KEY=paste-your-actual-key-here
```

Replace `paste-your-actual-key-here` with the real key (keep the quotes on Mac/Linux and PowerShell).  
**The key resets** when you close the terminal. Next time, activate the venv again and run `export` / `$env:…` / `set` again—or ask a teacher to show you a `.env` file approach for a more permanent (still local) setup.

---

## Step 8: Run Groq Chat

With the venv **active**, `GROQ_API_KEY` **set**, and the terminal in the project folder:

**Mac / Linux:**

```bash
python3 groq_chat.py
```

**Windows:**

```bash
python groq_chat.py
```

You should see text in the terminal that includes a **local URL**, often:

`http://127.0.0.1:7860`  
(or another port if 7860 is busy)

Open that address in **Chrome, Firefox, or Edge**. You will see a page titled **“Groq chat”** with a **Prompt** box, a **Model** dropdown, and **Send**.

- Type a question, choose a model, click **Send** (or press Enter in the prompt box, depending on the UI).
- The **Response** area fills with the model’s answer.

**To stop the app:** go back to the terminal and press **Ctrl+C** (Mac/Linux/Windows).

---

## What you can try in the app

The dropdown lists default models (for example Llama, Mixtral, Gemma). You can switch models to see different styles or speeds. The field may also allow typing a custom model name if you know a valid Groq model id; if unsure, stay with the list.

---

## Troubleshooting

**“Missing GROQ_API_KEY” in the response box**  
Set the key again in **the same terminal session** you used to start the app (see Step 7), then run `python(3) groq_chat.py` again.

**`python` or `python3` is not recognized**  
Python is not installed or not on PATH. Repeat Step 1, make sure “Add to PATH” is selected on Windows, or use the full path to the Python executable.

**`ModuleNotFoundError: No module named 'gradio'` (or `groq`)**  
Your venv may not be activated, or you skipped Step 5. Run `source .venv/bin/activate` (or Windows activate), then `pip install -r requirements.txt` again.

**Port already in use**  
Another program (or an old run of the same app) is using the port. Close other Gradio apps or change the port when launching (see Gradio’s `launch(server_port=…)` in code—only if a maintainer shows you how).

**The browser shows “refused to connect”**  
The app is not running, or the URL/port is wrong. Check the **exact** URL printed in the terminal after you start `groq_chat.py`.

**I accidentally put my API key on GitHub**  
Revoke that key in the Groq console immediately, create a new key, and never commit keys in files. Add `.env` to `.gitignore` if you use a local env file in the future.
