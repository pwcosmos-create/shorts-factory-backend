const API_URL = "/api/v1/shorts/generate-pipeline";

const form = document.getElementById("generate-form");
const loadingOverlay = document.getElementById("loading-overlay");
const loadingStep = document.getElementById("loading-step");
const resultsEmpty = document.getElementById("results-empty");
const resultsPanel = document.getElementById("results-panel");
const statusBanner = document.getElementById("status-banner");
const metaRow = document.getElementById("meta-row");
const finalVideoContainer = document.getElementById("final-video-container");
const finalVideoPlayer = document.getElementById("final-video-player");
const finalVideoDownload = document.getElementById("final-video-download");
const sceneList = document.getElementById("scene-list");
const submitBtn = document.getElementById("submit-btn");
const toggleKeyBtn = document.getElementById("toggle-key");
const apiKeyInput = document.getElementById("api-key");
const loadExampleBtn = document.getElementById("load-example-btn");
const businessConceptInput = document.getElementById("business-concept");
const businessNameInput = document.getElementById("business-name");
const keywordsInput = document.getElementById("keywords");

const replicateKeyInput = document.getElementById("replicate-key");
const toggleReplicateBtn = document.getElementById("toggle-replicate-key");

toggleReplicateBtn?.addEventListener("click", () => {
  const isPassword = replicateKeyInput.type === "password";
  replicateKeyInput.type = isPassword ? "text" : "password";
  toggleReplicateBtn.textContent = isPassword ? "숨기기" : "보기";
});

function appendLog(msg) {
  loadingStep.textContent = msg;
}

let phoneRotateInterval = null;

toggleKeyBtn?.addEventListener("click", () => {
  const isPassword = apiKeyInput.type === "password";
  apiKeyInput.type = isPassword ? "text" : "password";
  toggleKeyBtn.textContent = isPassword ? "숨기기" : "보기";
});

loadExampleBtn?.addEventListener("click", async () => {
  const apiKey = apiKeyInput.value.trim();
  const bizName = businessNameInput.value.trim();
  const keywordsVal = keywordsInput ? keywordsInput.value.trim() : "";
  
  if (!apiKey || !bizName) {
    alert("API 키와 매장명을 먼저 입력해주세요.");
    return;
  }
  
  const originalText = loadExampleBtn.textContent;
  loadExampleBtn.textContent = "불러오는 중...";
  loadExampleBtn.disabled = true;
  
  try {
    const res = await fetch("/api/v1/shorts/generate-concept-example", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        credentials: { api_key: apiKey },
        business_name: bizName,
        keywords: keywordsVal
      })
    });
    
    const data = await res.json();
    if (res.ok && data.example) {
      businessConceptInput.value = data.example;
    } else {
      alert("예시를 불러오는데 실패했습니다.");
    }
  } catch (e) {
    alert("예시 불러오기 오류가 발생했습니다.");
  } finally {
    loadExampleBtn.textContent = originalText;
    loadExampleBtn.disabled = false;
  }
});

form?.addEventListener("submit", async (e) => {
  e.preventDefault();

  const apiKey = apiKeyInput.value.trim();
  const repKey = replicateKeyInput ? replicateKeyInput.value.trim() : "";
  
  if (!apiKey || !repKey) {
    alert("Google API 키와 Replicate API 키를 모두 입력해주세요.");
    return;
  }

  const payload = {
    credentials: { api_key: apiKey },
    replicate_api_key: repKey,
    business_name: document.getElementById("business-name").value.trim(),
    keywords: keywordsInput ? keywordsInput.value.trim() : "",
    business_concept: document.getElementById("business-concept").value.trim(),
    video_style: document.getElementById("video-style").value,
    duration_seconds: parseInt(document.getElementById("duration").value, 10),
  };

  startLoading();
  submitBtn.disabled = true;
  sceneList.innerHTML = "";
  if(finalVideoContainer) finalVideoContainer.style.display = "none";
  resultsEmpty.style.display = "none";
  resultsPanel.classList.add("visible");
  statusBanner.className = "shorts-status ok";
  statusBanner.textContent = "생성 진행 중...";

  try {
    const res = await fetch("/api/v1/shorts/generate-stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let done = false;

    while (!done) {
      const { value, done: doneReading } = await reader.read();
      done = doneReading;
      if (value) {
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.substring(6);
            try {
              const data = JSON.parse(dataStr);
              handleStreamEvent(data);
            } catch (e) {
              console.error("Parse error", e);
            }
          }
        }
      }
    }
  } catch (err) {
    showError(err.message);
  } finally {
    stopLoading();
    submitBtn.disabled = false;
  }
});

