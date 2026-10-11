const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const messages = document.getElementById("messages");
const welcome = document.getElementById("welcome");
const sendButton = document.getElementById("send-button");
const webToggle = document.getElementById("web-toggle");
const uploadInput = document.getElementById("pdf-file");
const uploadButton = document.getElementById("upload-button");
const uploadStatus = document.getElementById("upload-status");
const healthStatus = document.getElementById("health-status");

function addMessage(role, text, sources = []) {
  welcome.hidden = true;
  const wrapper = document.createElement("article");
  wrapper.className = `message ${role}`;
  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "YOU" : "AI";
  const content = document.createElement("div");
  content.className = "message-content";
  const label = document.createElement("div");
  label.className = "message-label";
  label.textContent = role === "user" ? "YOU" : "INDUSTRIAL PRODUCT ASSISTANT";
  const body = document.createElement("div");
  body.className = "message-text";
  body.textContent = text;
  content.append(label, body);

  if (sources.length) {
    const sourceTitle = document.createElement("div");
    sourceTitle.className = "message-label";
    sourceTitle.style.marginTop = "14px";
    sourceTitle.textContent = `SOURCES (${sources.length})`;
    const sourceList = document.createElement("div");
    sourceList.className = "sources";
    sources.forEach((source) => {
      const card = document.createElement("div");
      card.className = "source-card";
      const type = document.createElement("span");
      type.className = "source-type";
      type.textContent = source.type === "web" ? "Web" : "Document";
      card.append(type);
      if (source.url) {
        const link = document.createElement("a");
        link.href = source.url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = source.title || source.url;
        card.append(link);
      } else {
        const title = document.createElement("strong");
        title.textContent = source.title || "Internal document";
        card.append(title);
      }
      if (source.excerpt) {
        const excerpt = document.createElement("p");
        excerpt.textContent = source.excerpt;
        card.append(excerpt);
      }
      sourceList.append(card);
    });
    content.append(sourceTitle, sourceList);
  }
  wrapper.append(avatar, content);
  messages.append(wrapper);
  wrapper.scrollIntoView({ behavior: "smooth", block: "nearest" });
  return wrapper;
}

async function sendMessage(message) {
  addMessage("user", message);
  const pending = addMessage("assistant", "Searching available evidence…");
  pending.querySelector(".message-text").classList.add("typing");
  sendButton.disabled = true;
  input.disabled = true;
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, use_web: webToggle.checked }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Chat request failed.");
    pending.querySelector(".message-text").classList.remove("typing");
    pending.querySelector(".message-text").textContent = data.answer;
    if (data.sources?.length) {
      const sourceBox = document.createElement("div");
      sourceBox.className = "sources";
      data.sources.forEach((source) => {
        const card = document.createElement("div");
        card.className = "source-card";
        const type = document.createElement("span");
        type.className = "source-type";
        type.textContent = source.type === "web" ? "Web" : "Document";
        card.append(type);
        if (source.url) {
          const link = document.createElement("a");
          link.href = source.url;
          link.target = "_blank";
          link.rel = "noopener noreferrer";
          link.textContent = source.title || source.url;
          card.append(link);
        } else {
          const title = document.createElement("strong");
          title.textContent = source.title || "Internal document";
          card.append(title);
        }
        if (source.excerpt) {
          const excerpt = document.createElement("p");
          excerpt.textContent = source.excerpt;
          card.append(excerpt);
        }
        sourceBox.append(card);
      });
      const sourceTitle = document.createElement("div");
      sourceTitle.className = "message-label";
      sourceTitle.style.marginTop = "14px";
      sourceTitle.textContent = `SOURCES (${data.sources.length})`;
      pending.querySelector(".message-content").append(sourceTitle, sourceBox);
    }
  } catch (error) {
    pending.querySelector(".message-text").classList.remove("typing");
    pending.querySelector(".message-text").textContent = `Error: ${error.message}`;
  } finally {
    sendButton.disabled = false;
    input.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  await sendMessage(message);
});

document.querySelectorAll(".suggestion").forEach((button) => {
  button.addEventListener("click", () => {
    input.value = button.textContent.trim();
    input.focus();
  });
});

uploadButton.addEventListener("click", async () => {
  const file = uploadInput.files?.[0];
  if (!file) {
    uploadStatus.textContent = "Choose a PDF first.";
    return;
  }
  const formData = new FormData();
  formData.append("file", file);
  uploadButton.disabled = true;
  uploadStatus.textContent = "Uploading and indexing PDF…";
  try {
    const response = await fetch("/api/ingest", { method: "POST", body: formData });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Upload failed.");
    uploadStatus.textContent = result.warning || `Indexed ${result.chunks_added} text chunks from ${result.filename}.`;
    await refreshHealth();
  } catch (error) {
    uploadStatus.textContent = `Error: ${error.message}`;
  } finally {
    uploadButton.disabled = false;
  }
});

async function refreshHealth() {
  try {
    const response = await fetch("/api/health");
    const health = await response.json();
    healthStatus.textContent = `${health.indexed_chunks} indexed chunks · ${health.tavily_enabled ? "Web search configured" : "Web search not configured"}`;
  } catch {
    healthStatus.textContent = "Could not check service status.";
  }
}
refreshHealth();
