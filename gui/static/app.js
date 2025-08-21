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
})();
