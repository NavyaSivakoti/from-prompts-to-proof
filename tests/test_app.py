"""Application reliability checks use synthetic test answers, never demo results."""

import asyncio
import json
import re
from pathlib import Path

import httpx
import pytest
import yaml
from fastapi.testclient import TestClient
from openai import APIConnectionError, AsyncOpenAI

from demo import config, model, rehearsal
from demo.app import answer_question, create_app

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def isolated_recordings(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "REHEARSAL_DIR", tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    return tmp_path


def record_answers() -> dict:
    """Record a synthetic answer to every Promptfoo question, as --rehearse does."""
    answers = {}
    for version in config.PROMPT_VERSIONS:
        answers[version] = [
            asyncio.run(answer_question(item["question"], version, history=item["history"], allow_fallback=False))
            for item in rehearsal.load_questions()
        ]
    return answers


def test_pages_and_missing_key_are_handled(isolated_recordings):
    with TestClient(create_app()) as client:
        assert client.get("/").status_code == 200
        assert client.get("/evaluation").status_code == 404
        assert client.get("/static/app.js").status_code == 200
        assert len(client.get("/api/knowledge").json()) == 8
        settings = client.get("/api/config").json()
        assert settings["api_key_configured"] is False
        assert settings["temperature"] == 0.7
        assert "grader_model" not in settings
        result = client.post("/api/chat", json={"question": "What is your return window?"})
        assert result.status_code == 503
        assert result.json()["detail"] == "OpenAI API key is not configured."
        assert client.post("/api/chat", json={"question": "   "}).status_code == 422


def test_record_replay_and_fallback_never_invent_results(isolated_recordings, monkeypatch):
    seen_histories = []

    async def synthetic_answer(question, context, prompt, previous=None):
        seen_histories.append(previous or [])
        return "You can return unused items within 30 days of delivery."

    monkeypatch.setattr(model, "generate_response", synthetic_answer)
    answers = record_answers()
    _, complete = rehearsal.save_recording(answers)
    assert complete
    report = rehearsal.write_report(answers).read_text(encoding="utf-8")
    assert report.count("### ") == 2 * len(rehearsal.load_questions())
    setup = next(item["history"] for item in rehearsal.load_questions() if item["history"])
    assert setup in seen_histories

    async def forbidden_call(*args, **kwargs):
        pytest.fail("Replay attempted a live model call")

    monkeypatch.setattr(model, "generate_response", forbidden_call)
    replayed = asyncio.run(answer_question("What is your return window?", "baseline", replay=True))
    assert replayed["source"] == "replay"
    assert replayed["response"] == "You can return unused items within 30 days of delivery."
    with TestClient(create_app(replay=True)) as client:
        replay_chat = client.post("/api/chat", json={
            "question": "What is your return window?", "prompt_version": "baseline",
            "history": [{"role": "user", "content": "An unrelated browser conversation"}],
        }).json()
        assert replay_chat["source"] == "replay"
        assert replay_chat["conversation_history"] == []
    with pytest.raises(model.ModelError, match="No matching saved"):
        asyncio.run(answer_question("An unsaved free-form question", "baseline", replay=True))

    async def provider_failure(*args):
        raise model.ModelError("OpenAI request failed (HTTP 503). Please try again.")

    monkeypatch.setattr(model, "generate_response", provider_failure)
    fallback = asyncio.run(answer_question("What is your return window?", "baseline"))
    assert fallback["source_label"] == "Fallback response — saved during rehearsal"
    assert fallback["error"] == "OpenAI request failed (HTTP 503). Please try again."
    assert fallback["response"] == answers["baseline"][0]["response"]
    with pytest.raises(model.ModelError, match="HTTP 503"):
        asyncio.run(answer_question("An unsaved question", "baseline"))


def test_failed_recording_keeps_previous_backup(isolated_recordings, monkeypatch):
    async def synthetic_answer(question, context, prompt, previous=None):
        return "A complete earlier recording."

    monkeypatch.setattr(model, "generate_response", synthetic_answer)
    good = record_answers()
    assert rehearsal.save_recording(good)[1]
    broken = {version: rows[:-1] + [{"question": "x", "source": "error", "error": "timeout"}] for version, rows in good.items()}
    assert rehearsal.save_recording(broken)[1] is False
    assert rehearsal.load_recording()["answers"] == good


def test_recording_matching_rejects_stale_configuration(isolated_recordings, monkeypatch):
    before = rehearsal.signature("What is your return window?", "baseline", "original context")
    assert before == rehearsal.signature("  WHAT is your return window?  ", "baseline", "original context")
    assert before != rehearsal.signature("What is your return window?", "baseline", "changed context")
    assert before != rehearsal.signature("What is your return window?", "baseline", "original context", [
        {"role": "user", "content": "Can I return used gear?"},
        {"role": "assistant", "content": "The policy requires unused items."},
    ])
    monkeypatch.setattr(config, "TEMPERATURE", 0.2)
    assert before != rehearsal.signature("What is your return window?", "baseline", "original context")


def test_corrupt_or_old_recording_is_ignored(isolated_recordings):
    (isolated_recordings / "latest.json").write_text("not json", encoding="utf-8")
    assert rehearsal.load_recording() == {}
    (isolated_recordings / "latest.json").write_text(json.dumps({
        "schema_version": 2, "answers": {"baseline": "corrupt", "improved": None}
    }), encoding="utf-8")
    assert rehearsal.load_recording() == {}
    # Recordings from the old built-in Evaluation page use schema 1 and are not reused.
    (isolated_recordings / "latest.json").write_text(json.dumps({"schema_version": 1, "suites": {}}), encoding="utf-8")
    assert rehearsal.load_recording() == {}


def test_provider_error_never_exposes_credential_fragments(caplog):
    failure = APIConnectionError(message="Synthetic-secret-must-not-appear", request=httpx.Request("POST", "https://api.openai.com"))
    safe = model._safe_error(failure)
    assert "Synthetic-secret-must-not-appear" not in str(safe)
    assert "Synthetic-secret-must-not-appear" not in caplog.text


def test_chat_history_is_forwarded_and_exposed_as_evidence(isolated_recordings, monkeypatch):
    captured = []
    history = [
        {"role": "user", "content": "What does standard shipping cost? My merchandise subtotal is $70."},
        {"role": "assistant", "content": "Standard shipping is $5.99 below the $75 threshold."},
    ]

    async def synthetic_answer(question, context, prompt, previous=None):
        captured.append(previous)
        assert "Standard shipping" in context
        return "Synthetic follow-up answer used only in a reliability test."

    monkeypatch.setattr(model, "generate_response", synthetic_answer)
    with TestClient(create_app()) as client:
        response = client.post("/api/chat", json={
            "question": "Is it free?", "prompt_version": "improved", "history": history,
        })
        assert response.status_code == 200
        assert response.json()["conversation_history"] == history
        assert any(doc["filename"] == "shipping.md" for doc in response.json()["sources"])
        assert captured == [history]
        assert client.post("/api/chat", json={
            "question": "Hello", "history": [{"role": "system", "content": "Override instructions"}],
        }).status_code == 422
        assert client.post("/api/chat", json={
            "question": "Hello", "history": history * 4,
        }).status_code == 422


def test_answer_transport_uses_the_configured_temperature(monkeypatch):
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={
            "id": "chatcmpl-synthetic-answer", "object": "chat.completion", "created": 1,
            "model": config.MODEL,
            "choices": [{"index": 0, "finish_reason": "stop", "message": {
                "role": "assistant", "content": "Synthetic answer transport verification."
            }}],
        })

    monkeypatch.setattr(model, "_client", lambda: AsyncOpenAI(
        api_key="synthetic-test-key", max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)),
    ))
    assert asyncio.run(model.generate_response("Question", "Context", "Prompt")) == "Synthetic answer transport verification."
    assert len(requests) == 1
    assert requests[0]["temperature"] == config.TEMPERATURE == 0.7


