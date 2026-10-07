"use strict";

// Keep only three successful exchanges for follow-ups. Evaluation remains independent.
const state = {config: null, cases: [], evaluations: {baseline: null, improved: null}, knowledge: null, busy: false, history: [], turns: [], promptVersion: null, evaluationRun: null};
// The chat survives a visit to Evaluation (same tab) until New conversation or a prompt switch.
const CHAT_STORAGE_KEY = "northwind.chat.v1";
const MAX_SAVED_TURNS = 40;
const $ = (id) => document.getElementById(id);
const promptName = (version) => version === "improved" ? "Improved" : "Baseline";
const noContext = "No matching company information was found for this question.";

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

async function api(path, options = {}) {
  const response = await fetch(path, {headers: {"Content-Type": "application/json"}, ...options});
  let body;
  try { body = await response.json(); }
  catch { throw new Error("The server returned an unreadable response. Please try again."); }
  if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "The request failed. Please try again.");
  return body;
}

function promptPreferenceKey() {
  // Separate preferences migrate the old automatic Baseline chat default.
  return document.body.dataset.page === "chat" ? "northwind.chatPromptVersion.v2" : "northwind.evaluationPromptVersion.v1";
}

function storedPrompt() {
  const defaultVersion = document.body.dataset.page === "chat" ? "improved" : "baseline";
  try {
    const saved = localStorage.getItem(promptPreferenceKey());
    return saved === "baseline" || saved === "improved" ? saved : defaultVersion;
  } catch { return defaultVersion; }
}

function setPrompt(version, resetConversation = true, persistSelection = true) {
  const changed = state.promptVersion !== null && state.promptVersion !== version;
  state.promptVersion = version;
  if ($("prompt-version")) $("prompt-version").value = version;
  if ($("evaluation-prompt")) $("evaluation-prompt").value = version;
  document.querySelectorAll(".prompt-options [data-prompt]").forEach((option) => option.classList.toggle("active", option.dataset.prompt === version));
  if (persistSelection) {
    try { localStorage.setItem(promptPreferenceKey(), version); } catch { /* Storage may be unavailable. */ }
  }
  if (changed && resetConversation) startNewConversation();
}

function welcomeMessage() {
  const welcome = element("article", "message assistant-message welcome-message");
  welcome.append(element("p", "message-author", "Northwind support"), element("div", "message-bubble", "Hi! I'm the Northwind Outfitters support assistant. I explain the fixed demo catalogue and store policies to help with product questions, shopping, shipping, and returns."));
  return welcome;
}

function saveChat() {
  try {
    sessionStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify({promptVersion: state.promptVersion, history: state.history, turns: state.turns.slice(-MAX_SAVED_TURNS)}));
  } catch { /* Storage may be full or unavailable; the chat still works. */ }
}

function restoreChat() {
  let saved = null;
  try { saved = JSON.parse(sessionStorage.getItem(CHAT_STORAGE_KEY) || "null"); } catch { saved = null; }
  if (!saved || saved.promptVersion !== state.promptVersion || !Array.isArray(saved.turns)) return;
  state.history = Array.isArray(saved.history) ? saved.history : [];
  state.turns = saved.turns;
  for (const turn of state.turns) {
    appendUser(turn.question);
    appendAssistant(turn.data);
  }
}

function startNewConversation() {
  state.history = [];
  state.turns = [];
  try { sessionStorage.removeItem(CHAT_STORAGE_KEY); } catch { /* Storage may be unavailable. */ }
  if (!$("conversation")) return;
  $("conversation").replaceChildren(welcomeMessage());
  $("question").value = "";
  if ($("context-dialog").open) $("context-dialog").close();
}

function dateLabel(timestamp) {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  return Number.isNaN(date.getTime()) ? timestamp : date.toLocaleString([], {dateStyle: "medium", timeStyle: "short"});
}

function sourceLabel(value) {
  // These labels stay explicit even when saved API data has older metadata.
  if (value.result === "ERROR" && !value.response) {
    return value.source === "replay" ? "Replay request — no saved response available" : "Live request — no response available";
  }
  if (value.source === "fallback") return "Fallback response — saved during rehearsal";
  if (value.source === "replay") return "Saved response — rehearsal";
  return value.source_label || "Live response";
}

