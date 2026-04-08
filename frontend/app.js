// === DOM Elements ===
const messagesEl = document.getElementById("messages");
const inputEl = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const statusBadge = document.getElementById("status-badge");
const newChatBtn = document.getElementById("new-chat-btn");
const sidebarToggle = document.getElementById("sidebar-toggle");
const sidebar = document.getElementById("sidebar");
const profileBtn = document.getElementById("profile-btn");
const profileModal = document.getElementById("profile-modal");
const modalClose = document.getElementById("modal-close");
const profileCancel = document.getElementById("profile-cancel");
const profileForm = document.getElementById("profile-form");
const loginSection = document.getElementById("login-section");
const userSection = document.getElementById("user-section");
const googleLoginBtn = document.getElementById("google-login-btn");
const logoutBtn = document.getElementById("logout-btn");

let sessionId = null;
let currentUser = null;
let userProfile = null;

// === Init ===
async function init() {
    const savedProfile = localStorage.getItem("jobscanner_profile");
    if (savedProfile) {
        userProfile = JSON.parse(savedProfile);
    }

    // Server is the single source of truth for auth
    try {
        const res = await fetch("/api/auth/me");
        const data = await res.json();
        if (data.authenticated) {
            currentUser = { name: data.name, email: data.email, picture: data.picture };
            localStorage.setItem("jobscanner_user", JSON.stringify(currentUser));
            showLoggedInState();
            if (!savedProfile) openProfileModal();
        } else {
            localStorage.removeItem("jobscanner_user");
        }
    } catch {
        // Network error: use localStorage as fallback
        const saved = localStorage.getItem("jobscanner_user");
        if (saved) {
            currentUser = JSON.parse(saved);
            showLoggedInState();
        }
    }
}

// === Auth ===
googleLoginBtn.addEventListener("click", async () => {
    try {
        const res = await fetch("/api/auth/google/url");
        const data = await res.json();
        if (data.url) {
            window.location.href = data.url;
        } else {
            // Fallback: demo login for development
            demoLogin();
        }
    } catch {
        demoLogin();
    }
});

function demoLogin() {
    currentUser = {
        name: "사용자",
        email: "user@example.com",
        picture: null,
    };
    localStorage.setItem("jobscanner_user", JSON.stringify(currentUser));
    showLoggedInState();
    // Show onboarding for first-time users
    if (!localStorage.getItem("jobscanner_profile")) {
        openProfileModal();
    }
}

function showLoggedInState() {
    loginSection.style.display = "none";
    userSection.classList.add("logged-in");
    document.getElementById("user-name").textContent = currentUser.name;
    document.getElementById("user-email").textContent = currentUser.email;
    profileBtn.classList.add("visible");

    const avatarEl = document.getElementById("user-avatar");
    avatarEl.textContent = "";
    const isHttps = currentUser.picture?.startsWith("https://");
    if (isHttps) {
        const img = document.createElement("img");
        img.src = currentUser.picture;
        img.alt = "avatar";
        avatarEl.appendChild(img);
    } else {
        avatarEl.textContent = currentUser.name.charAt(0).toUpperCase();
    }
}

logoutBtn.addEventListener("click", () => {
    currentUser = null;
    userProfile = null;
    localStorage.removeItem("jobscanner_user");
    localStorage.removeItem("jobscanner_profile");
    loginSection.style.display = "";
    userSection.classList.remove("logged-in");
    profileBtn.classList.remove("visible");
});

// === Profile Modal ===
profileBtn.addEventListener("click", openProfileModal);
modalClose.addEventListener("click", closeProfileModal);
profileCancel.addEventListener("click", closeProfileModal);

profileModal.addEventListener("click", (e) => {
    if (e.target === profileModal) closeProfileModal();
});

function openProfileModal() {
    profileModal.classList.add("active");
    // Populate if profile exists
    if (userProfile) {
        document.getElementById("user-fullname").value = userProfile.fullName || "";
        document.getElementById("user-age").value = userProfile.age || "";
        document.getElementById("career-type").value = userProfile.careerType || "";
        document.getElementById("job-category").value = userProfile.jobCategory || "";
        document.getElementById("education").value = userProfile.education || "";
        document.getElementById("major").value = userProfile.major || "";
        document.getElementById("salary-range").value = userProfile.salaryRange || "";
        document.getElementById("location-pref").value = userProfile.locationPref || "";

        // Restore tech tags
        selectedTechs.clear();
        if (userProfile.techStack) {
            userProfile.techStack.split(", ").forEach((t) => { if (t) selectedTechs.add(t); });
            updateTechUI();
        }
    }
}

function closeProfileModal() {
    profileModal.classList.remove("active");
}

// File upload handlers
const resumeUpload = document.getElementById("resume-upload");
const resumeFile = document.getElementById("resume-file");
const portfolioUpload = document.getElementById("portfolio-upload");
const portfolioFile = document.getElementById("portfolio-file");

resumeUpload.addEventListener("click", () => resumeFile.click());
resumeFile.addEventListener("change", () => {
    const name = resumeFile.files[0]?.name;
    document.getElementById("resume-file-name").textContent = name || "";
});

