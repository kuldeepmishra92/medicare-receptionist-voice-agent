/* ─────────────────────────────────────────────────────────
   Medicare Voice — Admin Dashboard Application Script
   Includes Web Speech Recognition (Microphone STT) & Text-To-Speech (Audio Voice Output)
   ───────────────────────────────────────────────────────── */

const API_BASE = "/api/v1";

let recognition = null;
let isListening = false;
const voiceSessionId = "sim_session_" + Date.now();

document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initClock();
    initTabs();
    initSpeechRecognition();
    initRefreshButton();
    loadDashboardData();
});


function initTheme() {
    const savedTheme = localStorage.getItem("dashboardTheme") || "black";
    setTheme(savedTheme);
}

function setTheme(theme) {
    const nextTheme = theme === "white" ? "white" : "black";
    document.body.setAttribute("data-theme", nextTheme);
    localStorage.setItem("dashboardTheme", nextTheme);
    document.querySelectorAll(".theme-option").forEach(button => {
        button.classList.toggle("active", button.dataset.themeValue === nextTheme);
    });
}
// ── Live Clock ────────────────────────────────────────────
function initClock() {
    const clock = document.getElementById("live-clock");
    const update = () => {
        const now = new Date();
        clock.innerText = now.toLocaleTimeString();
    };
    update();
    setInterval(update, 1000);
}

// ── Tab Navigation ────────────────────────────────────────
function initTabs() {
    const navItems = document.querySelectorAll(".nav-item");
    navItems.forEach(item => {
        item.addEventListener("click", () => {
            const targetTab = item.getAttribute("data-tab");
            switchTab(targetTab);
        });
    });
}

function switchTab(tabId) {
    document.querySelectorAll(".nav-item").forEach(i => i.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));

    const btn = document.querySelector(`.nav-item[data-tab="${tabId}"]`);
    const content = document.getElementById(tabId);

    if (btn) btn.classList.add("active");
    if (content) content.classList.add("active");

    // Update Titles
    const titleMap = {
        "tab-overview": ["Dashboard Overview", "Real-time hospital receptionist agent metrics and scheduling"],
        "tab-doctors": ["Doctor Management", "Manage doctor profiles, working schedules, and leave dates"],
        "tab-appointments": ["Appointment Bookings", "View, reschedule, and cancel patient appointments"],
        "tab-patients": ["Registered Patients", "View patient directory and auto-generated patient codes"],
        "tab-voice": ["Voice Agent Simulator", "Interactive voice call testing environment"],
    };

    if (titleMap[tabId]) {
        document.getElementById("page-title").innerText = titleMap[tabId][0];
        document.getElementById("page-subtitle").innerText = titleMap[tabId][1];
    }

    // Refresh Tab Data
    if (tabId === "tab-doctors") loadDoctors();
    if (tabId === "tab-appointments") loadAppointments();
    if (tabId === "tab-patients") loadPatients();
}

// ── Speech Recognition Setup (Microphone Voice Input) ────
function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        console.warn("Web Speech API is not supported in this browser.");
        return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onstart = () => {
        isListening = true;
        const micBtn = document.getElementById("mic-btn");
        if (micBtn) {
            micBtn.classList.add("recording");
            micBtn.innerHTML = "Listening...";
        }
        document.getElementById("stt-status").innerText = "🔴 Listening to your voice...";
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        console.log("Speech Recognized:", transcript);
        document.getElementById("voice-user-input").value = transcript;
        document.getElementById("stt-status").innerText = `Transcribed: "${transcript}"`;
        sendVoiceMessage();
    };

    recognition.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
        stopMicListening();
        document.getElementById("stt-status").innerText = `Mic Error: ${event.error}`;
    };

    recognition.onend = () => {
        stopMicListening();
    };
}

function toggleMicListening() {
    if (!recognition) {
        alert("Microphone voice input is supported best in Google Chrome or Microsoft Edge. Please use Chrome/Edge or type your query.");
        return;
    }

    if (isListening) {
        recognition.stop();
        stopMicListening();
    } else {
        try {
            recognition.start();
        } catch (e) {
            console.error("Failed to start recognition:", e);
        }
    }
}

function stopMicListening() {
    isListening = false;
    const micBtn = document.getElementById("mic-btn");
    if (micBtn) {
        micBtn.classList.remove("recording");
        micBtn.innerHTML = "Speak";
    }
}