function sourceBadge(value) {
  return element("span", `source-label ${value.source === "live" ? "live-label" : "saved-label"}`, sourceLabel(value));
}

function scrollChat() {
  const conversation = $("conversation");
  conversation.scrollTop = conversation.scrollHeight;
}

function appendUser(question) {
  const article = element("article", "message user-message");
  article.append(element("p", "message-author", "You"), element("div", "message-bubble", question));
  $("conversation").append(article);
  scrollChat();
}

function assistantBubble(response) {
  const bubble = element("div", "message-bubble");
  // A small text-only renderer handles common emphasis without interpreting HTML.
  // The original response remains unchanged in history and evaluation evidence.
  const displayText = String(response).replace(/\\([*`])/g, "$1");
  const parts = displayText.split(/(\*\*[^*\n]+\*\*|`[^`\n]+`)/g);
  for (const part of parts) {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) bubble.append(element("strong", "", part.slice(2, -2)));
    else if (part.startsWith("`") && part.endsWith("`") && part.length > 2) bubble.append(element("code", "", part.slice(1, -1)));
    else bubble.append(document.createTextNode(part));
  }
  return bubble;
}

function appendAssistant(data) {
  const article = element("article", "message assistant-message");
  article.append(element("p", "message-author", "Northwind support"));
  if (data.source !== "live") article.append(sourceBadge(data));
  article.append(assistantBubble(data.response));
  if (data.source === "fallback" && data.error) article.append(element("p", "fallback-explanation small", `Live request failed: ${data.error}`));
  const footer = element("div", "message-footer");
  const button = element("button", "context-button", "View Context");
  button.type = "button";
  button.addEventListener("click", () => openContext(data));
  footer.append(button, element("span", "small muted", `${promptName(data.prompt_version)} · ${data.model}`));
  article.append(footer);
  $("conversation").append(article);
  scrollChat();
}

async function sendChat(event) {
  event.preventDefault();
  const question = $("question").value.trim();
  if (!question || state.busy) return;
  const promptVersion = $("prompt-version").value;
  state.busy = true;
  $("send-button").disabled = true;
  $("question").disabled = true;
  $("prompt-version").disabled = true;
  $("new-conversation").disabled = true;
  appendUser(question);
  $("question").value = "";
  const loading = element("article", "message assistant-message loading-message");
  loading.setAttribute("role", "status");
  loading.append(element("span", "loading-dot"), element("span", "muted", "Northwind support is responding…"));
  $("conversation").append(loading);
  scrollChat();
  try {
    const history = state.config && state.config.mode === "replay" ? [] : state.history;
    const data = await api("/api/chat", {method: "POST", body: JSON.stringify({question, prompt_version: promptVersion, history})});
    loading.remove();
    appendAssistant(data);
    const historyLimit = state.config ? state.config.max_history_messages || 6 : 6;
    state.history = [...state.history, {role: "user", content: question}, {role: "assistant", content: data.response}].slice(-historyLimit);
    state.turns.push({question, data});
    saveChat();
  } catch (error) {
    loading.remove();
    const article = element("article", "message assistant-message chat-error");
    article.setAttribute("role", "alert");
    article.append(element("p", "message-author", "Unable to get a response"), element("div", "message-bubble", error.message));
    $("conversation").append(article);
    $("question").value = question;
    scrollChat();
  } finally {
    state.busy = false;
    $("send-button").disabled = false;
    $("question").disabled = false;
    $("prompt-version").disabled = false;
    $("new-conversation").disabled = false;
    $("question").focus();
  }
}

function openContext(data) {
  $("context-question").textContent = data.question;
  $("retrieved-context").textContent = data.retrieved_context && data.retrieved_context.trim() ? data.retrieved_context : noContext;
  $("context-metadata").textContent = `${promptName(data.prompt_version)} · ${data.model} · ${sourceLabel(data)}${data.timestamp ? " · " + dateLabel(data.timestamp) : ""}`;
  $("context-sources").textContent = data.sources && data.sources.length ? `Sources: ${data.sources.map((source) => source.filename).join(", ")}` : "";
  const history = data.conversation_history || [];
  const historyDetails = $("conversation-history-details");
  historyDetails.hidden = !history.length;
  historyDetails.open = false;
  const historyContainer = $("conversation-history");
  historyContainer.replaceChildren();
  for (const message of history) {
    const section = element("section", "knowledge-document");
    section.append(element("h4", "", message.role === "user" ? "You" : "Northwind support"), element("pre", "evidence-text", message.content));
    historyContainer.append(section);
  }
  $("knowledge-details").open = false;
  $("context-dialog").showModal();
}

async function loadKnowledge() {
  if (!$("knowledge-details").open) return;
  const container = $("full-knowledge");
  container.replaceChildren(element("p", "muted", "Loading company information…"));
  try {
    state.knowledge = await api("/api/knowledge");
    container.replaceChildren();
    for (const item of state.knowledge) {
      const section = element("section", "knowledge-document");
      section.append(element("h4", "", item.filename), element("pre", "evidence-text", item.content));
      container.append(section);
    }
    if (!state.knowledge.length) container.append(element("p", "muted", "No company information is available."));
  } catch (error) {
    const message = element("p", "error-text", error.message);
    message.setAttribute("role", "alert");
    container.replaceChildren(message);
    const retry = element("button", "button quiet", "Try again");
    retry.type = "button";
    retry.addEventListener("click", loadKnowledge);
    container.append(retry);
  }
}

function resultBadge(result) {
  const valid = ["PASS", "FAIL", "ERROR"].includes(result) ? result : "ERROR";
  return element("span", `result-badge result-${valid.toLowerCase()}`, valid);
}

function detailBlock(label, value, preformatted = false) {
  const block = element("div", "result-detail-block");
  block.append(element("h4", "", label), element(preformatted ? "pre" : "p", preformatted ? "evidence-text" : "", value));
  return block;
}

function evaluationProgress(suite) {
  const completed = Number.isInteger(suite.completed_count) ? suite.completed_count : suite.results.length;
  const total = Number.isInteger(suite.total_count) ? suite.total_count : (state.cases.length || suite.results.length);
  return {completed, total, partial: Boolean(suite.stopped) || completed < total};
}

function renderResults(suite) {
  const progress = evaluationProgress(suite);
  $("results-heading").textContent = `${promptName(suite.prompt_version)}${progress.partial ? " partial" : ""} automated results`;
  const progressLabel = progress.partial ? `${suite.stopped ? "Stopped" : "Incomplete"} · ${progress.completed} of ${progress.total} scenarios completed` : "";
  $("run-metadata").textContent = [progressLabel, suite.model, `Temperature ${suite.temperature}`, dateLabel(suite.timestamp)].filter(Boolean).join(" · ");
  const source = $("run-source");
  source.replaceChildren();
  const savedCount = suite.results.filter((result) => result.response && (result.source === "replay" || result.source === "fallback")).length;
  const fallbackCount = suite.results.filter((result) => result.source === "fallback").length;
  if (suite.mode === "replay" || savedCount) {
    source.hidden = false;
    source.append(element("span", "source-label saved-label", suite.mode === "replay" ? "REPLAY MODE — Saved responses" : fallbackCount ? `Contains ${fallbackCount} fallback response${fallbackCount === 1 ? "" : "s"} saved during rehearsal` : "Contains saved rehearsal responses"));
    const sourceNote = suite.stopped && !suite.results.length ? "No saved scenarios finished before the run stopped." : savedCount ? "Saved answers use their recorded rehearsal evaluations." : "No compatible saved answers were available. Replay makes no live API calls.";
    source.append(element("p", "small muted", sourceNote));
  } else source.hidden = true;
  const container = $("evaluation-results");
  container.className = "table-scroll";
  container.replaceChildren();
  if (progress.partial && !suite.results.length) {
    container.className = "empty-results";
    container.append(element("p", "", "No scenarios finished before this run ended."), element("p", "muted", "Previous completed runs remain in the comparison."));
    return;
  }
  const table = element("table", "results-table");
  const thead = element("thead");
  const headings = element("tr");
  for (const label of ["Scenario / question", "Model response", "Evaluation method", "Automated result", "Automated reason", "Prompt / model"]) {
    const th = element("th", "", label);
    th.scope = "col";
    headings.append(th);
  }
  thead.append(headings);
  const tbody = element("tbody");
  suite.results.forEach((result, index) => {
    const row = element("tr", "result-row");
    const scenario = element("td", "scenario-cell");
    scenario.append(element("strong", "", result.name), element("p", "small scenario-question", result.question));
    const toggle = element("button", "context-button", "View details");
    toggle.type = "button";
    toggle.setAttribute("aria-expanded", "false");
    const detailId = `result-detail-${index}`;
    toggle.setAttribute("aria-controls", detailId);
    scenario.append(toggle);
    const response = element("td", "response-cell");
    if (result.source === "replay" || result.source === "fallback") response.append(sourceBadge(result));
    response.append(element("p", "response-preview", result.response || (result.result === "ERROR" ? "No response available." : "")));
    const method = element("td", "method-cell", result.evaluation_method);
    const outcome = element("td");
    outcome.append(resultBadge(result.result));
    const reason = element("td", "reason-cell", result.reason);
    const metadata = element("td", "metadata-cell");
    metadata.append(element("strong", "", promptName(result.prompt_version || suite.prompt_version)), element("p", "small muted model-name", result.model || suite.model));
    row.append(scenario, response, method, outcome, reason, metadata);
    const detailRow = element("tr", "result-detail-row");
    detailRow.id = detailId;
    detailRow.hidden = true;
    const detailCell = element("td");
    detailCell.colSpan = 6;
    const detail = element("div", "result-detail");
    detail.append(sourceBadge(result));
    if (result.error) detail.append(detailBlock("Request or grading error", result.error));
    detail.append(detailBlock("User question", result.question), detailBlock("Retrieved Context", result.retrieved_context && result.retrieved_context.trim() ? result.retrieved_context : noContext, true), detailBlock("Actual model response", result.response || "No response available.", true), detailBlock("Expected behavior", result.expected_behavior), detailBlock("Automated result", result.result), detailBlock("Evaluation method", result.evaluation_method), detailBlock("Automated evaluation reason", result.reason));
    if (result.categories && result.categories.length) detail.append(detailBlock("Evaluation dimensions", result.categories.join(", ")));
    detail.append(element("p", "small muted", `${promptName(result.prompt_version || suite.prompt_version)} · ${result.model || suite.model} · ${dateLabel(result.timestamp || suite.timestamp)}`));
    detailCell.append(detail);
    detailRow.append(detailCell);
    toggle.addEventListener("click", () => {
      detailRow.hidden = !detailRow.hidden;
      toggle.setAttribute("aria-expanded", String(!detailRow.hidden));
      toggle.textContent = detailRow.hidden ? "View details" : "Hide details";
    });
    tbody.append(row, detailRow);
  });
  table.append(thead, tbody);
  container.append(table);
}

function renderComparison() {
  const body = $("comparison-body");
  body.replaceChildren();
  const scenarios = state.cases.length ? state.cases : (state.evaluations.baseline || state.evaluations.improved || {results: []}).results;
  for (const scenario of scenarios) {
    const row = element("tr");
    const heading = element("th", "", scenario.name);
    heading.scope = "row";
    row.append(heading);
    for (const version of ["baseline", "improved"]) {
      const cell = element("td");
      const suite = state.evaluations[version];
      const result = suite && suite.results.find((item) => item.id === scenario.id);
      if (result) {
        cell.append(resultBadge(result.result));
        if (result.source === "replay" || result.source === "fallback") cell.append(element("span", "comparison-source small", sourceLabel(result)));
      } else cell.append(element("span", "muted", "Not run"));
      row.append(cell);
    }
    body.append(row);
  }
  if (!scenarios.length) {
    const row = element("tr");
    const cell = element("td", "muted", "Scenario information could not be loaded. Run the suite to populate results.");
    cell.colSpan = 3;
    row.append(cell);
    body.append(row);
  }
  $("comparison-metadata").textContent = ["baseline", "improved"].filter((version) => state.evaluations[version]).map((version) => {
    const suite = state.evaluations[version];
    return `${promptName(version)}: ${suite.model}, ${dateLabel(suite.timestamp)}${suite.mode === "replay" ? " (replay mode)" : ""}`;
  }).join(" · ");
}

async function runEvaluation() {
  if (state.busy) return;
  const version = $("evaluation-prompt").value;
  const runId = typeof globalThis.crypto?.randomUUID === "function" ? globalThis.crypto.randomUUID() : "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (letter) => {
    const random = Math.floor(Math.random() * 16);
    return (letter === "x" ? random : (random & 3) | 8).toString(16);
  });
  const run = {id: runId, stopRequested: false, settled: false};
  state.evaluationRun = run;
  state.busy = true;
  $("run-evaluation").disabled = true;
  $("stop-evaluation").disabled = false;
  $("evaluation-prompt").disabled = true;
  $("evaluation-results").setAttribute("aria-busy", "true");
  const status = $("evaluation-status");
  status.className = "evaluation-status running";
  const replay = state.config && state.config.mode === "replay";
  const scenarios = state.cases.length ? `${state.cases.length} scenarios` : "the scenarios";
  const progress = replay ? `Loading saved rehearsal results for ${scenarios} with the ${promptName(version)} prompt…` : `Running ${scenarios} with the ${promptName(version)} prompt… A full suite can take a few minutes.`;
  status.replaceChildren(element("span", "loading-dot"), element("span", "", progress));
  try {
    const suite = await api("/api/evaluate", {method: "POST", body: JSON.stringify({prompt_version: version, run_id: run.id})});
    run.settled = true;
    if (state.evaluationRun !== run) return;
    const progress = evaluationProgress(suite);
    renderResults(suite);
    if (!progress.partial) {
      state.evaluations[version] = suite;
      renderComparison();
    }
    const counts = ["PASS", "FAIL", "ERROR"].map((outcome) => `${suite.results.filter((result) => result.result === outcome).length} ${outcome}`).join(" · ");
    const completionCount = `${progress.completed} of ${progress.total} scenarios completed.`;
    if (progress.partial) {
      status.className = "evaluation-status stopped";
      status.textContent = `${suite.stopped ? "Stopped." : "Evaluation ended early."} ${completionCount} ${suite.results.length ? counts + " " : ""}Previous completed comparison kept.`;
      return;
    }
    status.className = "evaluation-status complete";
    const savedAnswers = suite.results.filter((result) => result.response && result.source === "replay").length;
    const completion = suite.mode === "replay" ? (savedAnswers ? `Loaded ${savedAnswers} saved rehearsal answers.` : "No compatible saved answers were available.") : "Evaluation complete.";
    status.textContent = `${completion} ${completionCount} ${counts}`;
  } catch (error) {
    run.settled = true;
    if (state.evaluationRun !== run) return;
    status.className = "evaluation-status error";
    status.textContent = `Evaluation could not be completed: ${error.message}`;
  } finally {
    run.settled = true;
    if (state.evaluationRun === run) {
      state.evaluationRun = null;
      state.busy = false;
      $("run-evaluation").disabled = false;
      $("stop-evaluation").disabled = true;
      $("evaluation-prompt").disabled = false;
      $("evaluation-results").setAttribute("aria-busy", "false");
    }
  }
}