portfolioUpload.addEventListener("click", () => portfolioFile.click());
portfolioFile.addEventListener("change", () => {
    const name = portfolioFile.files[0]?.name;
    document.getElementById("portfolio-file-name").textContent = name || "";
});

// === Tech Stack Tag System ===
const selectedTechs = new Set();
const techSearch = document.getElementById("tech-search");
const techSuggestions = document.getElementById("tech-suggestions");
const techTagsContainer = document.getElementById("tech-tags-selected");
const techStackHidden = document.getElementById("tech-stack");

const ALL_TECHS = [
    "Python", "JavaScript", "TypeScript", "Java", "Go", "C++", "C#", "Rust", "Kotlin", "Swift",
    "React", "Next.js", "Vue.js", "Angular", "Svelte", "HTML/CSS", "Tailwind CSS",
    "FastAPI", "Django", "Flask", "Spring", "Node.js", "Express.js", "NestJS",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "SQLite",
    "Docker", "Kubernetes", "AWS", "GCP", "Azure", "Terraform", "GitHub Actions",
    "PyTorch", "TensorFlow", "Hugging Face", "LangChain", "LangGraph", "OpenAI API", "RAG",
    "Spark", "Kafka", "Airflow", "dbt", "Pandas", "NumPy", "Scikit-learn",
    "Git", "Linux", "CI/CD", "REST API", "GraphQL", "gRPC", "SQL",
    "ChromaDB", "Pinecone", "FAISS", "MLflow", "Jupyter",
];

function addTech(tech) {
    if (selectedTechs.has(tech)) return;
    selectedTechs.add(tech);
    updateTechUI();
}

function removeTech(tech) {
    selectedTechs.delete(tech);
    updateTechUI();
}

function updateTechUI() {
    // Update hidden input
    techStackHidden.value = Array.from(selectedTechs).join(", ");

    // Update selected tags
    techTagsContainer.innerHTML = "";
    selectedTechs.forEach((tech) => {
        const tag = document.createElement("span");
        tag.className = "tech-tag";
        tag.textContent = tech;

        const removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.className = "tech-tag-remove";
        removeBtn.textContent = "\u00d7";
        removeBtn.addEventListener("click", () => removeTech(tech));

        tag.appendChild(removeBtn);
        techTagsContainer.appendChild(tag);
    });

    // Update chip states
    document.querySelectorAll(".tech-chip").forEach((chip) => {
        chip.classList.toggle("selected", selectedTechs.has(chip.dataset.tech));
    });
}

// Click on popular tech chips
document.querySelectorAll(".tech-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
        const tech = chip.dataset.tech;
        if (selectedTechs.has(tech)) {
            removeTech(tech);
        } else {
            addTech(tech);
        }
    });
});

// Search input
techSearch.addEventListener("input", () => {
    const query = techSearch.value.trim().toLowerCase();
    if (query.length < 1) {
        techSuggestions.classList.remove("active");
        return;
    }

    const matches = ALL_TECHS.filter(
        (t) => t.toLowerCase().includes(query) && !selectedTechs.has(t)
    ).slice(0, 6);

    if (matches.length === 0) {
        techSuggestions.classList.remove("active");
        return;
    }

    techSuggestions.innerHTML = "";
    matches.forEach((tech) => {
        const item = document.createElement("div");
        item.className = "tech-suggestion-item";
        item.textContent = tech;
        item.addEventListener("click", () => {
            addTech(tech);
            techSearch.value = "";
            techSuggestions.classList.remove("active");
        });
        techSuggestions.appendChild(item);
    });
    techSuggestions.classList.add("active");
});

techSearch.addEventListener("blur", () => {
    setTimeout(() => techSuggestions.classList.remove("active"), 200);
});

// === Profile Form Submit ===
profileForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    userProfile = {
        fullName: document.getElementById("user-fullname").value,
        age: document.getElementById("user-age").value,
        careerType: document.getElementById("career-type").value,
        jobCategory: document.getElementById("job-category").value,
        techStack: document.getElementById("tech-stack").value,
        education: document.getElementById("education").value,
        major: document.getElementById("major").value,
        salaryRange: document.getElementById("salary-range").value,
        locationPref: document.getElementById("location-pref").value,
    };

    localStorage.setItem("jobscanner_profile", JSON.stringify(userProfile));

    // Upload resume if selected
    if (resumeFile.files[0]) {
        await uploadFile(resumeFile.files[0], "resume");
    }
    if (portfolioFile.files[0]) {
        await uploadFile(portfolioFile.files[0], "portfolio");
    }

    closeProfileModal();

    // Send profile context to chat
    const profileSummary = buildProfileSummary();
    if (profileSummary) {
        inputEl.value = profileSummary;
        sendMessage();
    }
});

async function uploadFile(file, type) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("type", type);
    try {
        await fetch("/api/profile/upload", { method: "POST", body: formData });
    } catch (err) {
        console.warn("File upload failed:", err);
    }
}

