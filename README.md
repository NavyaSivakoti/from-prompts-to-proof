# From Prompts to Proof

A small AI customer-support chatbot built for the talk **From Prompts to Proof: How QA Engineers Can Test AI Applications** (BrowserStack QA Meetup, Phoenix).

## The idea

**Northwind Outfitters** is a made-up outdoor gear store with five products: a rain jacket, fleece, backpack, hiking boots, and a tent. Its chatbot answers customer questions about products, shipping, returns, payments, and discounts using only eight short company documents.

The chatbot is meant to be tested. It can make mistakes, and this repo gives you two ways to catch them:

- **Test by hand in the chat**: ask a question, then click **View Context** to see exactly what company information the AI was given. Decide for yourself whether the answer is right.
- **Test automatically with [Promptfoo](https://www.promptfoo.dev/)**: run 31 ready-made test questions in one command. Every answer gets a PASS or FAIL with a reason, and you see a weak prompt (**Baseline**) and a stronger one (**Improved**) side by side.

The chatbot uses OpenAI's `gpt-4o-mini`. Promptfoo grades its answers with a different AI, Anthropic's Claude Haiku 4.5.

## Set up

You need:

- **Python 3.11 or newer**, for the chatbot
- **Node.js 22 or newer** (22.22+), for Promptfoo. Check with `node --version`.
- An **OpenAI API key** for the chatbot
- An **Anthropic API key** for Promptfoo's grader (the chat works without it)

### 1. Download and install

macOS / Linux:

```bash
git clone https://github.com/NavyaSivakoti/from-prompts-to-proof.git
cd from-prompts-to-proof
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Windows (PowerShell):

```powershell
git clone https://github.com/NavyaSivakoti/from-prompts-to-proof.git
cd from-prompts-to-proof
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

### 2. Add your API keys

Open the `.env` file in the project folder and replace the placeholders with your keys:

```text
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
```

`.env` stays on your computer. It is never uploaded to GitHub or shown in the browser. Promptfoo reads the same file.

### 3. Start the chatbot

```bash
python3 demo/app.py
```

On Windows, use `python demo/app.py`. Then open **http://localhost:8000** in your browser. Press **Ctrl+C** in the terminal to stop.

To confirm your OpenAI key works, run `python3 demo/app.py --check`.

## Use it

**Chat**

1. Type a question, or click **Saved Prompts** on the left and pick one to fill the message box, then press **Send**.
2. Click **View Context** under the answer to see the company information the AI used.
3. Check the answer against the facts in the [answer key](ANSWER_KEY.md).
4. In the **Assistant prompt** panel on the right, switch between **Baseline** (a short prompt with no rules) and **Improved** (a prompt with clear rules) to see how instructions change the answer.
5. Click **New conversation** to start fresh.

Try: *"Is the Summit Rain Jacket available in Navy, size M?"*, *"Can I use TRAIL10 on this jacket?"*, or *"Do you price match competitors?"*

**Automatic tests with Promptfoo**

Keep the chatbot running, open a second terminal in the project folder, and run:

```bash
npx promptfoo@latest eval --no-cache
```

It sends all 31 test questions to the chatbot with both prompts, then grades every answer. It takes a few minutes. To see the results in your browser:

```bash
npx promptfoo@latest view
```

Each row is one question, with a **Baseline** column and an **Improved** column. Click a result to see the answer and why it passed or failed. The AI grader can be wrong too, so read its reasons rather than trusting the score alone.

The tests are in [promptfoo/tests.yaml](promptfoo/tests.yaml), and the setup is in [promptfooconfig.yaml](promptfooconfig.yaml). Add a question and its written rule to the tests file, and it's included in the next run.

## Cost

Very small. Estimates are based on this app's real request sizes:

| What you do | OpenAI (`gpt-4o-mini`) | Anthropic (Claude Haiku 4.5) | Total |
|---|---|---|---|
| One chat question | about $0.0004 | none | under 1 cent |
| One Promptfoo run (31 questions, both prompts) | about $0.02 | about $0.17 | about $0.20 |
| Recording backup answers (`--rehearse`) | about $0.02 | none | about 2 cents |

A chat question sends about 2,000 tokens (the system prompt, company documents and question) and gets back about 100. Prices used: [`gpt-4o-mini`](https://developers.openai.com/api/docs/pricing) $0.15 / $0.60 per million input / output tokens, and Claude Haiku 4.5 $1 / $5. Check the providers' pricing pages for current rates.

## Learn more

- [How it works](HOW_IT_WORKS.md): what the chatbot can and can't do, how answers and Promptfoo grading work, company facts, offline backup answers, and the code layout.
- [Answer key](ANSWER_KEY.md): the facts every answer should match, expected behavior for the saved questions, and how to find the cause of a wrong answer.
- [Customer flows](CUSTOMER_FLOWS.md): the real stores that inspired Northwind's shopping journeys.

Run the app's own reliability checks with `python3 -m pytest -q`.

Licensed under [MIT](LICENSE).
