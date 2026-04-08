const messagesEl = document.getElementById("messages");
const inputEl = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const statusBadge = document.getElementById("status-badge");
const newChatBtn = document.getElementById("new-chat-btn");
const sidebarToggle = document.getElementById("sidebar-toggle");
const sidebar = document.querySelector(".sidebar");

let sessionId = null;

// === Event Listeners ===

inputEl.addEventListener("input", () => {
    // Auto-resize textarea
    inputEl.style.height = "auto";
    inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + "px";
    sendBtn.disabled = !inputEl.value.trim();
});

inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (inputEl.value.trim()) sendMessage();
    }
});

sendBtn.addEventListener("click", () => {
    if (inputEl.value.trim()) sendMessage();
});

newChatBtn.addEventListener("click", () => {
    // Delete server-side session to free memory
    if (sessionId) {
        fetch(`/api/chat/${sessionId}`, { method: "DELETE" }).catch(() => {});
    }
    sessionId = null;
    messagesEl.innerHTML = `
        <div class="welcome-message">
            <div class="welcome-icon">&#x1F44B;</div>
            <h2>안녕하세요! Job Scanner입니다</h2>
            <p>AI/개발 직군 취업을 도와드리는 AI 에이전트예요.<br>
            왼쪽 메뉴에서 기능을 선택하거나, 자유롭게 질문해 주세요!</p>
        </div>
    `;
    closeSidebar();
});

sidebarToggle.addEventListener("click", () => {
    sidebar.classList.toggle("open");
});

// Feature buttons
document.querySelectorAll(".feature-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
        inputEl.value = btn.dataset.prompt;
        inputEl.dispatchEvent(new Event("input"));
        sendMessage();
        closeSidebar();
    });
});

// Close sidebar when clicking outside on mobile
document.addEventListener("click", (e) => {
    if (
        sidebar.classList.contains("open") &&
        !sidebar.contains(e.target) &&
        e.target !== sidebarToggle
    ) {
        closeSidebar();
    }
});

// === Functions ===

function closeSidebar() {
    sidebar.classList.remove("open");
}

function addMessage(role, content, intent) {
    // Remove welcome message if present
    const welcome = messagesEl.querySelector(".welcome-message");
    if (welcome) welcome.remove();

    const msg = document.createElement("div");
    msg.className = `message ${role}`;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = role === "user" ? "U" : "AI";

    const contentEl = document.createElement("div");
    contentEl.className = "message-content";

    if (role === "ai") {
        let html = "";
        if (intent && intent !== "chitchat") {
            const intentLabels = {
                job_search: "공고 검색",
                resume_match: "이력서 매칭",
                skill_gap: "역량 갭 분석",
                trend: "트렌드 분석",
            };
            // DOMPurify.sanitize on the label as extra precaution
            const label = intentLabels[intent] || intent;
            html += `<span class="intent-badge">${DOMPurify.sanitize(label)}</span>`;
        }
        html += marked.parse(content);
        contentEl.innerHTML = DOMPurify.sanitize(html);
    } else {
        // user messages and error messages: always textContent (XSS-safe)
        contentEl.textContent = content;
    }

    msg.appendChild(avatar);
    msg.appendChild(contentEl);
    messagesEl.appendChild(msg);
    scrollToBottom();
}

function addLoadingMessage() {
    const msg = document.createElement("div");
    msg.className = "message ai";
    msg.id = "loading-message";

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = "AI";

    const contentEl = document.createElement("div");
    contentEl.className = "message-content";
    contentEl.innerHTML = `
        <div class="loading-dots">
            <span></span><span></span><span></span>
        </div>
    `;

    msg.appendChild(avatar);
    msg.appendChild(contentEl);
    messagesEl.appendChild(msg);
    scrollToBottom();
}

function removeLoadingMessage() {
    const el = document.getElementById("loading-message");
    if (el) el.remove();
}

function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

function setLoading(loading) {
    sendBtn.disabled = loading;
    inputEl.disabled = loading;
    if (loading) {
        statusBadge.textContent = "Thinking...";
        statusBadge.classList.add("loading");
    } else {
        statusBadge.textContent = "Ready";
        statusBadge.classList.remove("loading");
    }
}

async function sendMessage() {
    const message = inputEl.value.trim();
    if (!message) return;

    // Add user message
    addMessage("user", message);
    inputEl.value = "";
    inputEl.style.height = "auto";
    sendBtn.disabled = true;

    // Show loading
    setLoading(true);
    addLoadingMessage();

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message, session_id: sessionId }),
        });

        removeLoadingMessage();

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || "서버 오류가 발생했습니다.");
        }

        const data = await res.json();
        sessionId = data.session_id;
        addMessage("ai", data.response, data.intent);
    } catch (err) {
        removeLoadingMessage();
        addMessage("error", `오류가 발생했습니다: ${err.message}`);
    } finally {
        setLoading(false);
        inputEl.focus();
    }
}
