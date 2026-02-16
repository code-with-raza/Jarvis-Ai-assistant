// ===== Backend URLs =====
const BASE_URL = "http://127.0.0.1:8000";
const CHAT_URL = `${BASE_URL}/chat`;
const UPLOAD_URL = `${BASE_URL}/upload_pdf`;

// ===== DOM =====
const chatEl = document.getElementById("chat");
const textEl = document.getElementById("text");
const sendBtn = document.getElementById("sendBtn");
const micBtn = document.getElementById("micBtn");
const sessionEl = document.getElementById("session");
const statusEl = document.getElementById("status");
const countdownEl = document.getElementById("countdown");
const connEl = document.getElementById("conn");
const dotEl = document.getElementById("dot");
const ttsEl = document.getElementById("tts");

const uploadBtn = document.getElementById("uploadBtn");
const pdfFile = document.getElementById("pdfFile");

// ===== UI helpers =====
function addMsg(role, content) {
  const wrap = document.createElement("div");
  wrap.className = "msg " + (role === "me" ? "me" : "jarvis");
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = content;
  wrap.appendChild(bubble);
  chatEl.appendChild(wrap);
  chatEl.scrollTop = chatEl.scrollHeight;
}

function speak(text) {
  if (!ttsEl.checked) return;
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 1.0;
  u.pitch = 1.0;
  window.speechSynthesis.speak(u);
}

async function checkApi() {
  try {
    const r = await fetch("http://127.0.0.1:8000/");
    if (!r.ok) throw new Error("bad status");
    connEl.textContent = "API: ready";
    dotEl.classList.add("ok");
    dotEl.classList.remove("warn");
  } catch {
    connEl.textContent = "API: offline";
    dotEl.classList.remove("ok");
  }
}
checkApi();
setInterval(checkApi, 4000);

// ===== Chat =====
async function sendMessage(msg) {
  const session_id = sessionEl.value.trim() || "default";
  addMsg("me", msg);
  statusEl.textContent = "Jarvis is thinking…";
  countdownEl.textContent = "";

  try {
    const r = await fetch(CHAT_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id, text: msg })
    });

    if (!r.ok) {
      const errText = await r.text();
      statusEl.textContent = "Server error";
      addMsg("jarvis", `❌ ${r.status}: ${errText}`);
      return;
    }

    const data = await r.json();
    const answer = data.output ?? "(no output)";
    addMsg("jarvis", answer);
    speak(answer);
    statusEl.textContent = "Ready.";
  } catch (e) {
    statusEl.textContent = "Offline / CORS / server not running";
    addMsg("jarvis", "❌ Could not reach API. Is FastAPI running on :8000?");
  }
}

sendBtn.addEventListener("click", () => {
  const msg = textEl.value.trim();
  if (!msg) return;
  textEl.value = "";
  sendMessage(msg);
});

textEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendBtn.click();
});

// ===== PDF Upload =====
uploadBtn.addEventListener("click", async () => {
  const f = pdfFile.files[0];
  if (!f) {
    alert("Choose a PDF first.");
    return;
  }

  const session_id = sessionEl.value.trim() || "default";
  const form = new FormData();
  form.append("file", f);

  uploadBtn.disabled = true;
  uploadBtn.textContent = "Uploading…";
  statusEl.textContent = "Uploading PDF…";

  try {
    const r = await fetch(`${UPLOAD_URL}?session_id=${encodeURIComponent(session_id)}`, {
      method: "POST",
      body: form
    });

    const data = await r.json();

    if (!data.ok) {
      addMsg("jarvis", "❌ Upload failed: " + (data.error || "Unknown error"));
      statusEl.textContent = "Ready.";
      return;
    }

    addMsg(
      "jarvis",
      `✅ PDF uploaded: ${data.filename}\nChunks indexed: ${data.chunks_indexed}\nNow ask:\n/pdf ask <question> | source=${data.filename}`
    );
    statusEl.textContent = "Ready.";
  } catch (e) {
    addMsg("jarvis", "❌ Upload failed. Check server + CORS + that you opened web via http://localhost:5500");
    statusEl.textContent = "Ready.";
  } finally {
    uploadBtn.disabled = false;
    uploadBtn.textContent = "Upload PDF";
  }
});