function buildProfileSummary() {
    if (!userProfile) return null;
    const parts = [];
    const careerLabels = { new: "신입", junior: "주니어(1~3년)", mid: "미드레벨(4~7년)", senior: "시니어(8년+)" };
    const jobLabels = { backend: "백엔드", frontend: "프론트엔드", fullstack: "풀스택", "ai-ml": "AI/ML Engineer", data: "데이터 엔지니어", devops: "DevOps", other: "기타" };

    if (userProfile.careerType) parts.push(`경력: ${careerLabels[userProfile.careerType] || userProfile.careerType}`);
    if (userProfile.jobCategory) parts.push(`희망 직군: ${jobLabels[userProfile.jobCategory] || userProfile.jobCategory}`);
    if (userProfile.techStack) parts.push(`보유 기술: ${userProfile.techStack}`);
    if (userProfile.education) parts.push(`학력: ${userProfile.education}`);

    if (!parts.length) return null;
    return `내 프로필 정보를 기반으로 맞는 공고 추천해줘. ${parts.join(", ")}`;
}

// === Chat ===
inputEl.addEventListener("input", () => {
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
    if (sessionId) {
        fetch(`/api/chat/${sessionId}`, { method: "DELETE" }).catch(() => {});
    }
    sessionId = null;
    messagesEl.innerHTML = `
        <div class="welcome-message">
            <div class="welcome-logo">
                <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            </div>
            <h2>Job Scanner</h2>
            <p>AI/개발 직군 취업을 도와드리는 채용 분석 에이전트입니다.<br>궁금한 것을 자유롭게 물어보세요.</p>
            <div class="quick-actions">
                <button class="quick-chip" data-prompt="AI Engineer 공고 찾아줘">공고 검색</button>
                <button class="quick-chip" data-prompt="요즘 트렌드 알려줘">트렌드 분석</button>
                <button class="quick-chip" data-prompt="이력서 매칭해줘">이력서 매칭</button>
                <button class="quick-chip" data-prompt="역량 갭 분석해줘">갭 분석</button>
            </div>
        </div>
    `;
    bindQuickChips();
    closeSidebar();
});

// Sidebar
sidebarToggle.addEventListener("click", () => {
    const isOpen = sidebar.classList.toggle("open");
    sidebarToggle.setAttribute("aria-expanded", isOpen);
});

document.addEventListener("click", (e) => {
    if (sidebar.classList.contains("open") && !sidebar.contains(e.target) && e.target !== sidebarToggle) {
        closeSidebar();
    }
});

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
        if (profileModal.classList.contains("active")) {
            closeProfileModal();
        } else if (sidebar.classList.contains("open")) {
            closeSidebar();
        }
    }
});

function closeSidebar() {
    sidebar.classList.remove("open");
    sidebarToggle.setAttribute("aria-expanded", "false");
}

// Feature buttons + quick chips
document.querySelectorAll(".feature-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
        inputEl.value = btn.dataset.prompt;
        inputEl.dispatchEvent(new Event("input"));
        sendMessage();
        closeSidebar();
    });
});

function bindQuickChips() {
    document.querySelectorAll(".quick-chip").forEach((chip) => {
        chip.addEventListener("click", () => {
            inputEl.value = chip.dataset.prompt;
            inputEl.dispatchEvent(new Event("input"));
            sendMessage();
        });
    });
}
bindQuickChips();

// === Message Rendering ===
function addMessage(role, content, intent) {
    const welcome = messagesEl.querySelector(".welcome-message");
    if (welcome) welcome.remove();

    const msg = document.createElement("div");
    msg.className = `message ${role}`;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = role === "user" ? (currentUser ? currentUser.name.charAt(0) : "U") : "JS";

    const contentEl = document.createElement("div");
    contentEl.className = "message-content";

    if (role === "ai") {
        if (intent && intent !== "chitchat") {
            const intentLabels = { job_search: "공고 검색", resume_match: "이력서 매칭", skill_gap: "역량 갭 분석", trend: "트렌드 분석" };
            const badge = document.createElement("span");
            badge.className = "intent-badge";
            badge.textContent = intentLabels[intent] || intent;
            contentEl.appendChild(badge);
        }
        const parsed = document.createElement("div");
        parsed.innerHTML = DOMPurify.sanitize(marked.parse(content));
        contentEl.appendChild(parsed);
    } else {
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
    avatar.textContent = "JS";

    const contentEl = document.createElement("div");
    contentEl.className = "message-content";
    contentEl.innerHTML = '<div class="loading-dots"><span></span><span></span><span></span></div>';

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
    statusBadge.textContent = loading ? "Thinking..." : "Ready";
    statusBadge.classList.toggle("loading", loading);
}

async function sendMessage() {
    const message = inputEl.value.trim();
    if (!message) return;

    addMessage("user", message);
    inputEl.value = "";
    inputEl.style.height = "auto";
    sendBtn.disabled = true;

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
            throw new Error(err.detail || "Server error");
        }

        const data = await res.json();
        sessionId = data.session_id;
        addMessage("ai", data.response, data.intent);
    } catch (err) {
        removeLoadingMessage();
        addMessage("ai", `요청 처리 중 문제가 발생했습니다. 다시 시도해 주세요.`);
    } finally {
        setLoading(false);
        inputEl.focus();
    }
}

// === Start ===
init();