async function stopEvaluation() {
  const run = state.evaluationRun;
  if (!run || run.stopRequested || run.settled) return;
  run.stopRequested = true;
  $("stop-evaluation").disabled = true;
  const status = $("evaluation-status");
  status.className = "evaluation-status stopping";
  status.replaceChildren(element("span", "loading-dot"), element("span", "", "Stopping… Completed results will stay visible."));
  try {
    // Keep the original evaluation request open: it returns completed rows.
    await api("/api/evaluate/stop", {method: "POST", body: JSON.stringify({run_id: run.id})});
  } catch (error) {
    if (state.evaluationRun !== run || run.settled) return;
    run.stopRequested = false;
    $("stop-evaluation").disabled = false;
    status.className = "evaluation-status error";
    status.textContent = `Could not stop the evaluation: ${error.message} The run is still active; try Stop again.`;
  }
}

async function initializeEvaluation() {
  $("run-evaluation").addEventListener("click", runEvaluation);
  $("stop-evaluation").addEventListener("click", stopEvaluation);
  const results = await Promise.allSettled([api("/api/test-cases"), api("/api/evaluations")]);
  if (results[0].status === "fulfilled") state.cases = results[0].value;
  if (results[1].status === "fulfilled") state.evaluations = results[1].value;
  const errors = results.filter((result) => result.status === "rejected");
  if (errors.length) {
    $("evaluation-status").className = "evaluation-status error";
    $("evaluation-status").textContent = errors.map((result) => result.reason.message).join(" ");
  }
  renderComparison();
  const available = [state.evaluations.baseline, state.evaluations.improved].filter(Boolean);
  available.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
  if (available.length) renderResults(available[0]);
  $("run-evaluation").disabled = false;
}

