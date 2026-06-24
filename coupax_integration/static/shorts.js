const API_URL = "/api/v1/shorts/generate-pipeline";
const DS = window.ShortsDeviceSave;

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
const businessNameInput = document.getElementById("business-name");
const businessConceptInput = document.getElementById("business-concept");

const LOADING_STEPS = [
  "Gemini 시나리오 생성 중...",
  "Lyria BGM 렌더링 중...",
  "Imagen 이미지 생성 중...",
  "영상 조립 중...",
  "기기에 저장 중...",
];

let loadingInterval = null;
let phoneRotateInterval = null;
let currentVideoUrl = null;
let currentVideoMeta = {};

if (DS) {
  DS.loadApiKey(apiKeyInput);
  DS.loadShopDraft(businessNameInput, businessConceptInput);
  businessNameInput?.addEventListener("blur", () => DS.saveShopDraft(businessNameInput, businessConceptInput));
  businessConceptInput?.addEventListener("blur", () => DS.saveShopDraft(businessNameInput, businessConceptInput));
  DS.bindDownloadButton(finalVideoDownload, () => currentVideoUrl, () => currentVideoMeta);
}

toggleKeyBtn?.addEventListener("click", () => {
  const isPassword = apiKeyInput.type === "password";
  apiKeyInput.type = isPassword ? "text" : "password";
  toggleKeyBtn.textContent = isPassword ? "숨기기" : "보기";
});

form?.addEventListener("submit", async (e) => {
  e.preventDefault();

  const payload = {
    credentials: { api_key: apiKeyInput.value.trim() },
    business_name: businessNameInput.value.trim(),
    business_concept: businessConceptInput.value.trim(),
    video_style: document.getElementById("video-style").value,
    duration_seconds: parseInt(document.getElementById("duration").value, 10),
  };

  if (!payload.credentials.api_key || !payload.business_name || !payload.business_concept) {
    showError("API 키, 매장명, 컨셉은 필수 입력 항목입니다.");
    return;
  }

  currentVideoMeta = {
    businessName: payload.business_name,
    durationSeconds: payload.duration_seconds,
  };

  startLoading();
  submitBtn.disabled = true;
  currentVideoUrl = null;
  if (finalVideoContainer) finalVideoContainer.style.display = "none";

  try {
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(
        typeof data.detail === "string" ? data.detail : "서버 오류가 발생했습니다."
      );
    }

    await showResults(data);
    startPhonePreview(data.assets?.timeline_scenes || []);
    if (DS) {
      DS.saveApiKey(payload.credentials.api_key);
      DS.saveShopDraft(businessNameInput, businessConceptInput);
    }
  } catch (err) {
    showError(err.message);
  } finally {
    stopLoading();
    submitBtn.disabled = false;
  }
});

function startLoading() {
  loadingOverlay.classList.add("visible");
  let step = 0;
  loadingStep.textContent = LOADING_STEPS[0];
  loadingInterval = setInterval(() => {
    step = (step + 1) % LOADING_STEPS.length;
    loadingStep.textContent = LOADING_STEPS[step];
  }, 1800);
}

function stopLoading() {
  loadingOverlay.classList.remove("visible");
  clearInterval(loadingInterval);
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

async function showResults(data) {
  if (!data.final_video_url) {
    showError("영상이 생성되지 않았습니다.");
    return;
  }

  currentVideoUrl = data.final_video_url;
  currentVideoMeta = {
    businessName: data.meta?.business_name || businessNameInput?.value?.trim(),
    durationSeconds: data.meta?.total_duration || 30,
  };

  resultsEmpty.style.display = "none";
  resultsPanel.classList.add("visible");
  statusBanner.className = "shorts-status ok";
  statusBanner.textContent = data.message || "생성 완료";

  const meta = data.meta || {};
  metaRow.innerHTML = `
    <span>${escapeHtml(meta.business_name || "")}</span>
    <span>${escapeHtml(meta.style || "")}</span>
    <span>${meta.total_duration || 0}초</span>
  `;

  const scenes = data.assets?.timeline_scenes || [];
  sceneList.innerHTML = scenes
    .map(
      (scene) => `
    <div class="shorts-scene-card">
      <div class="shorts-scene-head">
        <span class="shorts-scene-num">Scene ${scene.scene_number}</span>
        <span class="shorts-scene-badge">렌더 완료</span>
      </div>
      <div class="shorts-scene-caption">${escapeHtml(scene.caption)}</div>
      <div class="shorts-scene-narration">${escapeHtml(scene.narration)}</div>
    </div>
  `
    )
    .join("");

  if (finalVideoContainer && finalVideoPlayer) {
    finalVideoContainer.style.display = "block";
    finalVideoPlayer.src = data.final_video_url;
  }

  if (DS) {
    try {
      const result = await DS.saveVideoToDevice(data.final_video_url, currentVideoMeta);
      if (result.method === "download") {
        statusBanner.textContent += " · 기기에 저장됨";
        if (finalVideoPlayer && result.blobUrl) finalVideoPlayer.src = result.blobUrl;
      } else if (result.method === "share") {
        statusBanner.textContent += " · 공유 메뉴에서 저장하세요";
      }
    } catch (err) {
      statusBanner.textContent += ` · 저장 실패: ${err.message}`;
    }
  }
}

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