function handleStreamEvent(data) {
  if (data.message) appendLog(data.message);
  
  if (data.step === "blueprint") {
    const scenes = data.data.scenes;
    scenes.forEach(s => {
      const div = document.createElement("div");
      div.className = "shorts-scene-card";
      div.id = `scene-card-${s.scene_number}`;
      div.innerHTML = `
        <div class="shorts-scene-head">
          <span class="shorts-scene-num">Scene ${s.scene_number}</span>
          <span class="shorts-scene-badge" id="badge-${s.scene_number}">시나리오 생성됨</span>
        </div>
        <div class="shorts-scene-caption">${escapeHtml(s.caption)}</div>
        <div class="shorts-scene-narration">${escapeHtml(s.narration)}</div>
      `;
      sceneList.appendChild(div);
    });
  } else if (data.step === "image_done") {
    const badge = document.getElementById(`badge-${data.scene_number}`);
    if (badge) { badge.textContent = "이미지 완성"; badge.style.background = "#ff9800"; }
  } else if (data.step === "video_done") {
    const badge = document.getElementById(`badge-${data.scene_number}`);
    if (badge) { badge.textContent = "비디오 완성"; badge.style.background = "#4caf50"; }
  } else if (data.step === "complete") {
    statusBanner.textContent = data.message || "최종 생성 완료!";
    if (data.final_video_url && finalVideoContainer && finalVideoPlayer) {
      finalVideoContainer.style.display = "block";
      finalVideoPlayer.src = data.final_video_url;
      if (finalVideoDownload) finalVideoDownload.href = data.final_video_url;
    }
  } else if (data.step === "error") {
    showError(data.message);
  }
}

function startLoading() {
  loadingOverlay.classList.add("visible");
  appendLog("시나리오 작성 시작...");
}

function stopLoading() {
  loadingOverlay.classList.remove("visible");
}

function showError(message) {
  resultsEmpty.style.display = "none";
  resultsPanel.classList.add("visible");
  statusBanner.className = "shorts-status err";
  statusBanner.textContent = message;
  metaRow.innerHTML = "";
  sceneList.innerHTML = "";
  if (finalVideoContainer) finalVideoContainer.style.display = "none";
}

// showResults is deprecated due to streaming

function startPhonePreview(scenes) {
  const screen = document.getElementById("phone-screen");
  if (!screen || !scenes.length) return;

  clearInterval(phoneRotateInterval);

  screen.innerHTML = scenes
    .map(
      (s, i) => `
    <div class="shorts-phone-scene${i === 0 ? " active" : ""}">Scene ${s.scene_number}</div>
  `
    )
    .join(`
    <div class="shorts-phone-caption" id="phone-caption">${escapeHtml(scenes[0].caption)}</div>
  `);

  let current = 0;
  const phoneScenes = screen.querySelectorAll(".shorts-phone-scene");
  const captionEl = document.getElementById("phone-caption");

  phoneRotateInterval = setInterval(() => {
    phoneScenes[current]?.classList.remove("active");
    current = (current + 1) % scenes.length;
    phoneScenes[current]?.classList.add("active");
    if (captionEl) captionEl.textContent = scenes[current].caption;
  }, 3000);
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

(function initHeroDemo() {
  const captions = ["치즈 폭포의 향연!", "겉바속촉의 정석", "오늘 점심은 돈까스?"];
  const captionEl = document.getElementById("hero-caption");
  const scenes = document.querySelectorAll("#hero-phone .shorts-phone-scene");
  if (!scenes.length) return;

  let idx = 0;
  setInterval(() => {
    scenes[idx]?.classList.remove("active");
    idx = (idx + 1) % scenes.length;
    scenes[idx]?.classList.add("active");
    if (captionEl) captionEl.textContent = captions[idx];
  }, 2800);
})();