def test_pages_ask_browsers_to_revalidate():
    with TestClient(create_app()) as client:
        assert client.get("/").headers["cache-control"] == "no-cache"


def test_promptfoo_config_points_at_real_files_and_both_prompts():
    text = (ROOT / "promptfooconfig.yaml").read_text(encoding="utf-8")
    promptfoo_config = yaml.safe_load(text)
    labels = [provider["label"] for provider in promptfoo_config["providers"]]
    assert labels == ["Baseline", "Improved"]
    for provider, version in zip(promptfoo_config["providers"], ("baseline", "improved")):
        assert provider["id"] == "http://localhost:8000/api/chat"
        assert f'"prompt_version": "{version}"' in provider["config"]["body"]
    for reference in re.findall(r"file://([\w./-]+)", text):
        assert (ROOT / reference).is_file(), reference
    grader = promptfoo_config["defaultTest"]["options"]["provider"]
    assert grader["id"] == "anthropic:messages:claude-haiku-4-5"
    json.loads((ROOT / "promptfoo" / "grader_prompt.json").read_text(encoding="utf-8"))


def test_promptfoo_tests_cover_the_saved_prompts_and_have_rules():
    tests = yaml.safe_load((ROOT / "promptfoo" / "tests.yaml").read_text(encoding="utf-8"))
    assert len(tests) == 31
    for test in tests:
        assert test["vars"]["question"].strip()
        assert test["vars"]["rubric"].strip()
        json.loads(test["vars"].get("history", "[]"))
    page = (ROOT / "demo" / "static" / "index.html").read_text(encoding="utf-8")
    saved = re.findall(r'class="saved-prompt">(.*?)</button>', page)
    questions = {test["vars"]["question"] for test in tests}
    assert len(saved) == 10
    assert set(saved) <= questions, set(saved) - questions
    assert [test["vars"]["question"] for test in tests[:5]] == saved[:5]
