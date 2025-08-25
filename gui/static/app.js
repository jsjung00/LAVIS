(function () {
  const fileInput = document.getElementById("fileInput");
  const submitBtn = document.getElementById("submitBtn");
  const clearBtn = document.getElementById("clearBtn");
  const canvasWrapper = document.getElementById("canvasWrapper");
  const imageCanvas = document.getElementById("imageCanvas");
  const drawCanvas = document.getElementById("drawCanvas");
  const mainCaption = document.getElementById("mainCaption");
  const captionsListHeader = document.getElementById("captionsListHeader");
  const captionsList = document.getElementById("captionsList");
  const statusBox = document.getElementById("status");

  const galleryEl = document.getElementById("gallery");
  const galleryStatus = document.getElementById("galleryStatus");
  const GALLERY_URLS = [
    "https://files.cryoetdataportal.cziscience.com/10302/01082023_BrnoKrios_Arctis_WebUI_Position_35/Reconstructions/VoxelSpacing7.840/Images/100/key-photo-original.png",
    "https://files.cryoetdataportal.cziscience.com/10302/01082023_BrnoKrios_Arctis_WebUI_Position_6/Reconstructions/VoxelSpacing7.840/Images/100/key-photo-original.png",
    "https://files.cryoetdataportal.cziscience.com/10302/01082023_BrnoKrios_Arctis_WebUI_Position_8/Reconstructions/VoxelSpacing7.840/Images/100/key-photo-original.png",
    "https://files.cryoetdataportal.cziscience.com/10302/01112022_BrnoKrios_Arctis_p3xe_grid1_Position_19/Reconstructions/VoxelSpacing7.840/Images/100/key-photo-original.png",
    "https://files.cryoetdataportal.cziscience.com/10302/01122021_BrnoKrios_arctis_lam2_pos16/Reconstructions/VoxelSpacing7.840/Images/100/key-photo-original.png",
    "https://files.cryoetdataportal.cziscience.com/10302/02052022_BrnoKrios_Arctis_grid_hGIS_Position_15/Reconstructions/VoxelSpacing7.840/Images/100/key-photo-original.png",
    "https://files.cryoetdataportal.cziscience.com/10302/02052022_BrnoKrios_Arctis_grid_hGIS_Position_70/Reconstructions/VoxelSpacing7.840/Images/100/key-photo-original.png",
    "https://files.cryoetdataportal.cziscience.com/10302/02052022_BrnoKrios_Arctis_grid_hGIS_Position_79/Reconstructions/VoxelSpacing7.840/Images/100/key-photo-original.png",
    "https://files.cryoetdataportal.cziscience.com/10302/02122021_BrnoKrios_Arctis_lam1_pos6/Reconstructions/VoxelSpacing7.840/Images/100/key-photo-original.png",
    "https://files.cryoetdataportal.cziscience.com/10302/06022023_BrnoKrios_Arctis_xe_Position_108/Reconstructions/VoxelSpacing7.840/Images/100/key-photo-original.png",
    "https://files.cryoetdataportal.cziscience.com/10302/06022023_BrnoKrios_Arctis_xe_Position_92/Reconstructions/VoxelSpacing7.840/Images/100/key-photo-original.png",
    "https://files.cryoetdataportal.cziscience.com/10302/08042022_BrnoKrios_Arctis_grid4_Position_3/Reconstructions/VoxelSpacing7.840/Images/100/key-photo-original.png",
    "https://files.cryoetdataportal.cziscience.com/10302/08042022_BrnoKrios_Arctis_grid5_gistest_Position_17/Reconstructions/VoxelSpacing7.840/Images/100/key-photo-original.png",
    "https://files.cryoetdataportal.cziscience.com/10302/08042022_BrnoKrios_Arctis_grid5_gistest_Position_27/Reconstructions/VoxelSpacing7.840/Images/100/key-photo-original.png",
    "https://files.cryoetdataportal.cziscience.com/10302/09022023_BrnoKrios_Arctis_xe_grid7_Position_12/Reconstructions/VoxelSpacing7.840/Images/100/key-photo-original.png",
  ];

  const imgCtx = imageCanvas.getContext("2d");
  const drawCtx = drawCanvas.getContext("2d");

  let img = new Image();
  let isDragging = false;
  let startX = 0,
    startY = 0,
    endX = 0,
    endY = 0;
  let hasBox = false;

  // Helpers
  function fitCanvasToImage(width, height, maxW = 900, maxH = 600) {
    // Simple contain fit
    const ratio = Math.min(maxW / width, maxH / height, 1);
    const w = Math.round(width * ratio);
    const h = Math.round(height * ratio);
    imageCanvas.width = w;
    imageCanvas.height = h;
    drawCanvas.width = w;
    drawCanvas.height = h;
    drawCanvas.style.left = imageCanvas.offsetLeft + "px";
    drawCanvas.style.top = imageCanvas.offsetTop + "px";
  }

  function redrawOverlay() {
    drawCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
    if (hasBox) {
      const x = Math.min(startX, endX);
      const y = Math.min(startY, endY);
      const w = Math.abs(endX - startX);
      const h = Math.abs(endY - startY);
      drawCtx.lineWidth = 4;
      drawCtx.strokeStyle = "red";
      drawCtx.strokeRect(x + 0.5, y + 0.5, w, h);
    }
  }

  function drawMainImageAndReset() {
    canvasWrapper.classList.remove("d-none");
    fitCanvasToImage(img.naturalWidth, img.naturalHeight);
    imgCtx.clearRect(0, 0, imageCanvas.width, imageCanvas.height);
    imgCtx.drawImage(img, 0, 0, imageCanvas.width, imageCanvas.height);
    hasBox = false;
    redrawOverlay();
    submitBtn.disabled = false;
    clearBtn.disabled = true;
  }

  async function loadFromURL(url) {
    statusBox.textContent = "Loading image…";
    const newImg = new Image();
    // Attempt to keep canvas untainted when the origin allows it
    newImg.crossOrigin = "anonymous";
    newImg.onload = () => {
      img = newImg;
      drawMainImageAndReset();
      statusBox.textContent = "";
    };
    newImg.onerror = () => {
      statusBox.textContent = "Failed to load image from URL.";
    };
    // Cache-busting to avoid stale thumbnails in certain setups
    const sep = url.includes("?") ? "&" : "?";
    newImg.src = url + sep + "t=" + Date.now();
  }

  // Load local image to canvas (client-side only)
  fileInput.addEventListener("change", (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      img.onload = () => {
        canvasWrapper.classList.remove("d-none");
        fitCanvasToImage(img.naturalWidth, img.naturalHeight);
        // draw base image
        imgCtx.clearRect(0, 0, imageCanvas.width, imageCanvas.height);
        imgCtx.drawImage(img, 0, 0, imageCanvas.width, imageCanvas.height);
        // reset overlay
        hasBox = false;
        redrawOverlay();
        submitBtn.disabled = false;
        clearBtn.disabled = true;
      };
      img.src = ev.target.result;
    };
    reader.readAsDataURL(file);
  });

  function getCanvasPos(e, canvas) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY,
    };
  }

  // Use pointer events (works for mouse + touch + pen)
  drawCanvas.addEventListener("pointerdown", (e) => {
    if (!img.src) return;
    isDragging = true;
    hasBox = true;
    const { x, y } = getCanvasPos(e, drawCanvas);
    startX = x;
    startY = y;
    endX = x;
    endY = y;
    redrawOverlay();
  });

  drawCanvas.addEventListener("pointermove", (e) => {
    if (!isDragging) return;
    const { x, y } = getCanvasPos(e, drawCanvas);
    endX = x;
    endY = y;
    redrawOverlay();
  });

  window.addEventListener("pointerup", () => {
    if (isDragging) {
      isDragging = false;
      clearBtn.disabled = !hasBox;
    }
  });

  clearBtn.addEventListener("click", () => {
    hasBox = false;
    redrawOverlay();
    clearBtn.disabled = true;
  });

  // Submit: export a composed image (base + red square) as PNG data URL
  submitBtn.addEventListener("click", async () => {
    if (!img.src) return;
    statusBox.textContent = "Generating captions…";

    // Compose onto an offscreen canvas at the visible size for simplicity
    const compose = document.createElement("canvas");
    compose.width = imageCanvas.width;
    compose.height = imageCanvas.height;
    const cctx = compose.getContext("2d");
    cctx.drawImage(imageCanvas, 0, 0);

    if (hasBox) {
      const x = Math.min(startX, endX);
      const y = Math.min(startY, endY);
      const w = Math.abs(endX - startX);
      const h = Math.abs(endY - startY);
      cctx.lineWidth = 6;
      cctx.strokeStyle = "red";
      cctx.strokeRect(x + 0.5, y + 0.5, w, h);
    }

    const dataURL = compose.toDataURL("image/png");

    try {
      // Clear previous results
      mainCaption.textContent = "";
      captionsList.innerHTML = "";
      captionsListHeader.classList.add("d-none");
      statusBox.textContent = "Processing image…";
      const resp = await fetch("/caption", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_data: dataURL }),
      });
      const payload = await resp.json();
      captionsList.innerHTML = "";
      if (!resp.ok) throw new Error(payload.error || "Server error");
      const { captions } = payload;
      captions.forEach((t, i) => {
        // set to 6 word maximum
        // replace " - " with ", "
        t = t.replace(/ - /g, ", ");
        // t = t.split(" ").slice(0, 6).join(" ");
        if (i === 0) {
          mainCaption.textContent = t;
          return;
        }
        const li = document.createElement("li");
        li.textContent = t;
        captionsList.appendChild(li);
      });
      captionsListHeader.classList.remove("d-none");
      statusBox.textContent = captions.length ? "" : "No captions returned.";
    } catch (err) {
      statusBox.textContent = "Error: " + err.message;
    }
  });

  (function initGallery() {
    galleryEl.innerHTML = "";
    const frag = document.createDocumentFragment();
    GALLERY_URLS.forEach((url, idx) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "thumb-btn";
      btn.setAttribute("data-url", url);
      btn.setAttribute("aria-label", `Load gallery image ${idx + 1}`);
      btn.innerHTML = `
        <img style="width: 256px;" loading="lazy" alt="Gallery image ${
          idx + 1
        }" />
      `;
      const imgEl = btn.querySelector("img");
      imgEl.src = url;
      imgEl.referrerPolicy = "no-referrer";
      // Clicking loads image to the canvas
      btn.addEventListener("click", () => {
        [...galleryEl.querySelectorAll(".thumb-btn.active")].forEach((b) =>
          b.classList.remove("active")
        );
        btn.classList.add("active");
        loadFromURL(url);
      });
      frag.appendChild(btn);
    });
    galleryEl.appendChild(frag);
    galleryStatus.textContent = `Loaded ${GALLERY_URLS.length} gallery items.`;
  })();
})();
