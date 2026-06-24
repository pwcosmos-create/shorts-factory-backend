/**
 * 숏폼공장 — 기기(휴대폰·PC) 로컬 저장 유틸
 */
(function (global) {
  const KEYS = {
    apiKey: "sf_gemini_key",
    shopDraft: "sf_shop_draft",
    lastVideoMeta: "sf_last_video_meta",
  };

  let lastVideoBlobUrl = null;

  function sanitizeFilename(name) {
    return String(name || "숏폼")
      .replace(/[\\/:*?"<>|]/g, "")
      .replace(/\s+/g, "_")
      .slice(0, 40) || "숏폼";
  }

  function buildVideoFilename(businessName, durationSeconds) {
    const date = new Date().toISOString().slice(0, 10);
    return `${sanitizeFilename(businessName)}_${durationSeconds || 30}초_${date}.mp4`;
  }

  function loadApiKey(input) {
    if (!input) return;
    try {
      const saved = localStorage.getItem(KEYS.apiKey);
      if (saved) input.value = saved;
    } catch (_) {}
  }

  function saveApiKey(value) {
    if (!value) return;
    try {
      localStorage.setItem(KEYS.apiKey, value);
    } catch (_) {}
  }

  function loadShopDraft(nameInput, conceptInput) {
    try {
      const raw = localStorage.getItem(KEYS.shopDraft);
      if (!raw) return;
      const draft = JSON.parse(raw);
      if (nameInput && draft.name) nameInput.value = draft.name;
      if (conceptInput && draft.concept) conceptInput.value = draft.concept;
    } catch (_) {}
  }

  function saveShopDraft(nameInput, conceptInput) {
    try {
      localStorage.setItem(
        KEYS.shopDraft,
        JSON.stringify({
          name: nameInput?.value?.trim() || "",
          concept: conceptInput?.value?.trim() || "",
        })
      );
    } catch (_) {}
  }

  async function fetchVideoBlob(videoUrl) {
    const res = await fetch(videoUrl, { credentials: "same-origin" });
    if (!res.ok) throw new Error("영상 파일을 가져오지 못했습니다.");
    return res.blob();
  }

  async function saveVideoToDevice(videoUrl, options = {}) {
    const filename = buildVideoFilename(options.businessName, options.durationSeconds);
    const blob = await fetchVideoBlob(videoUrl);
    const file = new File([blob], filename, { type: "video/mp4" });

    if (lastVideoBlobUrl) URL.revokeObjectURL(lastVideoBlobUrl);
    lastVideoBlobUrl = URL.createObjectURL(blob);

    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      try {
        await navigator.share({ files: [file], title: filename, text: "숏폼공장 홍보 영상" });
        return { method: "share", filename, blobUrl: lastVideoBlobUrl };
      } catch (err) {
        if (err?.name === "AbortError") return { method: "cancelled", filename, blobUrl: lastVideoBlobUrl };
      }
    }

    const a = document.createElement("a");
    a.href = lastVideoBlobUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    return { method: "download", filename, blobUrl: lastVideoBlobUrl };
  }

  function bindDownloadButton(button, getVideoUrl, getMeta) {
    if (!button) return;
    button.addEventListener("click", async (e) => {
      e.preventDefault();
      const url = typeof getVideoUrl === "function" ? getVideoUrl() : getVideoUrl;
      if (!url) return;
      const prev = button.textContent;
      button.disabled = true;
      button.textContent = "저장 중…";
      try {
        await saveVideoToDevice(url, getMeta?.() || {});
        button.textContent = "저장 완료";
      } catch (err) {
        alert(err.message || "저장에 실패했습니다.");
        button.textContent = prev;
      } finally {
        button.disabled = false;
        setTimeout(() => { button.textContent = prev; }, 2500);
      }
    });
  }

  global.ShortsDeviceSave = {
    loadApiKey,
    saveApiKey,
    loadShopDraft,
    saveShopDraft,
    saveVideoToDevice,
    bindDownloadButton,
    getLastBlobUrl: () => lastVideoBlobUrl,
  };
})(window);