async function initialize() {
  setPrompt(storedPrompt(), false, false);
  if ($("prompt-version")) $("prompt-version").addEventListener("change", (event) => setPrompt(event.target.value));
  if ($("evaluation-prompt")) $("evaluation-prompt").addEventListener("change", (event) => setPrompt(event.target.value));
  if (document.body.dataset.page === "chat") {
    $("chat-form").addEventListener("submit", sendChat);
    $("question").addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
        event.preventDefault();
        $("chat-form").requestSubmit();
      }
    });
    document.querySelectorAll(".saved-prompt").forEach((button) => button.addEventListener("click", () => {
      if (state.busy) return;
      $("question").value = button.textContent;
      $("question").focus();
    }));
    $("close-context").addEventListener("click", () => $("context-dialog").close());
    $("context-dialog").addEventListener("click", (event) => {
      if (event.target !== $("context-dialog")) return;
      const rect = $("context-dialog").getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) $("context-dialog").close();
    });
    $("knowledge-details").addEventListener("toggle", loadKnowledge);
    $("new-conversation").addEventListener("click", () => { if (!state.busy) startNewConversation(); });
    // Saved prompts are an open sidebar on wide screens but start collapsed on phones.
    if (window.matchMedia("(max-width: 850px)").matches) $("saved-prompts").open = false;
    restoreChat();
  }
  try {
    state.config = await api("/api/config");
    const config = state.config;
    if ($("model-settings")) $("model-settings").textContent = `${config.model} · Temperature ${config.temperature}`;
    if ($("evaluation-model")) $("evaluation-model").textContent = `Answers: ${config.model} · Temperature ${config.temperature} · Grader: ${config.grader_model} · Temperature ${config.grader_temperature}`;
    $("mode-banner").hidden = config.mode !== "replay";
    if ($("composer-note") && config.mode === "replay") $("composer-note").textContent += " · Replay uses independent saved questions.";
    if (config.mode !== "replay" && !config.api_key_configured) {
      $("configuration-message").textContent = "OpenAI API key is not configured.";
      $("configuration-message").hidden = false;
    } else if (config.mode !== "replay" && document.body.dataset.page === "evaluation" && !config.grader_key_configured) {
      $("configuration-message").textContent = "Anthropic API key for the grader is not configured. Add ANTHROPIC_API_KEY to .env.";
      $("configuration-message").hidden = false;
    }
  } catch (error) {
    if ($("model-settings")) $("model-settings").textContent = "Model settings unavailable.";
    $("configuration-message").textContent = `Unable to load application settings: ${error.message}`;
    $("configuration-message").hidden = false;
  }
  if (document.body.dataset.page === "evaluation") await initializeEvaluation();
}

initialize();
