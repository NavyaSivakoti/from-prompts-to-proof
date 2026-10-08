"""Run with python3 demo/app.py. Evaluation lives in Promptfoo (promptfooconfig.yaml)."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Literal

# Support the README's direct script command and imports from pytest alike.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import uvicorn
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel, Field, field_validator

    from demo import config, model, rehearsal
    from demo.retrieval import format_context, load_knowledge, retrieve
except ModuleNotFoundError as exc:
    if __name__ != "__main__":
        raise
    print(f"Missing Python dependency: {exc.name}. Activate the project virtual environment.", file=sys.stderr)
    if sys.platform == "win32":
        commands = ".venv\\Scripts\\Activate.ps1\npython -m pip install -r requirements.txt\npython demo/app.py"
    else:
        commands = "source .venv/bin/activate\npython3 -m pip install -r requirements.txt\npython3 demo/app.py"
    print(f"\nFrom the repository folder, run:\n\n{commands}", file=sys.stderr)
    sys.exit(1)

logger = logging.getLogger(__name__)
# Pages always revalidate, so a browser never shows an outdated page after an update.
NO_CACHE = {"Cache-Control": "no-cache"}


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    prompt_version: Literal["baseline", "improved"] = "improved"
    history: list[HistoryMessage] = Field(default_factory=list, max_length=config.MAX_HISTORY_MESSAGES)

    @field_validator("question")
    @classmethod
    def meaningful_question(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Enter a question.")
        return value.strip()


async def answer_question(question: str, prompt_version: str, *, history: list[dict] | None = None, replay: bool = False, allow_fallback: bool = True) -> dict:
    # Live chats and Promptfoo tests carry bounded history. Public replay chat
    # discards browser history at its route.
    conversation_history = (history or [])[-config.MAX_HISTORY_MESSAGES:]
    documents = retrieve(question, history=conversation_history) if conversation_history else retrieve(question)
    context = format_context(documents)
    saved = rehearsal.find_saved(question, prompt_version, context, conversation_history) if replay or allow_fallback else None
    if replay:
        if saved is None:
            raise model.ModelError(
                "No matching saved rehearsal response exists for this question and configuration. "
                "Replay makes no live API calls. Run --rehearse with your API key first."
            )
        saved.update(source="replay", source_label=rehearsal.SOURCE_LABELS["replay"])
        return saved
    try:
        prompt = config.load_prompt(prompt_version)
        response = await model.generate_response(question, context, prompt, conversation_history) if conversation_history else await model.generate_response(question, context, prompt)
    except model.ModelError as exc:
        if saved is None:
            raise
        saved.update(source="fallback", source_label=rehearsal.SOURCE_LABELS["fallback"], error=str(exc))
        return saved
    return {
        "question": question,
        "response": response,
        "retrieved_context": context,
        "sources": documents,
        "conversation_history": conversation_history,
        "model": config.MODEL,
        "temperature": config.TEMPERATURE,
        "max_completion_tokens": config.MAX_COMPLETION_TOKENS,
        "prompt_version": prompt_version,
        "timestamp": rehearsal.timestamp(),
        "source": "live",
        "source_label": rehearsal.SOURCE_LABELS["live"],
        "signature": rehearsal.signature(question, prompt_version, context, conversation_history),
    }


def create_app(*, replay: bool = False) -> FastAPI:
    application = FastAPI(title="Northwind Outfitters Support", docs_url=None, redoc_url=None)
    application.state.replay = replay
    static = config.DEMO_DIR / "static"
    application.mount("/static", StaticFiles(directory=static), name="static")

    @application.get("/")
    async def chat_page():
        return FileResponse(static / "index.html", headers=NO_CACHE)

    @application.get("/api/config")
    async def app_config():
        return {
            "model": config.MODEL, "temperature": config.TEMPERATURE,
            "prompt_versions": list(config.PROMPT_VERSIONS),
            "mode": "replay" if replay else "live",
            "replay_available": bool(rehearsal.load_recording()),
            "api_key_configured": model.api_key_configured(),
            "max_history_messages": config.MAX_HISTORY_MESSAGES,
        }

    @application.get("/api/knowledge")
    async def knowledge():
        return load_knowledge()

    @application.post("/api/chat")
    async def chat(request: ChatRequest):
        try:
            history = [] if replay else [message.model_dump() for message in request.history]
            return await answer_question(request.question, request.prompt_version, history=history, replay=replay)
        except model.ModelError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from None

    return application


async def check_connection() -> int:
    print("API key: " + ("found" if model.api_key_configured() else "missing"))
    print(f"Model: {config.MODEL}")
    try:
        await model.generate_response("Reply with OK.", "", "You are a connection check assistant.")
    except model.ModelError as exc:
        print(f"Connection: FAIL — {exc}")
        return 1
    print("Connection: PASS")
    return 0


async def rehearse() -> int:
    """Record live answers to every Promptfoo test question, for fallback and replay."""
    if not model.api_key_configured():
        print("Rehearsal needs OPENAI_API_KEY in .env.")
        return 1
    questions = rehearsal.load_questions()
    print(f"Recording {len(questions)} questions for both prompts with {config.MODEL}, temperature={config.TEMPERATURE}.")
    answers = {}
    for version in config.PROMPT_VERSIONS:
        print(f"Running {version}…", flush=True)
        rows = []
        for item in questions:
            try:
                row = await answer_question(item["question"], version, history=item["history"], allow_fallback=False)
                print(f"  saved: {item['question'][:70]}")
            except model.ModelError as exc:
                row = {"question": item["question"], "conversation_history": item["history"],
                       "prompt_version": version, "source": "error", "error": str(exc)}
                print(f"  ERROR: {item['question'][:70]} — {exc}")
            rows.append(row)
        answers[version] = rows
    path, complete = rehearsal.save_recording(answers)
    print(f"Saved answers: {path}")
    print(f"Saved readable report: {rehearsal.write_report(answers)}")
    if not complete:
        print("Some requests failed. The previous backup answers were kept.")
        return 1
    print("Backup answers ready for fallback and --replay.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true", help="Check the OpenAI key with one small request.")
    modes.add_argument("--rehearse", action="store_true", help="Record backup answers for every test question and both prompts.")
    modes.add_argument("--replay", action="store_true", help="Serve saved evidence without calling OpenAI.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    if args.check:
        sys.exit(asyncio.run(check_connection()))
    if args.rehearse:
        sys.exit(asyncio.run(rehearse()))
    if args.replay:
        print(rehearsal.SOURCE_LABELS["replay"])
    print("Open http://localhost:8000 — press Ctrl+C to stop.")
    # Bind locally; there are deliberately no accounts or authentication in this demo.
    uvicorn.run(create_app(replay=args.replay), host="127.0.0.1", port=8000, log_level="warning")


if __name__ == "__main__":
    main()
