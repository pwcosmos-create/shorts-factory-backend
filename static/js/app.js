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
const businessConceptInput = document.getElementById("business-concept");
const businessNameInput = document.getElementById("business-name");
const keywordsInput = document.getElementById("keywords");
const replicateKeyInput = document.getElementById("replicate-key");
const toggleReplicateBtn = document.getElementById("toggle-replicate-key");

let phoneRotateInterval = null;
let currentVideoUrl = null;
let currentVideoMeta = {};

toggleReplicateBtn?.addEventListener("click", () => {
  const isPassword = replicateKeyInput.type === "password";
  replicateKeyInput.type = isPassword ? "text" : "password";
  toggleReplicateBtn.textContent = isPassword ? "숨기기" : "보기";
});

toggleKeyBtn?.addEventListener("click", () => {
  const isPassword = apiKeyInput.type === "password";
  apiKeyInput.type = isPassword ? "text" : "password";
  toggleKeyBtn.textContent = isPassword ? "숨기기" : "보기";
});

if (DS) {
  DS.loadApiKey(apiKeyInput);
  DS.loadShopDraft(businessNameInput, businessConceptInput, keywordsInput);
  businessNameInput?.addEventListener("blur", () =>
    DS.saveShopDraft(businessNameInput, businessConceptInput, keywordsInput)
  );
  businessConceptInput?.addEventListener("blur", () =>
    DS.saveShopDraft(businessNameInput, businessConceptInput, keywordsInput)
  );
  keywordsInput?.addEventListener("blur", () =>
    DS.saveShopDraft(businessNameInput, businessConceptInput, keywordsInput)
  );
  DS.bindDownloadButton(
    finalVideoDownload,
    () => currentVideoUrl,
    () => currentVideoMeta
  );
}

form?.addEventListener("submit", async (e) => {
  e.preventDefault();

  const apiKey = apiKeyInput.value.trim();
  const repKey = replicateKeyInput ? replicateKeyInput.value.trim() : "";

  if (!apiKey) {
    alert("Google API 키를 입력해주세요.");
    return;
  }

  const payload = {
    credentials: { api_key: apiKey },
    business_name: businessNameInput.value.trim(),
    keywords: keywordsInput ? keywordsInput.value.trim() : "",
    business_concept: businessConceptInput.value.trim(),
    video_style: document.getElementById("video-style").value,
    duration_seconds: parseInt(document.getElementById("duration").value, 10),
  };
  if (repKey) payload.replicate_api_key = repKey;

  currentVideoMeta = {
    businessName: payload.business_name,
    durationSeconds: payload.duration_seconds,
  };

  startLoading();
  submitBtn.disabled = true;
  sceneList.innerHTML = "";
  currentVideoUrl = null;
  if (finalVideoContainer) finalVideoContainer.style.display = "none";
  resultsEmpty.style.display = "none";
  resultsPanel.classList.add("visible");
  statusBanner.className = "shorts-status ok";
  statusBanner.textContent = "생성 진행 중...";

  try {
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok) {
      const detail = data.detail;
      const msg =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((d) => d.msg).join(", ")
            : "서버 오류가 발생했습니다.";
      throw new Error(msg);
    }

    await handlePipelineResult(data);
    if (DS) {
      DS.saveApiKey(apiKey);
      DS.saveShopDraft(businessNameInput, businessConceptInput, keywordsInput);
    }
  } catch (err) {
    showError(err.message);
  } finally {
    stopLoading();
    submitBtn.disabled = false;
  }
});

async function handlePipelineResult(data) {
  if (!data.final_video_url) {
    showError("영상이 생성되지 않았습니다. 서버 로그를 확인해 주세요.");
    return;
  }

  currentVideoUrl = data.final_video_url;
  currentVideoMeta = {
    businessName: data.meta?.business_name || businessNameInput?.value?.trim(),
    durationSeconds: data.meta?.total_duration || 30,
  };

  statusBanner.textContent =
    data.message || `${currentVideoMeta.durationSeconds}초 숏폼 생성 완료`;

  const scenes = data.assets?.timeline_scenes || [];
  sceneList.innerHTML = "";
  scenes.forEach((s) => {
    const div = document.createElement("div");
    div.className = "shorts-scene-card";
    div.id = `scene-card-${s.scene_number}`;
    div.innerHTML = `
      <div class="shorts-scene-head">
        <span class="shorts-scene-num">Scene ${s.scene_number}</span>
        <span class="shorts-scene-badge">렌더 완료</span>
      </div>
      <div class="shorts-scene-caption">${escapeHtml(s.caption)}</div>
      <div class="shorts-scene-narration">${escapeHtml(s.narration)}</div>
    `;
    sceneList.appendChild(div);
  });

  if (finalVideoContainer && finalVideoPlayer) {
    finalVideoContainer.style.display = "block";
    const blobUrl = DS?.getLastBlobUrl?.();
    finalVideoPlayer.src = blobUrl || data.final_video_url;
  }

  if (scenes.length) startPhonePreview(scenes);

  if (DS) {
    try {
      const result = await DS.saveVideoToDevice(data.final_video_url, currentVideoMeta);
      if (result.method === "download") {
        statusBanner.textContent += " · 기기에 저장됨";
        if (finalVideoPlayer && result.blobUrl) {
          finalVideoPlayer.src = result.blobUrl;
        }
      } else if (result.method === "share") {
        statusBanner.textContent += " · 공유 메뉴에서 저장하세요";
      }
    } catch (err) {
      statusBanner.textContent += ` · 저장 실패: ${err.message}`;
    }
  }
}

function startLoading() {
  loadingOverlay.classList.add("visible");
  loadingStep.textContent = "시나리오 작성 시작...";
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