async function speakTextOutLoud(text) {
    if (!text) return;
    try {
        const res = await fetch(`${API_BASE}/voice/tts`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: text })
        });
        if (res.ok) {
            const blob = await res.blob();
            const audioUrl = URL.createObjectURL(blob);
            const audio = new Audio(audioUrl);
            audio.play();
            const ttsElem = document.getElementById("tts-status");
            if (ttsElem) ttsElem.innerText = "🔊 Played high-quality ElevenLabs TTS voice audio";
            return;
        }
    } catch (e) {
        console.warn("ElevenLabs TTS endpoint unreachable, falling back to browser synthesis:", e);
    }

    // Fallback to browser SpeechSynthesis API
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        window.speechSynthesis.speak(utterance);
        const ttsElem = document.getElementById("tts-status");
        if (ttsElem) ttsElem.innerText = "🔊 Played voice response via Web Speech API (Fallback)";
    }
}


function initRefreshButton() {
    const refreshBtn = document.getElementById("refresh-btn");
    if (refreshBtn) {
        refreshBtn.addEventListener("click", refreshDashboard);
    }
}

async function refreshDashboard() {
    const refreshBtn = document.getElementById("refresh-btn");
    const originalText = refreshBtn ? refreshBtn.innerText : "Refresh";
    if (refreshBtn) {
        refreshBtn.disabled = true;
        refreshBtn.innerText = "Refreshing...";
    }

    try {
        await loadDashboardData();
        const activeTab = document.querySelector(".tab-content.active")?.id;
        if (activeTab === "tab-doctors") await loadDoctors();
        if (activeTab === "tab-appointments") await loadAppointments();
        if (activeTab === "tab-patients") await loadPatients();
    } finally {
        if (refreshBtn) {
            refreshBtn.innerText = "Done";
            setTimeout(() => {
                refreshBtn.disabled = false;
                refreshBtn.innerText = originalText;
            }, 700);
        }
    }
}
// ── Load Overview Stats ──────────────────────────────────
async function loadDashboardData() {
    try {
        const [aptsRes, docsRes, patsRes] = await Promise.all([
            fetch(`${API_BASE}/appointments/`).then(r => r.json()),
            fetch(`${API_BASE}/doctors/`).then(r => r.json()),
            fetch(`${API_BASE}/patients/`).then(r => r.json()),
        ]);

        document.getElementById("stat-total-apts").innerText = Array.isArray(aptsRes) ? aptsRes.length : 0;
        document.getElementById("stat-total-doctors").innerText = Array.isArray(docsRes) ? docsRes.length : 0;
        document.getElementById("stat-total-patients").innerText = Array.isArray(patsRes) ? patsRes.length : 0;

        renderOverviewRecentTable(Array.isArray(aptsRes) ? aptsRes.slice(0, 5) : []);
    } catch (e) {
        console.error("Dashboard data load error:", e);
    }
}

function renderOverviewRecentTable(apts) {
    const tbody = document.getElementById("overview-recent-table");
    if (!apts || apts.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center">No appointments found.</td></tr>`;
        return;
    }

    tbody.innerHTML = apts.map(a => `
        <tr>
            <td><strong>${a.appointment_id}</strong></td>
            <td>${a.patient_id.substring(0, 8)}...</td>
            <td>${a.doctor_id.substring(0, 8)}...</td>
            <td>${formatDateTime(a.appointment_date)}</td>
            <td><span class="badge-status status-${a.status}">${a.status}</span></td>
        </tr>
    `).join("");
}

// ── Load Doctors ──────────────────────────────────────────
async function loadDoctors() {
    const grid = document.getElementById("doctors-grid");
    grid.innerHTML = `<p class="text-subtle">Loading doctors...</p>`;
    try {
        const res = await fetch(`${API_BASE}/doctors/`);
        const docs = await res.json();

        if (!docs || docs.length === 0) {
            grid.innerHTML = `<p class="text-subtle">No doctors registered yet.</p>`;
            return;
        }

        grid.innerHTML = docs.map(d => `
            <div class="doctor-card">
                <div>
                    <h4 class="doc-name">${d.full_name}</h4>
                    <span class="doc-spec">${d.specialization}</span>
                </div>
                <div class="doc-hours">
                    📅 Working Days: ${(d.working_days || []).join(", ")}<br>
                    ⏰ Hours: ${d.work_start_time} - ${d.work_end_time} (${d.slot_duration_minutes} min slots)
                </div>
                <div>
                    <span class="badge-status status-confirmed">Active</span>
                </div>
            </div>
        `).join("");
    } catch (e) {
        grid.innerHTML = `<p class="text-subtle">Error loading doctors.</p>`;
    }
}

