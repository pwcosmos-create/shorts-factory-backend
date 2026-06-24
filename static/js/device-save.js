/**
 * 숏폼공장 — 기기(휴대폰·PC) 로컬 저장 유틸
 * 서버에는 영상·API 키를 남기지 않고, 브라우저에서만 다운로드/기억합니다.
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
    } catch (_) {
      /* private mode */
    }
  }

  function saveApiKey(value) {
    if (!value) return;
    try {
      localStorage.setItem(KEYS.apiKey, value);
    } catch (_) {
      /* quota / private mode */
    }
  }

  function loadShopDraft(nameInput, conceptInput, keywordsInput) {
    try {
      const raw = localStorage.getItem(KEYS.shopDraft);
      if (!raw) return;
      const draft = JSON.parse(raw);
      if (nameInput && draft.name) nameInput.value = draft.name;
      if (conceptInput && draft.concept) conceptInput.value = draft.concept;
      if (keywordsInput && draft.keywords) keywordsInput.value = draft.keywords;
    } catch (_) {
      /* ignore */
    }
  }

  function saveShopDraft(nameInput, conceptInput, keywordsInput) {
    try {
      localStorage.setItem(
        KEYS.shopDraft,
        JSON.stringify({
          name: nameInput?.value?.trim() || "",
          concept: conceptInput?.value?.trim() || "",
          keywords: keywordsInput?.value?.trim() || "",
        })
      );
    } catch (_) {
      /* ignore */
    }
  }

  async function fetchVideoBlob(videoUrl) {
    const res = await fetch(videoUrl, { credentials: "same-origin" });
    if (!res.ok) {
      throw new Error("영상 파일을 가져오지 못했습니다.");
    }
    return res.blob();
  }

  /**
   * MP4를 기기에 저장합니다.
   * - PC: 다운로드 폴더로 저장
   * - iOS/Android: 공유 시트 → '파일에 저장' / 갤러리 저장 가능
   */
  async function saveVideoToDevice(videoUrl, options = {}) {
    const filename = buildVideoFilename(
      options.businessName,
      options.durationSeconds
    );
    const blob = await fetchVideoBlob(videoUrl);
    const file = new File([blob], filename, { type: "video/mp4" });

    if (lastVideoBlobUrl) {
      URL.revokeObjectURL(lastVideoBlobUrl);
      lastVideoBlobUrl = null;
    }
    lastVideoBlobUrl = URL.createObjectURL(blob);

    try {
      localStorage.setItem(
        KEYS.lastVideoMeta,
        JSON.stringify({
          filename,
          savedAt: new Date().toISOString(),
          businessName: options.businessName || "",
          durationSeconds: options.durationSeconds || 30,
        })
      );
    } catch (_) {
      /* ignore */
    }

    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      try {
        await navigator.share({
          files: [file],
          title: filename,
          text: "숏폼공장에서 생성한 홍보 영상",
        });
        return { method: "share", filename, blobUrl: lastVideoBlobUrl };
      } catch (err) {
        if (err?.name === "AbortError") {
          return { method: "cancelled", filename, blobUrl: lastVideoBlobUrl };
        }
      }
    }

    const a = document.createElement("a");
    a.href = lastVideoBlobUrl;
    a.download = filename;
    a.rel = "noopener";
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
        const result = await saveVideoToDevice(url, getMeta?.() || {});
        if (result.method === "share") {
          button.textContent = "공유 완료";
        } else if (result.method === "cancelled") {
          button.textContent = "기기에 다시 저장";
        } else {
          button.textContent = "저장 완료";
        }
      } catch (err) {
        alert(err.message || "저장에 실패했습니다.");
        button.textContent = prev;
      } finally {
        button.disabled = false;
        setTimeout(() => {
          button.textContent = prev;
        }, 2500);
      }
    });
  }

  global.ShortsDeviceSave = {
    KEYS,
    loadApiKey,
    saveApiKey,
    loadShopDraft,
    saveShopDraft,
    buildVideoFilename,
    saveVideoToDevice,
    bindDownloadButton,
    getLastBlobUrl: () => lastVideoBlobUrl,
  };
})(window);
