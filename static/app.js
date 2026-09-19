/**
 * AI Document Assistant -- frontend logic.
 *
 * Talks to the FastAPI backend (main.py) at /api/ingest, /api/ask,
 * /api/remove. All dynamic content (questions, answers, document text) is
 * inserted with textContent, never innerHTML, so nothing from the document
 * or the model can inject markup into the page.
 */

const uploadView = document.getElementById("upload-view");
const indexingView = document.getElementById("indexing-view");
const chatView = document.getElementById("chat-view");

const fileInput = document.getElementById("file-input");
const dropzone = document.getElementById("dropzone");
const uploadError = document.getElementById("upload-error");

const docName = document.getElementById("doc-name");
const docMeta = document.getElementById("doc-meta");
const removeBtn = document.getElementById("remove-btn");

const messagesEl = document.getElementById("messages");
const askForm = document.getElementById("ask-form");
const questionInput = document.getElementById("question-input");
const askBtn = document.getElementById("ask-btn");

const sourceItemTemplate = document.getElementById("source-item-template");

function showView(view) {
  uploadView.hidden = view !== "upload";
  indexingView.hidden = view !== "indexing";
  chatView.hidden = view !== "chat";
}

function addMessage(role, text) {
  const el = document.createElement("div");
  el.className = `message ${role}`;
  el.textContent = text;
  messagesEl.appendChild(el);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return el;
}

function addSources(sources) {
  if (!sources || sources.length === 0) return;

  const details = document.createElement("details");
  details.className = "message-sources";

  const summary = document.createElement("summary");
  summary.textContent = `Sources (${sources.length})`;
  details.appendChild(summary);

  for (const src of sources) {
    const node = sourceItemTemplate.content.cloneNode(true);
    node.querySelector(".source-page").textContent = `Page ${src.page}`;
    node.querySelector(".source-score").textContent = `similarity: ${src.score.toFixed(3)}`;
    node.querySelector(".source-text").textContent = src.text;
    details.appendChild(node);
  }

  messagesEl.appendChild(details);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function uploadFile(file) {
  uploadError.hidden = true;

  if (file.size > 25 * 1024 * 1024) {
    uploadError.textContent = "File is too large. The limit is 25MB.";
    uploadError.hidden = false;
    return;
  }

  showView("indexing");

  const formData = new FormData();
  formData.append("file", file);

  let response;
  try {
    response = await fetch("/api/ingest", { method: "POST", body: formData });
  } catch (err) {
    showView("upload");
    uploadError.textContent = "Network error while uploading. Please try again.";
    uploadError.hidden = false;
    return;
  }

  const data = await response.json();

  if (!response.ok || data.error) {
    showView("upload");
    uploadError.textContent = data.error || "Something went wrong. Please try again.";
    uploadError.hidden = false;
    return;
  }

  docName.textContent = data.filename;
  docMeta.textContent = `${data.num_pages} pages · ${data.num_chunks} chunks`;
  messagesEl.innerHTML = "";
  addMessage("assistant", "Document loaded — ask me anything about it.");
  questionInput.value = "";
  showView("chat");
  questionInput.focus();
}

fileInput.addEventListener("change", () => {
  if (fileInput.files.length > 0) uploadFile(fileInput.files[0]);
});

// Drag-and-drop support on the dropzone label.
["dragover", "dragleave", "drop"].forEach((evt) => {
  dropzone.addEventListener(evt, (e) => e.preventDefault());
});
dropzone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (file) uploadFile(file);
});

removeBtn.addEventListener("click", async () => {
  await fetch("/api/remove", { method: "POST" });
  fileInput.value = "";
  messagesEl.innerHTML = "";
  showView("upload");
});

askForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = questionInput.value.trim();
  if (!question) return;

  addMessage("user", question);
  questionInput.value = "";
  autoGrow();
  askBtn.disabled = true;
  questionInput.disabled = true;

  const thinking = addMessage("assistant", "Thinking…");

  let response;
  try {
    response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
  } catch (err) {
    thinking.textContent = "Network error. Please try again.";
    thinking.className = "message error";
    askBtn.disabled = false;
    questionInput.disabled = false;
    questionInput.focus();
    return;
  }

  const data = await response.json();

  if (data.error) {
    thinking.textContent = data.error;
    thinking.className = "message error";
  } else {
    thinking.textContent = data.answer;
    addSources(data.sources);
  }

  askBtn.disabled = false;
  questionInput.disabled = false;
  questionInput.focus();
});

// Enter submits, Shift+Enter inserts a newline.
questionInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    askForm.requestSubmit();
  }
});

// Minimal auto-grow so multi-line questions are easier to write on mobile.
function autoGrow() {
  questionInput.style.height = "auto";
  questionInput.style.height = `${questionInput.scrollHeight}px`;
}
questionInput.addEventListener("input", autoGrow);
