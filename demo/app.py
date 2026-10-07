"""Run with python3 demo/app.py; the three demo CLI modes share the same code."""

import argparse
import asyncio
import logging
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Literal
from uuid import uuid4

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
    from demo.evaluator import evaluate_response, load_test_cases
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


class EvaluationRequest(BaseModel):
    prompt_version: Literal["baseline", "improved"] = "baseline"
    run_id: str | None = Field(default=None, min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")


class EvaluationStopRequest(BaseModel):
    run_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")


async def answer_question(question: str, prompt_version: str, *, history: list[dict] | None = None, replay: bool = False, allow_fallback: bool = True) -> dict:
    # Live chats carry bounded browser history; evaluation can supply a declared
    # user-only setup. Public replay chat discards browser history at its route.
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


def method_label(case: dict) -> str:
    if case["evaluation_method"] == "model-graded":
        return f"Model-graded ({config.GRADER_MODEL})"
    if case["id"] == "prompt-injection":
        return "Deterministic — system prompt leakage check"
    return "Deterministic"


def suite_result(prompt_version: str, rows: list[dict], *, replay: bool = False) -> dict:
    return {
        "prompt_version": prompt_version, "model": config.MODEL,
        "temperature": config.TEMPERATURE, "timestamp": rehearsal.timestamp(),
        "max_completion_tokens": config.MAX_COMPLETION_TOKENS,
        "mode": "replay" if replay else ("fallback" if any(r["source"] == "fallback" for r in rows) else "live"),
        "results": rows,
    }


async def run_suite(
    prompt_version: str, *, replay: bool = False, allow_fallback: bool = True,
    completed_rows: list[dict] | None = None,
) -> dict:
    rows = completed_rows if completed_rows is not None else []
    for case in load_test_cases():
        history = case.get("history", [])[-config.MAX_HISTORY_MESSAGES:]
        documents = retrieve(case["question"], history=history)
        row = {
            "id": case["id"], "name": case["name"], "question": case["question"],
            "expected_behavior": case["expected_behavior"], "categories": case["categories"],
            "evaluation_method": method_label(case), "response": "",
            "retrieved_context": format_context(documents), "sources": documents,
            "conversation_history": history,
            "model": config.MODEL, "temperature": config.TEMPERATURE,
            "max_completion_tokens": config.MAX_COMPLETION_TOKENS,
            "prompt_version": prompt_version, "timestamp": rehearsal.timestamp(),
            "source": "replay" if replay else "live",
            "source_label": rehearsal.SOURCE_LABELS["replay" if replay else "live"],
        }
        try:
            answer = await answer_question(case["question"], prompt_version, history=history,
                                           replay=replay, allow_fallback=allow_fallback)
            row.update(answer)
            if answer["source"] == "live":
                grade = await evaluate_response(case, answer["response"], answer["retrieved_context"])
                row.update(grade)
            else:
                # Reuse the recorded judgment only for the same rubric. Never silently
                # call the model grader in replay, or grade a fallback as a new answer.
                if answer.get("case_signature") != rehearsal.case_signature(case) or answer.get("result") not in {"PASS", "FAIL"}:
                    raise model.ModelError("No saved evaluation matches the current test case and rubric. Run --rehearse again.")
            row["case_signature"] = rehearsal.case_signature(case)
        except model.ModelError as exc:
            row.update(result="ERROR", reason=str(exc), error=str(exc))
            if not row["response"]:
                row["source_label"] = "Replay request — no saved response available" if replay else "Live request — no response available"
        rows.append(row)
    return suite_result(prompt_version, rows, replay=replay)


def create_app(*, replay: bool = False) -> FastAPI:
    application = FastAPI(title="Northwind Outfitters Support", docs_url=None, redoc_url=None)
    application.state.replay = replay
    application.state.latest = {version: None for version in config.PROMPT_VERSIONS}
    # Keep active tasks and a bounded history of early stops/finished IDs. Each
    # web run has a unique ID, so a late Stop cannot cancel a subsequent run.
    application.state.evaluation_runs = OrderedDict()
    static = config.DEMO_DIR / "static"
    application.mount("/static", StaticFiles(directory=static), name="static")

    def remember_run(run_id: str, state: dict) -> None:
        runs = application.state.evaluation_runs
        runs[run_id] = state
        runs.move_to_end(run_id)
        while len(runs) > 128:
            removable = next(key for key, value in runs.items() if value["status"] not in {"running", "stopping"})
            del runs[removable]

    def web_suite(suite: dict, run_id: str, *, stopped: bool, total_count: int) -> dict:
        return {**suite, "run_id": run_id, "stopped": stopped,
                "completed_count": len(suite["results"]), "total_count": total_count}

    @application.get("/")
    async def chat_page():
        return FileResponse(static / "index.html")

    @application.get("/evaluation")
    async def evaluation_page():
        return FileResponse(static / "evaluation.html")

    @application.get("/api/config")
    async def app_config():
        return {
            "model": config.MODEL, "temperature": config.TEMPERATURE,
            "prompt_versions": list(config.PROMPT_VERSIONS),
            "mode": "replay" if replay else "live",
            "replay_available": bool(rehearsal.load_recording()),
            "api_key_configured": model.api_key_configured(),
            "grader_model": config.GRADER_MODEL,
            "grader_temperature": config.GRADER_TEMPERATURE,
            "grader_key_configured": model.grader_key_configured(),
            "max_history_messages": config.MAX_HISTORY_MESSAGES,
        }

    @application.get("/api/test-cases")
    async def test_cases():
        return load_test_cases()

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

    @application.post("/api/evaluate")
    async def evaluate(request: EvaluationRequest):
        run_id = request.run_id or uuid4().hex
        runs = application.state.evaluation_runs
        previous = runs.get(run_id)
        total_count = len(load_test_cases())
        if previous and previous["status"] == "pending-stop":
            remember_run(run_id, {"status": "stopped"})
            return web_suite(suite_result(request.prompt_version, [], replay=replay), run_id,
                             stopped=True, total_count=total_count)
        if previous:
            raise HTTPException(status_code=409, detail="This evaluation run ID has already been used. Start with a new run ID.")
        if any(state["status"] in {"running", "stopping"} for state in runs.values()):
            raise HTTPException(status_code=409, detail="An evaluation is already running. Stop it or wait for it to finish.")

        rows = []
        task = asyncio.create_task(run_suite(request.prompt_version, replay=replay, completed_rows=rows))
        state = {"status": "running", "task": task, "stop_requested": False}
        remember_run(run_id, state)
        try:
            try:
                suite = await task
            except asyncio.CancelledError:
                if not state["stop_requested"]:
                    raise
                # Cancellation can arrive before the worker starts, during an
                # answer, or during grading. Only fully finished rows survive.
                return web_suite(suite_result(request.prompt_version, rows, replay=replay), run_id,
                                 stopped=True, total_count=total_count)
            result = web_suite(suite, run_id, stopped=False, total_count=total_count)
            application.state.latest[request.prompt_version] = result
            return result
        finally:
            remember_run(run_id, {"status": "stopped" if state["stop_requested"] else "finished"})

    @application.post("/api/evaluate/stop")
    async def stop_evaluation(request: EvaluationStopRequest):
        state = application.state.evaluation_runs.get(request.run_id)
        if state is None:
            # The separate Stop request may reach the server before Evaluate.
            remember_run(request.run_id, {"status": "pending-stop"})
            return {"run_id": request.run_id, "status": "stopping", "stopped": True}
        if state["status"] == "pending-stop":
            return {"run_id": request.run_id, "status": "stopping", "stopped": True}
        if state["status"] in {"running", "stopping"} and not state["task"].done():
            if not state["stop_requested"]:
                state["task"].cancel()
            state["stop_requested"] = True
            state["status"] = "stopping"
            return {"run_id": request.run_id, "status": "stopping", "stopped": True}
        return {"run_id": request.run_id, "status": "not-running", "stopped": False}

    @application.get("/api/evaluations")
    async def evaluations():
        return application.state.latest

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
    print("Grader API key (Anthropic): " + ("found" if model.grader_key_configured() else "missing"))
    print(f"Grader model: {config.GRADER_MODEL}")
    if not model.grader_key_configured():
        print("Grader: SKIPPED — add ANTHROPIC_API_KEY to .env to run Evaluation.")
        return 1
    try:
        await model.grade_response("Reply check", "", "OK", "PASS if the answer is OK.")
    except model.ModelError as exc:
        print(f"Grader: FAIL — {exc}")
        return 1
    print("Grader: PASS")
    return 0


async def rehearse() -> int:
    missing = [name for name, ok in (("OPENAI_API_KEY", model.api_key_configured()),
                                     ("ANTHROPIC_API_KEY", model.grader_key_configured())) if not ok]
    if missing:
        print(f"Rehearsal needs both API keys. Add {' and '.join(missing)} to .env, then run again.")
        return 1
    print(f"Rehearsing both prompts with {config.MODEL}, temperature={config.TEMPERATURE}.")
    print(f"Grader: {config.GRADER_MODEL}, temperature={config.GRADER_TEMPERATURE}.")
    print("Running actual answers and evaluations; no fallback responses are used.")
    suites = {}
    for version in config.PROMPT_VERSIONS:
        print(f"Running {version}…", flush=True)
        suite = await run_suite(version, allow_fallback=False)
        suites[version] = suite
        for row in suite["results"]:
            print(f"  {row['id']}: {row['result']} — {row['reason']}")
    path, complete = rehearsal.save_recording(suites)
    print(f"Saved actual rehearsal evidence: {path}")
    print(f"Saved development report: {rehearsal.write_report(suites)}")
    if not complete:
        print("Rehearsal has errors. No complete replay recording was replaced.")
        return 1
    print("Replay recording ready. PASS and FAIL are both valid recorded outcomes.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true", help="Check both API keys with one small request each.")
    modes.add_argument("--rehearse", action="store_true", help="Record actual answers and grades for both prompts.")
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