// ===== Voice input (Wake word + 5s silence + countdown) =====
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let rec = null;
let listening = false;

let bufferText = "";
let silenceTimer = null;

const SILENCE_MS = 5000;
let countdownTimer = null;
let remainingSec = 0;

// Wake word
const WAKE_WORD = "hey jarvis";
let armed = false;

function stopCountdown() {
  if (countdownTimer) clearInterval(countdownTimer);
  countdownTimer = null;
  remainingSec = 0;
  countdownEl.textContent = "";
}

function startCountdown(seconds) {
  remainingSec = seconds;
  countdownEl.textContent = `Sending in ${remainingSec}s…`;

  if (countdownTimer) clearInterval(countdownTimer);
  countdownTimer = setInterval(() => {
    remainingSec -= 1;
    if (remainingSec <= 0) stopCountdown();
    else countdownEl.textContent = `Sending in ${remainingSec}s…`;
  }, 1000);
}

function resetSilenceTimer() {
  if (silenceTimer) clearTimeout(silenceTimer);

  stopCountdown();
  startCountdown(Math.ceil(SILENCE_MS / 1000));

  silenceTimer = setTimeout(() => {
    stopCountdown();
    const msg = bufferText.trim();
    bufferText = "";

    if (msg) sendMessage(msg);

    armed = false;
    statusEl.textContent = `Listening… Say “${WAKE_WORD}” to start.`;
  }, SILENCE_MS);
}

if (SpeechRecognition) {
  rec = new SpeechRecognition();
  rec.continuous = true;
  rec.interimResults = true;
  rec.lang = "en-US";

  rec.onstart = () => {
    listening = true;
    micBtn.classList.add("on");
    bufferText = "";
    armed = false;
    stopCountdown();
    statusEl.textContent = `Listening… Say “${WAKE_WORD}” to start.`;
  };

  rec.onend = () => {
    listening = false;
    micBtn.classList.remove("on");
    if (silenceTimer) clearTimeout(silenceTimer);
    silenceTimer = null;
    stopCountdown();
    statusEl.textContent = "Ready.";
  };

  rec.onerror = (e) => {
    stopCountdown();
    statusEl.textContent = "Mic error: " + e.error;
  };

  rec.onresult = (event) => {
    let interimText = "";
    let finalText = "";

    for (let i = event.resultIndex; i < event.results.length; i++) {
      const res = event.results[i];
      const txt = res[0].transcript;
      if (res.isFinal) finalText += " " + txt;
      else interimText += " " + txt;
    }

    const heardNow = (interimText + " " + finalText).trim();
    const heardLower = (bufferText + " " + heardNow).trim().toLowerCase();

    if (!armed) {
      if (heardLower.includes(WAKE_WORD)) {
        armed = true;
        bufferText = "";
        stopCountdown();
        statusEl.textContent = "✅ Activated. Speak your command…";
      } else {
        statusEl.textContent = `Listening… Say “${WAKE_WORD}” to start.`;
      }
      return;
    }

    if (finalText.trim()) {
      bufferText += (bufferText ? " " : "") + finalText.trim();
      resetSilenceTimer();
      statusEl.textContent = "Heard: " + bufferText;
    } else {
      statusEl.textContent = "Heard: " + (bufferText + " " + interimText).trim();
    }
  };

  micBtn.addEventListener("click", () => {
    if (!rec) return;

    if (listening) {
      if (silenceTimer) clearTimeout(silenceTimer);
      stopCountdown();

      const msg = bufferText.trim();
      bufferText = "";

      rec.stop();
      if (armed && msg) sendMessage(msg);
      armed = false;
    } else {
      rec.start();
    }
  });
} else {
  micBtn.disabled = true;
  statusEl.textContent = "Voice not supported. Use Chrome/Edge.";
}
