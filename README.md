# From Prompts to Proof

A small AI customer-support chatbot built for the talk **From Prompts to Proof: How QA Engineers Can Test AI Applications** (BrowserStack QA Meetup, Phoenix).

## The idea

**Northwind Outfitters** is a made-up outdoor gear store with five products: a rain jacket, fleece, backpack, hiking boots, and a tent. Its chatbot answers customer questions about products, shipping, returns, payments, and discounts using only eight short company documents.

The chatbot is meant to be tested. It can make mistakes, and the app gives you two ways to catch them:

- **Chat**: ask a question, then click **View Context** to see exactly what company information the AI was given. Decide for yourself whether the answer is right.
- **Evaluation**: run 31 ready-made test questions in one click. Each answer gets a PASS or FAIL with a reason, and you can compare a weak prompt (**Baseline**) with a stronger one (**Improved**).

The chatbot uses OpenAI's `gpt-4o-mini`. The Evaluation page grades its answers with a different AI, Anthropic's Claude Haiku 4.5.

## Set up

You need:

- **Python 3.11 or newer**
- An **OpenAI API key** for the chatbot
- An **Anthropic API key** for the Evaluation page (chat works without it)

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

`.env` stays on your computer. It is never uploaded to GitHub or shown in the browser.

### 3. Start the app

```bash
python3 demo/app.py
```

On Windows, use `python demo/app.py`. Then open **http://localhost:8000** in your browser. Press **Ctrl+C** in the terminal to stop.

To confirm both keys work, run `python3 demo/app.py --check`.

## Use it

**Chat**

1. Type a question, or open **Saved Prompts** and click one to fill the message box, then press **Send**.
2. Click **View Context** under the answer to see the company information the AI used.
3. Check the answer against the facts. The [presenter guide](DEMO_GUIDE.md) has the answer key.
4. In **Settings**, switch between **Baseline** and **Improved** to see how the prompt changes the answer.

Try: *"Is the Summit Rain Jacket available in Navy, size M?"*, *"Can I use TRAIL10 on this jacket?"*, or *"Do you price match competitors?"*

**Evaluation**

1. Click **Evaluation** at the top of the page.
2. Choose a prompt and click **Run Evaluation Suite**. It takes a few minutes.
3. Click **View details** on any result to see the question, the answer, and why it passed or failed.

The AI grader can be wrong too, so read its reasons rather than trusting the score alone.

## Cost

Very small. Estimates are based on this app's real request sizes:

| What you do | OpenAI (`gpt-4o-mini`) | Anthropic (Claude Haiku 4.5) | Total |
|---|---|---|---|
| One chat question | about $0.0004 | none | under 1 cent |
| One Evaluation run (31 questions, one prompt) | about $0.01 | about $0.08 | about $0.10 |
| Recording backup answers for both prompts (`--rehearse`) | about $0.02 | about $0.17 | about $0.20 |

A chat question sends about 2,000 tokens (the system prompt, company documents and question) and gets back about 100. Prices used: [`gpt-4o-mini`](https://developers.openai.com/api/docs/pricing) $0.15 / $0.60 per million input / output tokens, and Claude Haiku 4.5 $1 / $5. Check the providers' pricing pages for current rates.

## Learn more

- [How it works](HOW_IT_WORKS.md): what the chatbot can and can't do, how answers and grading work, company facts, offline backup answers, and the code layout.
- [Presenter guide](DEMO_GUIDE.md): the answer key, a live demo flow, and a pre-talk checklist.
- [Customer flows](CUSTOMER_FLOWS.md): the real stores that inspired Northwind's shopping journeys.

Run the automated tests with `python3 -m pytest -q`.

Licensed under [MIT](LICENSE).
