"""Plain local JSON recordings of real answers. Only compatible answers are reused."""

import hashlib
import json
import re
from datetime import datetime, timezone

import yaml

from demo import config

SOURCE_LABELS = {
    "live": "Live response",
    "replay": "REPLAY MODE — Saved responses",
    "fallback": "Fallback response — saved during rehearsal",
}
SCHEMA_VERSION = 2
TESTS_PATH = config.ROOT_DIR / "promptfoo" / "tests.yaml"


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def signature(question: str, prompt_version: str, context: str, history: list[dict] | None = None) -> str:
    """Invalidate recordings when question, prompt, model, settings, or context change."""
    evidence = {
        "question": " ".join(question.casefold().split()),
        "prompt": config.load_prompt(prompt_version),
        "context": context,
        "model": config.MODEL,
        "temperature": config.TEMPERATURE,
        "max_completion_tokens": config.MAX_COMPLETION_TOKENS,
        "conversation_history": history or [],
    }
    return hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()


def load_questions() -> list[dict]:
    """The Promptfoo test questions are what we record. Each test is one question."""
    tests = yaml.safe_load(TESTS_PATH.read_text(encoding="utf-8"))
    return [{"question": test["vars"]["question"], "history": []} for test in tests]


def load_recording() -> dict:
    path = config.REHEARSAL_DIR / "latest.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        answers = data.get("answers")
        if data.get("schema_version") != SCHEMA_VERSION or not isinstance(answers, dict):
            return {}
        if set(answers) != set(config.PROMPT_VERSIONS) or any(
            not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows)
            for rows in answers.values()
        ):
            return {}
        return data
    except (OSError, ValueError, AttributeError):
        return {}


def find_saved(question: str, prompt_version: str, context: str, history: list[dict] | None = None) -> dict | None:
    rows = load_recording().get("answers", {}).get(prompt_version, [])
    wanted = signature(question, prompt_version, context, history)
    for record in rows:
        if record.get("signature") == wanted and isinstance(record.get("response"), str) and record["response"]:
            return record.copy()
    return None


def save_recording(answers: dict) -> tuple:
    """Keep an archive; replace latest only if every answer was recorded live."""
    config.REHEARSAL_DIR.mkdir(parents=True, exist_ok=True)
    data = {"schema_version": SCHEMA_VERSION, "timestamp": timestamp(), "answers": answers}
    archive = config.REHEARSAL_DIR / (
        "rehearsal-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json"
    )
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    archive.write_text(payload, encoding="utf-8")
    complete = set(answers) == set(config.PROMPT_VERSIONS) and all(
        rows and all(row.get("source") == "live" for row in rows) for rows in answers.values()
    )
    if complete:
        temporary = config.REHEARSAL_DIR / "latest.tmp"
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(config.REHEARSAL_DIR / "latest.json")
    return archive, complete


def write_report(answers: dict):
    """Save every recorded answer verbatim, with the documents the chatbot was given."""
    def verbatim(value: str) -> str:
        longest = max((len(run) for run in re.findall(r"`+", value)), default=0)
        fence = "`" * max(3, longest + 1)
        return f"{fence}text\n{value}\n{fence}\n"

    lines = ["# Recorded answers\n", "Real answers saved by `--rehearse`, without edits. Grade them with Promptfoo.\n"]
    for version, rows in answers.items():
        lines.append(f"## {version.title()} prompt\n")
        for index, row in enumerate(rows, 1):
            lines.extend([
                f"### {index}. {row['question']}\n",
                "Earlier messages:\n", verbatim(json.dumps(row.get("conversation_history", []), ensure_ascii=False, indent=2)),
                "Company documents given to the chatbot:\n",
                verbatim(row.get("retrieved_context") or "No matching company information was found for this question."),
                "Answer:\n", verbatim(row["response"]) if row.get("response") else f"No answer: {row.get('error', 'unknown error')}\n",
            ])
    path = config.REHEARSAL_DIR / "recorded-answers.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