// ── Load Appointments ────────────────────────────────────
async function loadAppointments() {
    const tbody = document.getElementById("all-appointments-table");
    const statusFilter = document.getElementById("apt-status-filter").value;
    tbody.innerHTML = `<tr><td colspan="7" class="text-center">Loading appointments...</td></tr>`;

    try {
        let url = `${API_BASE}/appointments/`;
        if (statusFilter) url += `?status_filter=${statusFilter}`;

        const res = await fetch(url);
        const apts = await res.json();

        if (!apts || apts.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center">No appointments found.</td></tr>`;
            return;
        }

        tbody.innerHTML = apts.map(a => `
            <tr>
                <td><strong>${a.appointment_id}</strong></td>
                <td>${a.patient_id.substring(0, 8)}...</td>
                <td>${a.doctor_id.substring(0, 8)}...</td>
                <td>${formatDateTime(a.appointment_date)}</td>
                <td><span class="badge-status status-${a.status}">${a.status}</span></td>
                <td><span class="time-display">${a.google_event_id || 'N/A'}</span></td>
                <td>
                    ${a.status !== 'cancelled' ? `
                        <button class="btn btn-sm btn-danger" onclick="cancelAppointment('${a.appointment_id}')">Cancel</button>
                    ` : '<span class="text-subtle">Cancelled</span>'}
                </td>
            </tr>
        `).join("");
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center">Error loading appointments.</td></tr>`;
    }
}

// ── Cancel Appointment ───────────────────────────────────
async function cancelAppointment(aptId) {
    if (!confirm(`Are you sure you want to cancel appointment ${aptId}?`)) return;

    try {
        const res = await fetch(`${API_BASE}/appointments/${aptId}`, { method: "DELETE" });
        if (res.ok) {
            alert(`Appointment ${aptId} cancelled successfully!`);
            loadAppointments();
            loadDashboardData();
        } else {
            const err = await res.json();
            alert(`Failed to cancel: ${err.detail || 'Unknown error'}`);
        }
    } catch (e) {
        alert(`Error cancelling appointment: ${e}`);
    }
}

// ── Load Patients ────────────────────────────────────────
async function loadPatients() {
    const tbody = document.getElementById("patients-table");
    tbody.innerHTML = `<tr><td colspan="5" class="text-center">Loading patients...</td></tr>`;

    try {
        const res = await fetch(`${API_BASE}/patients/`);
        const pats = await res.json();

        if (!pats || pats.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="text-center">No patients registered yet.</td></tr>`;
            return;
        }

        tbody.innerHTML = pats.map(p => `
            <tr>
                <td><strong>${p.patient_code}</strong></td>
                <td>${p.full_name}</td>
                <td>${p.phone_number}</td>
                <td>${p.email || 'N/A'}</td>
                <td>${formatDateTime(p.created_at)}</td>
            </tr>
        `).join("");
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center">Error loading patients.</td></tr>`;
    }
}

// ── Voice Agent Simulator Send ───────────────────────────
async function sendVoiceMessage() {
    const input = document.getElementById("voice-user-input");
    const text = input.value.trim();
    if (!text) return;

    const simPhone = document.getElementById("sim-phone").value.trim() || "+919876543210";
    const messagesContainer = document.getElementById("chat-messages");

    // Render User Message
    messagesContainer.innerHTML += `
        <div class="message msg-user">
            <div class="msg-bubble">${escapeHtml(text)}</div>
        </div>
    `;
    input.value = "";
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Inspector Status Update
    document.getElementById("stt-status").innerText = `Transcribed: "${text}"`;
    document.getElementById("graph-status").innerText = "Executing LangGraph State Graph & Tools...";

    try {
        const res = await fetch(`${API_BASE}/voice/webhook`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: text,
                phone_number: simPhone,
                session_id: voiceSessionId
            })
        });

        const data = await res.json();

        // Render Agent Response
        messagesContainer.innerHTML += `
            <div class="message msg-agent">
                <div class="msg-bubble">${escapeHtml(data.response)}</div>
            </div>
        `;
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // Inspector Payload Update
        document.getElementById("graph-status").innerText = "Completed";
        document.getElementById("tts-status").innerText = "Generated audio via ElevenLabs / Web Speech TTS";
        document.getElementById("raw-payload").innerText = JSON.stringify(data, null, 2);

        // Speak AI Response Out Loud via Text-to-Speech
        speakTextOutLoud(data.response);

        // Refresh stats
        loadDashboardData();
    } catch (e) {
        messagesContainer.innerHTML += `
            <div class="message msg-agent">
                <div class="msg-bubble" style="color: var(--danger)">Error connecting to voice agent webhook.</div>
            </div>
        `;
    }
}

// ── Helpers ──────────────────────────────────────────────
function formatDateTime(dtStr) {
    if (!dtStr) return "N/A";
    const dt = new Date(dtStr);
    return dt.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function escapeHtml(text) {
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}






