"""Plain local JSON recordings. Only compatible evidence can be replayed."""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from demo import config
from demo.evaluator import load_test_cases

SOURCE_LABELS = {
    "live": "Live response",
    "replay": "REPLAY MODE — Saved responses",
    "fallback": "Fallback response — saved during rehearsal",
}


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


def case_signature(case: dict) -> str:
    from demo.model import GRADING_INSTRUCTIONS

    evidence = {"case": case}
    if case["evaluation_method"] == "model-graded":
        evidence["grading_instructions"] = GRADING_INSTRUCTIONS
        evidence["grader_model"] = config.GRADER_MODEL
        evidence["grader_temperature"] = config.GRADER_TEMPERATURE
    return hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()


def load_recording() -> dict:
    path = config.REHEARSAL_DIR / "latest.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or not isinstance(data.get("suites"), dict):
            return {}
        suites = data["suites"]
        expected_ids = {case["id"] for case in load_test_cases()}
        if set(suites) != set(config.PROMPT_VERSIONS):
            return {}
        if any(
            not isinstance(suite, dict)
            or not isinstance(suite.get("results"), list)
            or len(suite["results"]) != len(expected_ids)
            or any(not isinstance(row, dict) or not isinstance(row.get("id"), str)
                   for row in suite["results"])
            or {row.get("id") for row in suite["results"]} != expected_ids
            for suite in suites.values()
        ):
            return {}
        return data
    except (OSError, ValueError, AttributeError):
        return {}


def find_saved(question: str, prompt_version: str, context: str, history: list[dict] | None = None) -> dict | None:
    suite = load_recording().get("suites", {}).get(prompt_version, {})
    wanted = signature(question, prompt_version, context, history)
    for record in suite.get("results", []):
        if record.get("signature") == wanted and isinstance(record.get("response"), str) and record["response"]:
            return record.copy()
    return None


def save_recording(suites: dict) -> tuple:
    """Keep an archive; publish latest only if both suites completed without errors."""
    config.REHEARSAL_DIR.mkdir(parents=True, exist_ok=True)
    recorded_at = timestamp()
    data = {"schema_version": 1, "timestamp": recorded_at, "suites": suites}
    archive = config.REHEARSAL_DIR / (
        "rehearsal-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json"
    )
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    archive.write_text(payload, encoding="utf-8")
    expected_ids = {case["id"] for case in load_test_cases()}
    complete = set(suites) == set(config.PROMPT_VERSIONS) and all(
        len(suite["results"]) == len(expected_ids)
        and {row.get("id") for row in suite["results"]} == expected_ids
        and all(row.get("result") in {"PASS", "FAIL"} and row.get("source") == "live" for row in suite["results"])
        for suite in suites.values()
    )
    if complete:
        temporary = config.REHEARSAL_DIR / "latest.tmp"
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(config.REHEARSAL_DIR / "latest.json")
    return archive, complete


def write_report(suites: dict) -> Path:
    """Save every answer verbatim, with the evidence and evaluation beside it."""
    def verbatim(value: str) -> str:
        longest = max((len(run) for run in re.findall(r"`+", value)), default=0)
        fence = "`" * max(3, longest + 1)
        return f"{fence}text\n{value}\n{fence}\n"

    lines = ["# Development report\n", "These are recorded outcomes, without response edits or predetermined grades.\n"]
    has_errors = any(row.get("result") == "ERROR" for suite in suites.values() for row in suite["results"])
    if has_errors:
        lines.append("**Live verification could not be completed.** Errors below are request or grading errors, not behavior failures. No answer is invented for a failed request.\n")
    for version, suite in suites.items():
        lines.extend([
            f"## {version.title()} Prompt\n",
            f"Model: `{suite['model']}` · Temperature: `{suite['temperature']}` · "
            f"Max completion tokens: `{suite.get('max_completion_tokens', config.MAX_COMPLETION_TOKENS)}` · "
            f"Run time (UTC): `{suite['timestamp']}`\n",
        ])
        for index, row in enumerate(suite["results"], 1):
            lines.extend([
                f"### {index}. {row['name']}\n",
                "Question:\n", verbatim(row["question"]),
                "Declared conversation setup (user messages, not fabricated model answers):\n",
                verbatim(json.dumps(row.get("conversation_history", []), ensure_ascii=False, indent=2)),
                "Expected behavior:\n", row["expected_behavior"] + "\n",
                "Retrieved context:\n", verbatim(row["retrieved_context"] or "No matching company information was found for this question."),
                "Actual model response:\n", verbatim(row["response"]) if row["response"] else "No model response was returned.\n",
                f"Evaluation method: {row['evaluation_method']}\n",
                f"Outcome: **{row['result']}**\n",
                "Evaluation reason:\n", verbatim(row["reason"]),
                f"Response source: {row['source_label']}\n",
            ])
    path = config.REHEARSAL_DIR / "development-report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
