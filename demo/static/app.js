"use strict";

// Keep only three successful exchanges for follow-ups. Evaluation remains independent.
const state = {config: null, knowledge: null, busy: false, history: [], turns: [], promptVersion: null};
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
  return "northwind.chatPromptVersion.v3";
}

function storedPrompt() {
  const defaultVersion = "baseline";
  try {
    const saved = localStorage.getItem(promptPreferenceKey());
    return saved === "baseline" || saved === "improved" ? saved : defaultVersion;
  } catch { return defaultVersion; }
}

function setPrompt(version, resetConversation = true, persistSelection = true) {
  const changed = state.promptVersion !== null && state.promptVersion !== version;
  state.promptVersion = version;
  if ($("prompt-version")) $("prompt-version").value = version;
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
  // The original response remains unchanged in the conversation history.
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

async function initialize() {
  setPrompt(storedPrompt(), false, false);
  if ($("prompt-version")) $("prompt-version").addEventListener("change", (event) => setPrompt(event.target.value));
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
    restoreChat();
  }
  try {
    state.config = await api("/api/config");
    const config = state.config;
    $("mode-banner").hidden = config.mode !== "replay";
    if ($("composer-note") && config.mode === "replay") $("composer-note").textContent += " · Replay uses independent saved questions.";
    if (config.mode !== "replay" && !config.api_key_configured) {
      $("configuration-message").textContent = "OpenAI API key is not configured.";
      $("configuration-message").hidden = false;
    }
  } catch (error) {
    $("configuration-message").textContent = `Unable to load application settings: ${error.message}`;
    $("configuration-message").hidden = false;
  }
}

initialize();
